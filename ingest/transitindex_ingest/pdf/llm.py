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

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional, Protocol, runtime_checkable

from ..refdata import METRICS

# The sourced metrics (every non-derived code in METRICS) are the only ones the
# model may emit. Derived metrics (average_fare, farebox_recovery_ratio, ...)
# are computed downstream, never read off a page.
SOURCED_METRIC_CODES: tuple[str, ...] = tuple(
    code for code, m in METRICS.items() if not m["is_derived"]
)

# Below this, a value is staged with an extra 'low_confidence' flag (still
# pending -- it does not block, it signals the reviewer).
LOW_CONFIDENCE_THRESHOLD = Decimal("0.7")

# Confidence ceilings applied in _row_to_value when the model's source_quote does
# not corroborate the printed digits (see quote_supports_value). A missing quote is
# unverifiable; a quote whose digits don't match is a stronger red flag.
QUOTE_MISSING_CONFIDENCE_CAP = Decimal("0.5")
QUOTE_MISMATCH_CONFIDENCE_CAP = Decimal("0.3")


@dataclass(frozen=True)
class ExtractedValue:
    """One metric reading the LLM pulled from the document text.

    Carries the metric code, the parsed numeric value, the reporting period it
    belongs to, the page it came from, and the model's self-reported
    confidence. The pipeline maps this onto a `MetricValueRecord`.
    """

    metric_code: str
    value: Decimal  # final value: raw-as-printed * scale * sign (applied in _row_to_value)
    unit: str
    period_kind: str  # 'annual' | 'monthly' | ...
    period_year: int
    page_number: int
    confidence: Decimal
    period_month: Optional[int] = None
    note: Optional[str] = None
    source_quote: Optional[str] = None  # verbatim snippet the number was read from (verify/review aid)
    printed_scale: str = "units"  # 'units' | 'thousands' | 'millions' (the table's stated units)
    printed_sign: str = "positive"  # 'negative' for accounting parentheses, e.g. (1,234)
    service_scope: str = "total"  # 'total'|'conventional'|'specialized'|'system_wide'|'mode_subset'|'city_wide'
    basis: str = "actual"  # 'actual'|'budget'|'forecast'|'restated'
    # Expense-line accounting basis; a DIFFERENT axis from `basis` above.
    cost_basis: str = "operating"  # 'operating' (excl. amortization) | 'psab_total' (incl.)
    printed_label: Optional[str] = None  # verbatim printed row/line label the number was read from
    table_reference: Optional[str] = None  # statement/note/schedule id, e.g. "Note 7", "Schedule 2"


def value_to_dict(v: ExtractedValue) -> dict:
    """Serialize an ExtractedValue to a plain JSON-able dict (round-trips via
    value_from_dict). Decimal fields become str(...); everything else is as-is."""
    return {
        "metric_code": v.metric_code,
        "value": str(v.value),
        "unit": v.unit,
        "period_kind": v.period_kind,
        "period_year": v.period_year,
        "page_number": v.page_number,
        "confidence": str(v.confidence),
        "period_month": v.period_month,
        "note": v.note,
        "source_quote": v.source_quote,
        "printed_scale": v.printed_scale,
        "printed_sign": v.printed_sign,
        "service_scope": v.service_scope,
        "basis": v.basis,
        "cost_basis": v.cost_basis,
        "printed_label": v.printed_label,
        "table_reference": v.table_reference,
    }


