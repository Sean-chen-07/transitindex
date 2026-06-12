"""The default real extractor: whole-PDF native vision via Claude.

`ClaudePdfExtractor` sends the entire PDF to Claude as a base64 'document'
content block so the model reads numbers visually from tables, charts, and
figures -- not from flattened text. It forces structured output with the same
`record_metrics` tool the legacy client uses, caches the document block (so a
re-run of the SAME call shape is cheap), and re-checks every extracted number
against the PDF -- lowering confidence or dropping values the model can no
longer support. (The verify pass sends a different tools array than the extract
pass, so its document upload is a fresh cache write, not a read.) PDFs over
Anthropic's per-request limits (100 pages / 32 MB) are split into page-range
chunks with pypdf and merged.

`anthropic` and `pypdf` are imported lazily inside methods, so importing this
module needs neither dependency (the offline suite never instantiates the
class; it injects a fake client).
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Optional

from .extractor import ExtractionRequest, ExtractionResult
from .llm import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_TOOL,
    ExtractedValue,
    _row_to_value,
    apply_scale_sign,
    parse_number,
)

# Anthropic per-request PDF limits (200k-context models): split past either one.
ANTHROPIC_MAX_PAGES = 100
ANTHROPIC_MAX_BYTES = 32 * 1024 * 1024  # 32 MB

# Rough Sonnet 4.x input rate ($3 / MTok). A display aid for pdf-smoke only --
# NOT billing. est_cost_usd sums the ACTUAL reported token usage (including the
# verify pass's fresh document upload), so it stays accurate regardless of caching.
_USD_PER_INPUT_TOKEN = 3.0 / 1_000_000

# Vision-tuned variant of the extraction instructions. Reuses the same tool
# (record_metrics) so the parsing path is identical, but tells the model it is
# LOOKING at the PDF (tables, charts, figures) and must fill source_quote.
VISION_EXTRACTION_SYSTEM_PROMPT = EXTRACTION_SYSTEM_PROMPT + """

You are looking at the ORIGINAL PDF pages (tables, charts, figures), not a text
dump. Read numbers visually from tables and chart axes/labels. For every value,
set page_number to the PDF page you saw it on and put the exact on-page text you
read it from (a cell, label, or sentence) in source_quote.
"""

_vision_prompt_cache: Optional[str] = None


def _vision_system_prompt() -> str:
    """VISION_EXTRACTION_SYSTEM_PROMPT enriched with per-metric guidance from the
    data dictionary (definitions, EN+FR labels, where each figure lives, common
    confusions). Built lazily -- the dictionary needs PyYAML -- and cached; falls
    back to the base prompt if the dictionary can't be loaded. Only the real
    (Anthropic) path calls this, never the offline suite's fakes."""
    global _vision_prompt_cache
    if _vision_prompt_cache is None:
        try:
            from ..dictionary import extraction_guidance

            _vision_prompt_cache = (
                VISION_EXTRACTION_SYSTEM_PROMPT
                + "\n\nMetric guide — map each figure to the right code and mind the "
                "confusions:\n" + extraction_guidance()
            )
        except Exception:
            _vision_prompt_cache = VISION_EXTRACTION_SYSTEM_PROMPT
    return _vision_prompt_cache

# Verify-pass tool: the model re-checks each candidate against the cached PDF.
# Corrections follow the same labour split as extraction (see EXTRACTION_TOOL):
# the model reports the number AS PRINTED plus the table's stated scale/sign,
# and the code applies the multiplier in _merge_verify. Without this, a model
# echoing the printed digits of a "$000s" table would rescale the value 1000x.
VERIFY_TOOL = {
    "name": "verify_metrics",
    "description": "Re-check each proposed metric value against what the PDF actually shows.",
    "input_schema": {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "supported": {"type": "boolean"},
                        "corrected_value": {
                            "type": ["string", "null"],
                            "description": (
                                "If the printed number differs, the number EXACTLY AS "
                                "PRINTED (no scaling); set printed_scale for its table."
                            ),
                        },
                        "printed_scale": {
                            "type": "string",
                            "enum": ["units", "thousands", "millions"],
                            "description": (
                                "Stated units of the table corrected_value was read "
                                "from; code multiplies by 1/1e3/1e6."
                            ),
                        },
                        "printed_sign": {
                            "type": "string",
                            "enum": ["positive", "negative"],
                            "description": "'negative' for accounting parentheses, e.g. (1,234).",
                        },
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                        "source_quote": {"type": ["string", "null"]},
                    },
                    "required": ["index", "supported", "confidence"],
                },
            }
        },
        "required": ["results"],
    },
}


