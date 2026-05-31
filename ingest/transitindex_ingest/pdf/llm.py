"""The LLM extraction contract and clients.

`ExtractedValue` is what an LLM hands back per metric it found. `LLMClient` is
the structural interface the pipeline depends on; `AnthropicLLMClient` is the
real (lazy-imported) implementation and `FakeLLMClient` is the deterministic
test/eval double. `EXTRACTION_SYSTEM_PROMPT` and `EXTRACTION_TOOL` define the
structured-output schema the model must follow.

Only `ExtractedValue`, the protocol, the prompt/tool, `FakeLLMClient`, and the
number parser are stdlib-pure; the Anthropic SDK is imported lazily inside
`AnthropicLLMClient` so this module imports with no third-party deps.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional, Protocol, runtime_checkable

from ..refdata import METRICS

# The 14 sourced metrics are the only ones the model may emit. Derived metrics
# (average_fare, farebox_recovery_ratio, ...) are computed downstream, never
# read off a page.
SOURCED_METRIC_CODES: tuple[str, ...] = tuple(
    code for code, m in METRICS.items() if not m["is_derived"]
)

# Below this, a value is staged with an extra 'low_confidence' flag (still
# pending -- it does not block, it signals the reviewer).
LOW_CONFIDENCE_THRESHOLD = Decimal("0.7")


@dataclass(frozen=True)
class ExtractedValue:
    """One metric reading the LLM pulled from the document text.

    Carries the metric code, the parsed numeric value, the reporting period it
    belongs to, the page it came from, and the model's self-reported
    confidence. The pipeline maps this onto a `MetricValueRecord`.
    """

    metric_code: str
    value: Decimal
    unit: str
    period_kind: str  # 'annual' | 'monthly' | ...
    period_year: int
    page_number: int
    confidence: Decimal
    period_month: Optional[int] = None
    note: Optional[str] = None
    source_quote: Optional[str] = None  # verbatim snippet the number was read from (verify/review aid)


@runtime_checkable
class LLMClient(Protocol):
    """Extract metric values from document text. Implementations: real + fake."""

    def extract(
        self, system_prompt: str, document_text: str, agency_slug: str
    ) -> list[ExtractedValue]:
        ...


# --- system prompt + structured-output tool ---------------------------------

EXTRACTION_SYSTEM_PROMPT = f"""\
You extract transit performance figures from a Canadian transit agency's annual
report or budget. Return ONLY values you can read directly from the text.

Extract ONLY these {len(SOURCED_METRIC_CODES)} metric codes (ignore everything
else, and NEVER compute ratios or per-rider figures -- those are derived later):
{", ".join(SOURCED_METRIC_CODES)}

Rules:
- One result per (metric, reporting period). Use the period the figure reports
  on (period_kind 'annual' with period_year, or 'monthly' with period_month).
- Report the number in the document's own unit (e.g. count, hours, km, %, CAD).
  Convert "millions"/"thousands" wording into the full number.
- Canadian/French documents write numbers with spaces or non-breaking spaces as
  thousands separators (e.g. "1 234 567" = 1234567) and a comma decimal
  ("12,5" = 12.5). Normalize these to a plain number.
- confidence is 0..1. If you are NOT sure a figure maps to one of the codes,
  emit it with LOW confidence (below 0.7) rather than guessing or omitting it --
  do not silently drop uncertain figures. Never fabricate a value.
- Put any caveat (footnote, restated, partial year) in `note`.

Return your answer ONLY by calling the `record_metrics` tool.
"""

# Anthropic tool-use schema mirroring ExtractedValue. Used by AnthropicLLMClient
# to force structured JSON output.
EXTRACTION_TOOL = {
    "name": "record_metrics",
    "description": "Record every metric value extracted from the document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "values": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "metric_code": {
                            "type": "string",
                            "enum": list(SOURCED_METRIC_CODES),
                        },
                        "value": {
                            "type": "string",
                            "description": "Numeric value as written; separators ok.",
                        },
                        "unit": {"type": "string"},
                        "period_kind": {
                            "type": "string",
                            "enum": ["annual", "monthly"],
                        },
                        "period_year": {"type": "integer"},
                        "period_month": {"type": ["integer", "null"]},
                        "page_number": {"type": "integer"},
                        "confidence": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                        },
                        "note": {"type": ["string", "null"]},
                        "source_quote": {
                            "type": ["string", "null"],
                            "description": "Exact on-page text the value was read from.",
                        },
                    },
                    "required": [
                        "metric_code",
                        "value",
                        "unit",
                        "period_kind",
                        "period_year",
                        "page_number",
                        "confidence",
                    ],
                },
            }
        },
        "required": ["values"],
    },
}


def parse_number(raw: object) -> Decimal:
    """Parse a number string into Decimal, tolerating Canadian/French formats.

    Handles space / non-breaking-space thousands separators ('1 234 567') and a
    comma decimal ('12,5'). Plain ints/Decimals pass straight through.
    """
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, int):  # bool excluded: handled by Decimal path below
        return Decimal(raw)
    text = str(raw).strip()
    # Strip space-family thousands separators (regular, non-breaking, narrow nbsp).
    for sep in (" ", " ", " "):
        text = text.replace(sep, "")
    # Comma decimal -> dot decimal (only meaningful once spaces are gone).
    if "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"could not parse number: {raw!r}") from exc


def _row_to_value(row: dict) -> ExtractedValue:
    """Build an ExtractedValue from one structured-output row (tool input)."""
    return ExtractedValue(
        metric_code=row["metric_code"],
        value=parse_number(row["value"]),
        unit=row["unit"],
        period_kind=row["period_kind"],
        period_year=int(row["period_year"]),
        page_number=int(row["page_number"]),
        confidence=Decimal(str(row["confidence"])),
        period_month=(
            int(row["period_month"]) if row.get("period_month") is not None else None
        ),
        note=row.get("note"),
        source_quote=row.get("source_quote"),
    )


class AnthropicLLMClient:
    """Real LLM client over the Anthropic SDK (imported lazily).

    Uses tool-use for structured output and prompt caching (cache_control) on
    the system prompt and the document block, so re-runs over the same document
    are cheap. Only instantiated when ANTHROPIC_API_KEY is set; never exercised
    by the offline suite.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
    ) -> None:
        import anthropic  # lazy: real API path only

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def extract(
        self, system_prompt: str, document_text: str, agency_slug: str
    ) -> list[ExtractedValue]:
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": EXTRACTION_TOOL["name"]},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Agency: {agency_slug}\n\nDocument:",
                        },
                        {
                            "type": "text",
                            "text": document_text,
                            "cache_control": {"type": "ephemeral"},
                        },
                    ],
                }
            ],
        )
        rows: list[dict] = []
        for block in message.content:
            if getattr(block, "type", None) == "tool_use" and block.name == EXTRACTION_TOOL["name"]:
                rows.extend(block.input.get("values", []))
        return [_row_to_value(r) for r in rows]


class FakeLLMClient:
    """Deterministic LLMClient that returns a caller-supplied canned list.

    The test/eval double: feed it the ExtractedValues the model "would" return
    so the pipeline can be driven with no API and no PDF.
    """

    def __init__(self, values: list[ExtractedValue]) -> None:
        self._values = list(values)

    def extract(
        self, system_prompt: str, document_text: str, agency_slug: str
    ) -> list[ExtractedValue]:
        return list(self._values)