def value_from_dict(d: dict) -> ExtractedValue:
    """Inverse of value_to_dict: Decimal fields parsed back via Decimal(...)."""
    return ExtractedValue(
        metric_code=d["metric_code"],
        value=Decimal(d["value"]),
        unit=d["unit"],
        period_kind=d["period_kind"],
        period_year=d["period_year"],
        page_number=d["page_number"],
        confidence=Decimal(d["confidence"]),
        period_month=d["period_month"],
        note=d["note"],
        source_quote=d["source_quote"],
        printed_scale=d["printed_scale"],
        printed_sign=d["printed_sign"],
        service_scope=d.get("service_scope", "total"),
        basis=d.get("basis", "actual"),
        cost_basis=d.get("cost_basis", "operating"),
        printed_label=d.get("printed_label"),
        table_reference=d.get("table_reference"),
    )


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
- period_year is the calendar year the reporting period ENDS in. A calendar-year
  agency's 2024 figure -> 2024. A fiscal-year agency is named by its end year:
  a fiscal year running April 2023 -> March 2024 -> period_year 2024. Put the
  fiscal-year span (e.g. "fiscal year ending March 2024") in `note`.
- Report the number EXACTLY AS PRINTED, as a plain number (no thousands
  separators). Do NOT scale it yourself: set `printed_scale` to the table's
  stated units ('units'|'thousands'|'millions') and the code applies the
  multiplier. This splits the labour -- you read the digits + the units header
  (reliable); the code does the long-number arithmetic (exact, auditable).
- Set `printed_sign` to 'negative' for an accounting-bracketed figure like
  "(1,234)"; otherwise 'positive'.
- Canadian/French documents write a comma decimal ("12,5" = 12.5) and spaces as
  thousands separators ("1 234 567"); report the plain magnitude (e.g. 12.5).
- confidence is 0..1. If you are NOT sure a figure maps to one of the codes,
  emit it with LOW confidence (below 0.7) rather than guessing or omitting it --
  do not silently drop uncertain figures. Never fabricate a value.
- source_quote is REQUIRED: the verbatim on-page text you read the number from,
  containing the digits as printed.
- Put any caveat (footnote, restated, partial year) in `note`.
- service_scope: 'total' = whole agency. 'conventional'/'specialized'
  (paratransit)/'system_wide' as labeled by the source. 'mode_subset' = one mode
  only (bus-only, subway-only). 'city_wide' = a whole-city figure (city
  consolidated statements), not the transit service.
- basis: 'actual' = reported result; 'budget'/'forecast' = planned or projected
  figures (multi-year plans, budget columns); 'restated' = a prior-year figure
  restated.
- A 'planned', 'projected', 'budget' or future-year figure is NEVER basis='actual'.
- cost_basis (EXPENSE LINES ONLY -- operating_expenses, labour_cost,
  energy_fuel_cost, materials_services_cost, other_operating_expenses,
  total_expenses; a DIFFERENT axis from `basis` above): 'psab_total' when the
  figure is a PSAB statement-of-operations total that INCLUDES amortization/
  depreciation (the audited "Total expenses" line and its components); 'operating'
  when the source states the operating basis EXCLUDES amortization (a CUTA-style
  "(excludes amortization)"/"direct operating cost" figure). If unsure, an audited
  statement-of-operations expense is 'psab_total'. Leave 'operating' for
  non-expense metrics.
- For financial-statement lines, set `printed_label` to the exact printed line
  label (e.g. "Tangible capital assets") and `table_reference` to the statement,
  note, or schedule it came from (e.g. "Statement of Financial Position",
  "Note 7", "Schedule 2").