# --- page prefilter ---------------------------------------------------------
# Words that signal a page carries the metrics we source. Lowercase substrings;
# kept broad on purpose (recall matters more than precision -- the worst case is
# sending a spare page or two, the bad case is dropping the page with the number).
_METRIC_KEYWORDS: tuple[str, ...] = (
    "ridership", "rider", "boarding", "revenue ride", "passenger", "trip", "journey",
    "revenue", "fare", "farebox",
    "expenditure", "expense", "operating cost", "operating budget", "budget", "subsidy", "funding",
    "service hour", "revenue hour", "vehicle hour",
    "service kilom", "service km", "vehicle kilom", "vehicle km",
    "fleet", "buses", "vehicle", "streetcar", "train",
    "on-time", "on time", "punctual", "reliabilit", "performance",
    "employee", "position", "staff", "headcount", "fte",
    # EN + FR financial-statement anchors (page text is lowercased before
    # matching; keep accented forms AND unaccented variants, since text
    # extraction commonly strips accents).
    "statement of financial position", "etat de la situation financiere",
    "état de la situation financière",
    "statement of operations", "état des résultats", "etat des resultats",
    "net debt", "dette nette",
    "tangible capital", "immobilisations corporelles",
    "financial assets", "actifs financiers",
    "liabilities", "passif",
    "accumulated surplus", "excédent accumulé", "excedent accumule",
    "achalandage", "heures de service",
    "kilomètres parcourus", "kilometres parcourus",
)
# A run of digits (optionally with thousands/decimal separators) -- a data-density proxy.
_NUMBER_RE = re.compile(r"\d[\d,.]*\d")

# Always send the front-matter pages: transit reports put headline figures (and
# numbers that appear nowhere else, like total fleet or service-km) in the
# executive summary up front, where number density alone may not rank them in.
_HEAD_PAGES = 3


def score_page(text: str) -> int:
    """Relevance score for one page's text: metric keywords weighted over number density."""
    low = text.lower()
    keyword_hits = sum(low.count(kw) for kw in _METRIC_KEYWORDS)
    number_hits = len(_NUMBER_RE.findall(text))
    return keyword_hits * 5 + min(number_hits, 40)


def select_page_indices(page_texts: list[str], max_pages: int) -> list[int]:
    """Pick the (0-based) page indices worth sending to vision, in document order.

    Always keeps the first _HEAD_PAGES (the summary), then fills the rest of the
    max_pages budget with the highest-scoring remaining pages. If a doc already
    fits in max_pages, sends all of it. If nothing scores (e.g. a scanned PDF whose
    text didn't extract), the head pages still go, so we never send nothing.
    """
    n = len(page_texts)
    if n <= max_pages:
        return list(range(n))

    head = list(range(min(_HEAD_PAGES, max_pages)))
    head_set = set(head)
    scored = [(score_page(t), i) for i, t in enumerate(page_texts) if i not in head_set]
    candidates = [(s, i) for s, i in scored if s > 0] or scored
    candidates.sort(key=lambda si: (si[0], -si[1]), reverse=True)
    remaining = max_pages - len(head)
    keep = head_set | {i for _, i in candidates[:remaining]}
    return sorted(keep)