- Consolidated municipalities: if a city-wide financial statement does NOT break
  out the transit agency as its own segment/schedule, do NOT map the city-wide
  figures to the agency -- skip them and record the gap in `note`. Never
  attribute a whole municipality's balance sheet to its transit system.

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
                        "period_year": {
                            "type": "integer",
                            "description": "Calendar year the reporting period ENDS in (a fiscal year ending March 2024 -> 2024).",
                        },
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
                        "printed_scale": {
                            "type": "string",
                            "enum": ["units", "thousands", "millions"],
                            "description": "The table's stated units; code multiplies by 1/1e3/1e6.",
                        },
                        "printed_sign": {
                            "type": "string",
                            "enum": ["positive", "negative"],
                            "description": "'negative' for accounting parentheses, e.g. (1,234).",
                        },
                        "service_scope": {
                            "type": "string",
                            "enum": [
                                "total",
                                "conventional",
                                "specialized",
                                "system_wide",
                                "mode_subset",
                                "city_wide",
                            ],
                            "description": "'total' = whole agency. 'conventional'/'specialized' (paratransit)/'system_wide' as labeled by the source. 'mode_subset' = one mode only (bus-only, subway-only). 'city_wide' = a whole-city figure (city consolidated statements), not the transit service.",
                        },
                        "basis": {
                            "type": "string",
                            "enum": ["actual", "budget", "forecast", "restated"],
                            "description": "'actual' = reported result; 'budget'/'forecast' = planned or projected figures (multi-year plans, budget columns); 'restated' = a prior-year figure restated.",
                        },
                        "cost_basis": {
                            "type": "string",
                            "enum": ["operating", "psab_total"],
                            "description": "EXPENSE LINES ONLY (different axis from `basis`): 'psab_total' = a PSAB statement-of-operations expense total that INCLUDES amortization/depreciation; 'operating' = a CUTA-style operating figure the source states EXCLUDES amortization. Default 'operating' for non-expense metrics.",
                        },
                        "printed_label": {
                            "type": ["string", "null"],
                            "description": "Verbatim printed row/line label the number was read from.",
                        },
                        "table_reference": {
                            "type": ["string", "null"],
                            "description": "Statement/note/schedule id, e.g. 'Note 7', 'Schedule 2'.",
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
                        "source_quote",
                    ],
                },
            }
        },
        "required": ["values"],
    },
}


def parse_number(raw: object) -> Decimal:
    """Parse a number string into Decimal, tolerating Canadian/French formats.

    Handles space / non-breaking-space thousands separators ('1 234 567'),
    English-Canadian comma thousands separators ('1,234', '250,000,000',
    '1,234.56'), and a French comma decimal ('12,5'). Plain ints/Decimals pass
    straight through.
    """
    if isinstance(raw, Decimal):
        return raw
    if isinstance(raw, int):  # bool excluded: handled by Decimal path below
        return Decimal(raw)
    text = str(raw).strip()
    # Accounting negative: "(1,234)" -> negative. A safety net for when the model
    # forgets printed_sign; strip the parentheses and negate at the end.
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1].strip()
    # Strip space-family thousands separators (regular, non-breaking, narrow nbsp).
    for sep in (" ", " ", " "):
        text = text.replace(sep, "")
    # Disambiguate the comma (only meaningful once spaces are gone). With a period
    # present the comma can only be an English thousands separator ("1,234.56" ->
    # "1234.56"). Otherwise a lone comma trailing 1-2 digits is a French/European
    # decimal ("12,5" -> "12.5"); any other comma grouping is English thousands
    # separators ("250,000,000" / "1,234" -> strip them). The previous code treated
    # every comma as a decimal point, silently turning "1,234" into 1.234.
    if "." in text:
        text = text.replace(",", "")
    elif "," in text:
        if re.fullmatch(r"-?\d+,\d{1,2}", text):
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"could not parse number: {raw!r}") from exc
    return -value if negative else value


# Layout noise to drop before matching a printed value against a quote.
_QUOTE_SPACES = (" ", " ", " ")  # regular, non-breaking, narrow nbsp
_QUOTE_STRIP = _QUOTE_SPACES + (",", "(", ")")


def _strip_chars(text: str, chars: tuple[str, ...]) -> str:
    for ch in chars:
        text = text.replace(ch, "")
    return text


def quote_supports_value(printed: str, quote: Optional[str]) -> Optional[str]:
    """Does the source quote contain the value's printed digits?

    Returns None when the quote contains the printed value, 'missing' when there
    is no quote, and 'mismatch' when a quote exists but the digits aren't in it.
    Both strings are normalized (spaces / commas / accounting parens stripped);
    the comma-decimal variant of `printed` is also tried so an English-printed
    "525.5" matches a French-quoted "525,5". Compare on the as-printed string,
    never the scaled Decimal."""
    if quote is None or quote.strip() == "":
        return "missing"
    printed_norm = _strip_chars(printed, _QUOTE_STRIP)
    quote_norm = _strip_chars(quote, _QUOTE_STRIP)
    if printed_norm in quote_norm:
        return None
    # French quotes write a comma decimal ("525,5"); the English-printed "525.5"
    # would have lost its comma in normalization, so match the decimal variant
    # against a comma-preserving normalization of the quote.
    if "." in printed:
        comma_variant = _strip_chars(printed, _QUOTE_SPACES).replace(".", ",")
        if comma_variant in _strip_chars(quote, _QUOTE_SPACES + ("(", ")")):
            return None
    return "mismatch"


# Multiplier for the model-declared printed_scale; code applies it (not the model).
_SCALE_FACTOR = {
    "units": Decimal(1),
    "thousands": Decimal(1000),
    "millions": Decimal(1_000_000),
}


def apply_scale_sign(raw: Decimal, printed_scale: str, printed_sign: str) -> Decimal:
    """Final value = raw-as-printed * scale-multiplier * sign. Keeping this in code
    (not the model) makes every scaling/sign decision deterministic and auditable."""
    factor = _SCALE_FACTOR.get(printed_scale, Decimal(1))
    sign = Decimal(-1) if printed_sign == "negative" else Decimal(1)
    return raw * factor * sign


def _append_note(note: Optional[str], addition: str) -> str:
    """Append addition to note, semicolon-separated, preserving any existing note."""
    return f"{note}; {addition}" if note else addition


def _row_to_value(row: dict) -> ExtractedValue:
    """Build an ExtractedValue from one structured-output row (tool input).

    The model reports the number as printed plus printed_scale/printed_sign; the
    final value applies the scale multiplier and sign here in code. The free-text
    `unit` is discarded in favour of the metric's canonical unit, and a missing or
    non-corroborating `source_quote` caps confidence (see quote_supports_value)."""
    printed_scale = row.get("printed_scale") or "units"
    printed_sign = row.get("printed_sign") or "positive"
    service_scope = row.get("service_scope") or "total"
    basis = row.get("basis") or "actual"
    cost_basis = row.get("cost_basis") or "operating"
    value = apply_scale_sign(parse_number(row["value"]), printed_scale, printed_sign)
    confidence = Decimal(str(row["confidence"]))
    note = row.get("note")
    if basis == "restated":
        note = _append_note(note, "restated figure")
    source_quote = row.get("source_quote")
    # Check the as-printed digits against the model's quote, never the scaled Decimal.
    support = quote_supports_value(str(row["value"]), source_quote)
    if support == "missing":
        confidence = min(confidence, QUOTE_MISSING_CONFIDENCE_CAP)
        note = _append_note(note, "no source quote")
    elif support == "mismatch":
        confidence = min(confidence, QUOTE_MISMATCH_CONFIDENCE_CAP)
        note = _append_note(note, "⚠ value not found in its source quote")
    return ExtractedValue(
        metric_code=row["metric_code"],
        value=value,
        unit=METRICS[row["metric_code"]]["unit"],
        period_kind=row["period_kind"],
        period_year=int(row["period_year"]),
        page_number=int(row["page_number"]),
        confidence=confidence,
        period_month=(
            int(row["period_month"]) if row.get("period_month") is not None else None
        ),
        note=note,
        source_quote=source_quote,
        printed_scale=printed_scale,
        printed_sign=printed_sign,
        service_scope=service_scope,
        basis=basis,
        cost_basis=cost_basis,
        printed_label=row.get("printed_label"),
        table_reference=row.get("table_reference"),
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
        # 8192, not 4096: a multi-year stats table is 30-40 tool rows, which
        # overruns 4096 and truncates the tool-call JSON to nothing (stop_reason
        # 'max_tokens', zero values parsed). Matches the vision extractor.
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 8192,
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