class ClaudePdfExtractor:
    """Extractor that reads the WHOLE PDF with Claude's native vision.

    Sends the PDF as a base64 'document' content block (cache_control on it so a
    re-run of the same call shape is cheap), forces structured output via
    EXTRACTION_TOOL, then runs a VERIFY pass that re-checks each number against
    the PDF -- lowering confidence or dropping values the model can no longer
    support. The verify pass uses a different tools array than extract, so its
    document upload is a fresh cache write, not a read. PDFs over Anthropic's
    100-page / 32 MB per-request limit are split into page-range chunks (pypdf)
    and merged.

    anthropic and pypdf are imported lazily, so importing this module needs
    neither dependency (the offline suite never instantiates this class).
    """

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        verify: bool = True,
        max_tokens: int = 8192,
        prefilter: bool = True,
        max_pages: int = 15,
    ) -> None:
        import anthropic  # lazy: real API path only

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._verify = verify
        self._max_tokens = max_tokens
        self._prefilter = prefilter
        self._max_pages = max_pages

    # --- public seam ---------------------------------------------------------

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        pdf_bytes = request.pdf_bytes
        if pdf_bytes is None:
            # Offline / pages-only fallback: no bytes to send to vision. Flatten
            # the supplied pages to text and run the legacy text path so this
            # extractor still works when handed pages (keeps the seam total).
            return self._extract_from_pages(request)

        # Prefilter: send only the metric-dense pages to vision. Keeps each call
        # under the per-minute token rate limit and cuts cost; page_map re-bases
        # the model's page numbers back onto the original document.
        page_map: Optional[dict[int, int]] = None
        pages_total: Optional[int] = None
        pages_selected: Optional[list[int]] = None
        if self._prefilter:
            pdf_bytes, page_map, pages_total, pages_selected = self._filter_pdf(pdf_bytes)

        chunks, page_count = self._split_if_needed(pdf_bytes)
        if pages_total is None:
            pages_total = page_count

        all_values: list[ExtractedValue] = []
        diag = {
            "model": self._model,
            "chunks": len(chunks),
            "page_count": pages_total,
            "pages_sent": page_count,
            "input_tokens": 0,
            "est_cost_usd": 0.0,
            "verify_dropped": 0,
        }
        if pages_selected is not None:
            diag["pages_selected"] = pages_selected

        for b64, page_offset in chunks:
            values, usage = self._extract_chunk(b64, request)
            if self._verify and values:
                values, dropped = self._verify_chunk(b64, request, values)
                diag["verify_dropped"] += dropped
            # Re-base page_number onto the sent-document numbering, then (if we
            # prefiltered) back onto the original document's page numbers.
            values = [self._reoffset(v, page_offset) for v in values]
            if page_map is not None:
                values = [self._remap_page(v, page_map) for v in values]
            all_values.extend(values)
            self._accumulate_usage(diag, usage)

        diag["est_cost_usd"] = self._estimate_cost(diag["input_tokens"])
        return ExtractionResult(values=all_values, diagnostics=diag)

    # --- one extract call (document + forced tool + caching) -----------------

    def _document_block(self, b64: str, media_type: str) -> dict:
        """The base64 PDF content block, cached so a re-run of the same call shape is a hit."""
        return {
            "type": "document",
            "source": {"type": "base64", "media_type": media_type, "data": b64},
            "cache_control": {"type": "ephemeral"},
        }

    def _tool_rows(self, message, tool_name: str) -> list[dict]:
        """Pull the metric rows out of a forced tool_use response (same loop as legacy)."""
        for block in message.content:
            if getattr(block, "type", None) == "tool_use" and block.name == tool_name:
                return block.input.get("values", [])
        return []

    def _extract_chunk(self, b64: str, request: ExtractionRequest):
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=[
                {
                    "type": "text",
                    "text": _vision_system_prompt(),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": EXTRACTION_TOOL["name"]},
            messages=[
                {
                    "role": "user",
                    "content": [
                        self._document_block(b64, request.media_type),
                        {
                            "type": "text",
                            "text": (
                                f"Agency: {request.agency_slug}\n\n"
                                "Extract every sourced metric you can read in this PDF."
                            ),
                        },
                    ],
                }
            ],
        )
        rows = self._tool_rows(message, EXTRACTION_TOOL["name"])
        # Be defensive: a weaker/truncated model can hand back a malformed row
        # (a bare string, a missing key). Skip those rather than crash the run.
        values: list[ExtractedValue] = []
        for r in rows:
            if not isinstance(r, dict):
                continue
            try:
                values.append(_row_to_value(r))
            except (KeyError, ValueError, TypeError):
                continue
        return values, message.usage

    # --- the verify second pass (same cached document) -----------------------

    def _verify_chunk(self, b64: str, request: ExtractionRequest, values):
        """Re-check each candidate against the cached PDF; lower/correct/drop."""
        catalogue = "\n".join(
            f"{i}: {v.metric_code} = {v.value} {v.unit} "
            f"({v.period_kind} {v.period_year}"
            + (f"-{v.period_month:02d}" if v.period_month else "")
            + f"), page {v.page_number}"
            + self._printed_note(v)
            for i, v in enumerate(values)
        )
        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=[
                {
                    "type": "text",
                    "text": _vision_system_prompt(),
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            tools=[VERIFY_TOOL],
            tool_choice={"type": "tool", "name": VERIFY_TOOL["name"]},
            messages=[
                {
                    "role": "user",
                    "content": [
                        self._document_block(b64, request.media_type),
                        {
                            "type": "text",
                            "text": (
                                "Re-check each proposed value below against the PDF. "
                                "Each proposed value is the FINAL value after applying "
                                "the table's stated units — e.g. printed 2,240 in a "
                                "($000s) table appears below as 2240000, marked "
                                "[printed in thousands]. For each index, set "
                                "supported=false if you cannot find it. If the page "
                                "shows a different number than the proposal implies, "
                                "give corrected_value EXACTLY AS PRINTED (no scaling) "
                                "and set printed_scale/printed_sign for the table you "
                                "read it from — the code applies the multiplier, same "
                                "as extraction. Report your confidence and the "
                                "source_quote you saw.\n\n"
                                + catalogue
                            ),
                        },
                    ],
                }
            ],
        )
        results = self._verify_results(message)
        return self._merge_verify(values, results)

    def _printed_note(self, v: ExtractedValue) -> str:
        """Catalogue marker for a value whose printed form was scaled/signed, so the
        verify model knows the proposal is the FINAL value, not the printed digits."""
        parts = []
        if v.printed_scale != "units":
            parts.append(f"printed in {v.printed_scale}")
        if v.printed_sign == "negative":
            parts.append("printed in accounting parentheses")
        return f" [{'; '.join(parts)}]" if parts else ""

    def _verify_results(self, message) -> dict:
        """index -> result dict from the verify_metrics tool_use block."""
        for block in message.content:
            if (
                getattr(block, "type", None) == "tool_use"
                and block.name == VERIFY_TOOL["name"]
            ):
                return {r["index"]: r for r in block.input.get("results", [])}
        return {}

    def _merge_verify(self, values, results):
        """Apply verify results: drop unsupported, lower confidence, correct values."""
        kept: list[ExtractedValue] = []
        dropped = 0
        for i, v in enumerate(values):
            r = results.get(i)
            if r is None:
                kept.append(v)  # no verdict -> keep as-is
                continue
            if not r.get("supported", True):
                dropped += 1
                continue

            confidence = v.confidence
            returned = r.get("confidence")
            if returned is not None:
                confidence = min(confidence, parse_number(returned))  # verify only lowers

            value = v.value
            note = v.note
            printed_scale = v.printed_scale
            printed_sign = v.printed_sign
            corrected = r.get("corrected_value")
            if corrected is not None:
                # Corrections arrive AS PRINTED (mirroring extraction); the scale/
                # sign multiplier is applied here in code. A correction that omits
                # them inherits the original reading's — same table, same units
                # header — so a model echoing the printed digits of a scaled table
                # can never rescale the value.
                printed_scale = r.get("printed_scale") or v.printed_scale
                printed_sign = r.get("printed_sign") or v.printed_sign
                new_value = apply_scale_sign(
                    parse_number(corrected), printed_scale, printed_sign
                )
                if new_value != v.value:
                    note = (
                        f"verify-corrected from {v.value}"
                        if not note
                        else f"{note}; verify-corrected from {v.value}"
                    )
                    value = new_value

            source_quote = v.source_quote or r.get("source_quote")

            kept.append(
                replace(
                    v,
                    confidence=confidence,
                    value=value,
                    note=note,
                    source_quote=source_quote,
                    printed_scale=printed_scale,
                    printed_sign=printed_sign,
                )
            )
        return kept, dropped

    # --- size / page guard (lazy pypdf, chunk + merge) -----------------------

    def _split_if_needed(self, pdf_bytes: bytes):
        """Return ([(base64_chunk, page_offset), ...], total_page_count).

        If the PDF is within 100 pages AND 32 MB, returns one chunk at offset 0.
        Otherwise splits into <=100-page ranges (halving any range whose
        serialized chunk still exceeds 32 MB) and records each chunk's 0-based
        starting page so page_number can be re-based onto the whole document.
        """
        import base64
        from io import BytesIO

        from pypdf import PdfReader  # lazy: chunking only

        reader = PdfReader(BytesIO(pdf_bytes))
        n = len(reader.pages)

        if n <= ANTHROPIC_MAX_PAGES and len(pdf_bytes) <= ANTHROPIC_MAX_BYTES:
            return [(base64.standard_b64encode(pdf_bytes).decode("utf-8"), 0)], n

        chunks: list[tuple[str, int]] = []
        start = 0
        while start < n:
            window = min(ANTHROPIC_MAX_PAGES, n - start)
            self._emit_window(reader, start, window, chunks)
            start += window
        return chunks, n

    def _emit_window(self, reader, start: int, window: int, chunks: list) -> None:
        """Serialize pages [start, start+window) to base64; halve if over 32 MB."""
        import base64
        from io import BytesIO

        from pypdf import PdfWriter  # lazy: chunking only

        writer = PdfWriter()
        for i in range(start, start + window):
            writer.add_page(reader.pages[i])
        buf = BytesIO()
        writer.write(buf)
        data = buf.getvalue()

        if len(data) > ANTHROPIC_MAX_BYTES and window > 1:
            half = window // 2
            self._emit_window(reader, start, half, chunks)
            self._emit_window(reader, start + half, window - half, chunks)
            return

        chunks.append((base64.standard_b64encode(data).decode("utf-8"), start))

    def _reoffset(self, v: ExtractedValue, page_offset: int) -> ExtractedValue:
        """Re-base a chunk-local page number onto whole-document numbering."""
        if page_offset == 0:
            return v
        return replace(v, page_number=v.page_number + page_offset)

    # --- prefilter (lazy pypdf: read text, keep the dense pages) --------------

    def _filter_pdf(self, pdf_bytes: bytes):
        """Return (filtered_pdf, page_map, total_pages, selected_pages).

        Reads per-page text with pypdf, keeps the metric-dense pages (up to
        max_pages), and rebuilds a smaller PDF of just those. page_map maps a
        page number in the filtered PDF (1-based) to its original page number;
        selected_pages lists the original page numbers kept. If nothing is
        filtered out, returns the original bytes with page_map=None (no remap).
        """
        from io import BytesIO

        from pypdf import PdfReader, PdfWriter  # lazy: prefilter only

        reader = PdfReader(BytesIO(pdf_bytes))
        total = len(reader.pages)
        texts = [(page.extract_text() or "") for page in reader.pages]
        keep = select_page_indices(texts, self._max_pages)

        if len(keep) >= total:
            return pdf_bytes, None, total, list(range(1, total + 1))

        writer = PdfWriter()
        page_map: dict[int, int] = {}
        for new_pos, orig_idx in enumerate(keep, start=1):
            writer.add_page(reader.pages[orig_idx])
            page_map[new_pos] = orig_idx + 1
        buf = BytesIO()
        writer.write(buf)
        return buf.getvalue(), page_map, total, [i + 1 for i in keep]

    def _remap_page(self, v: ExtractedValue, page_map: dict[int, int]) -> ExtractedValue:
        """Map a filtered-PDF page number back to the original document's page."""
        orig = page_map.get(v.page_number)
        if orig is None or orig == v.page_number:
            return v
        return replace(v, page_number=orig)

    # --- diagnostics ---------------------------------------------------------

    def _accumulate_usage(self, diag: dict, usage) -> None:
        diag["input_tokens"] += int(getattr(usage, "input_tokens", 0) or 0)
        diag["input_tokens"] += int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        diag["input_tokens"] += int(getattr(usage, "cache_read_input_tokens", 0) or 0)

    def _estimate_cost(self, input_tokens: int) -> float:
        return input_tokens * _USD_PER_INPUT_TOKEN

    # --- pages-only safety net -----------------------------------------------

    def _extract_from_pages(self, request: ExtractionRequest) -> ExtractionResult:
        """Flatten pages to text and run the legacy text extraction (no vision)."""
        from .llm import AnthropicLLMClient

        pages = request.pages or []
        document_text = "\n\n".join(text for _, text in pages)
        # Reuse the legacy text client's extract via a throwaway that shares our
        # already-constructed Anthropic client.
        legacy = AnthropicLLMClient.__new__(AnthropicLLMClient)
        legacy._client = self._client
        legacy._model = self._model
        legacy._max_tokens = self._max_tokens
        values = legacy.extract(
            EXTRACTION_SYSTEM_PROMPT, document_text, request.agency_slug
        )
        return ExtractionResult(
            values=values, diagnostics={"model": self._model, "extractor": "pages_text"}
        )
