"""The default extractor: chunked hybrid (markitdown text + scanned-page images).

This is what real scanning runs. It never hands Claude a whole 30-page PDF or a
2000-line markdown in one shot. Instead it breaks the document into bite-size
segments, extracts each independently (in parallel), and merges:

  - markitdown converts the text layer to markdown, split into chunks ONLY at
    paragraph boundaries (blank lines) and packed to ~target_lines. A paragraph or a
    whole table is never split (a table has no blank line inside it, so its header
    stays with its rows), and NO content is duplicated between chunks.
  - the pages with no text layer (scans/figures markitdown can't read) are sent as
    images, in small batches (a few pages per call, not all at once); each page goes
    in exactly one batch.

Each segment is its own Claude call; results are merged and de-duped on
(metric, period): agreeing chunks collapse to the highest-confidence reading,
conflicting chunks are flagged for review.

A deterministic router (`route_chunk`, cue-matched against the dictionary's
`statements:` section) decides WHICH parser reads a segment. A chunk printing the
income statement goes to the income-statement SPECIALIST, one printing the balance
sheet to the balance-sheet SPECIALIST -- each with its statement's own brief, only
its slice of the metric canon, and a `record_metrics` schema whose metric_code enum
holds only its codes, so it structurally cannot record the other statement's
metrics. A chunk matching both is sent to both specialists and their readings meet
in the normal merge. Everything else -- service statistics, prose, scanned-page
images -- keeps the full-canon generalist call. There are exactly three prompt
variants, each fixed for the run, so each caches independently.

Per-segment model routing keeps the cost down: clean markdown text chunks (the bulk
of the tokens) go to a cheaper model (DEFAULT_TEXT_MODEL), and only the scanned-image
batches -- the genuinely hard read -- use the strong model (DEFAULT_IMAGE_MODEL).

It implements the `Extractor` seam (drop-in for run_pdf / scan / pdf-smoke).
`markitdown`, `anthropic`, and `pypdf` import lazily; `_to_markdown` /
`_image_page_batches` are module seams the offline tests monkeypatch, and `_client`
is injectable. No verify pass (cross-chunk merge + the pending-review queue cover it).
"""

from __future__ import annotations

import base64
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from typing import Optional

from ..refdata import agency_currency
from .ensemble import _key, _with_note
from .extractor import ExtractionRequest, ExtractionResult
from .llm import (
    COMPONENT_SUM_MARKER,
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_TOOL,
    SOURCED_METRIC_CODES,
    _row_to_value,
    extraction_system_prompt,
    extraction_tool,
    value_to_dict,
)
from .markitdown_path import IMAGE_TEXT_THRESHOLD, _INPUT_USD_PER_MTOK, _to_markdown

DEFAULT_TARGET_LINES = 350   # soft target lines per chunk; a single paragraph/table bigger than this is kept whole
DEFAULT_IMAGE_BATCH = 5      # scanned pages per image call -- not the whole 30-page scan at once
DEFAULT_IMAGE_OVERLAP = 0    # no overlap: each scanned page is sent in exactly one batch (no duplicate send)
DEFAULT_MAX_WORKERS = 4      # parallel segment calls (SDK retries 429s)
# Per-segment model routing: scanned-page images are the hard read (keep the strong
# model); clean markdown text is easy, so a cheaper model reads it at a fraction of the
# cost. Text is the bulk of the tokens, so this split is where most of the spend is saved.
DEFAULT_IMAGE_MODEL = "claude-opus-4-8"
DEFAULT_TEXT_MODEL = "claude-sonnet-4-6"
REVIEW_CONFIDENCE = Decimal("0.5")  # stamped on a cross-chunk disagreement so it surfaces for review
MERGE_REL_TOLERANCE = Decimal("0.005")  # readings within 0.5% are the same figure (rounded summary vs exact)
CONFIDENCE_FLOOR = Decimal("0.3")  # below this a reading is noise, not data -- dropped before merge

# Out-of-scope figures the metric set does not want at agency level: a single mode
# (bus-only) and whole-city consolidated figures are dropped after merge (step 2.3).
DROPPED_SCOPES = frozenset({"mode_subset", "city_wide"})
# Planned/projected figures are not actuals; 'restated' is an actual (just restated) and stays.
DROPPED_BASES = frozenset({"budget", "forecast"})

_SOURCED = frozenset(SOURCED_METRIC_CODES)  # codes a model may emit (derived are computed)


# --- markdown chunking (paragraph boundaries only) --------------------------


def _is_blank(line: str) -> bool:
    return not line.strip()


def _page_label(pages: list[int]) -> str:
    """Compact human label for a 1-based page list: [1,2,4,13,14] -> '1-2, 4, 13-14'.

    Consecutive runs collapse to 'start-end'; singletons stay bare. Keeps image-batch
    provenance honest when a batch spans non-contiguous scanned pages.
    """
    runs: list[str] = []
    start = prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
            continue
        runs.append(str(start) if start == prev else f"{start}-{prev}")
        start = prev = p
    runs.append(str(start) if start == prev else f"{start}-{prev}")
    return ", ".join(runs)


# A "(in thousands of dollars)" / "($000s)" / "(en milliers)" scale declaration, and a
# markdown heading line. Tracked so a chunk that lost its table's units header (or its
# section title) still carries that context into its segment prompt.
_SCALE_RE = re.compile(r"\((?:in\s+|en\s+)?(?:\$?\s*000s?|thousands|milliers|millions)[^)]*\)", re.IGNORECASE)
_HEADING_RE = re.compile(r"^#{1,6}\s+\S")


def chunk_markdown_with_context(md: str, *, target_lines: int = DEFAULT_TARGET_LINES) -> list[tuple[str, str]]:
    """Like chunk_markdown, but each chunk comes with a context header: the most
    recent markdown heading and the most recent scale declaration ('(in thousands
    of dollars)') seen in the document BEFORE the chunk's first line. Empty string
    when neither has occurred yet.

    Returns [(chunk_text, context_string), ...]. The context string format is
    `Context from earlier in the document — section: "<heading>"; scale declaration:
    "<match>"` with a missing part omitted.
    """
    # Build blocks, recording the heading/scale state in force at each block's start.
    blocks: list[list[str]] = []
    block_context: list[tuple[Optional[str], Optional[str]]] = []
    cur: list[str] = []
    last_heading: Optional[str] = None
    last_scale: Optional[str] = None
    for ln in md.splitlines():
        if _is_blank(ln):
            if cur:
                blocks.append(cur)
                cur = []
        else:
            if not cur:  # first line of a new block: snapshot the state before it
                block_context.append((last_heading, last_scale))
            if _HEADING_RE.match(ln):
                last_heading = ln.strip()
            m = _SCALE_RE.search(ln)
            if m:
                last_scale = m.group(0)
            cur.append(ln)
    if cur:
        blocks.append(cur)

    # Pack blocks into chunks (identical logic to chunk_markdown), carrying the
    # context of each chunk's FIRST block.
    chunks: list[list[str]] = []
    chunk_context: list[tuple[Optional[str], Optional[str]]] = []
    cur = []
    cur_context: tuple[Optional[str], Optional[str]] = (None, None)
    for blk, ctx in zip(blocks, block_context):
        if cur and len(cur) + len(blk) > target_lines:
            chunks.append(cur)
            chunk_context.append(cur_context)
            cur = []
        if cur:
            cur.append("")  # preserve the paragraph break between packed blocks
        else:
            cur_context = ctx
        cur.extend(blk)
    if cur:
        chunks.append(cur)
        chunk_context.append(cur_context)

    out: list[tuple[str, str]] = []
    for c, (heading, scale) in zip(chunks, chunk_context):
        text = "\n".join(c).strip()
        if not text:
            continue
        parts = []
        if heading:
            parts.append(f'section: "{heading}"')
        if scale:
            parts.append(f'scale declaration: "{scale}"')
        context = f"Context from earlier in the document — {'; '.join(parts)}" if parts else ""
        out.append((text, context))
    return out


def chunk_markdown(md: str, *, target_lines: int = DEFAULT_TARGET_LINES) -> list[str]:
    """Split markdown into chunks, cutting ONLY at paragraph boundaries (blank lines).

    A run of consecutive non-blank lines -- a paragraph, or a whole table (which has
    no blank line inside it, so its header stays with its rows) -- is the atomic unit.
    Blocks are packed up to ~target_lines and never split, so every chunk boundary
    falls at the end of a paragraph and NO content is duplicated between chunks. A
    single block larger than target_lines is kept whole as its own chunk rather than
    cut mid-paragraph.
    """
    return [text for text, _ in chunk_markdown_with_context(md, target_lines=target_lines)]


# --- statement routing (deterministic) --------------------------------------
#
# A chunk that clearly prints ONE financial statement goes to that statement's
# SPECIALIST call: a prompt built from the statement's own vocabulary + only that
# statement's slice of the metric canon, and a `record_metrics` schema whose
# metric_code enum holds only that statement's codes. Everything else (service
# statistics, prose, scanned-page images) keeps today's full-canon generalist call.

ROUTE_GENERAL = "general"
ROUTE_BOTH = "both"


def route_chunk(text: str, statements: dict) -> str:
    """Which statement specialist should read this text? Pure, deterministic.

    `text` is the chunk PLUS its context header (the header often carries the
    statement title the chunk itself lost). `statements` maps statement code ->
    `dictionary.StatementSpec`; a statement matches when any of its lowercase
    `cues` is a substring of the lowercased text.

    Returns the matching statement code, ROUTE_BOTH when both statements' cues
    appear (the chunk straddles them -- it goes to BOTH specialists), or
    ROUTE_GENERAL when nothing matches (or no specs are available at all).
    """
    hay = text.lower()
    hits = [
        code for code, spec in statements.items()
        if any(cue in hay for cue in spec.cues)
    ]
    if len(hits) > 1:
        return ROUTE_BOTH
    if hits:
        return hits[0]
    return ROUTE_GENERAL


def statement_prompt_block(spec) -> str:
    """The specialist's brief for one statement, built from its `StatementSpec`.

    Names it as printed (EN + FR), what the statement supplies (`notes`), and the
    look-alike statements/columns whose figures must never be recorded (the
    fiduciary fund, the city-wide consolidation, budget columns, ...).
    """
    lines = [
        f"*** YOU ARE THE {spec.display_name.upper()} SPECIALIST ***",
        "This segment was routed to you because it prints this statement. Extract "
        "ONLY figures belonging to it — the other statement has its own specialist "
        "parser, and its metric codes are not even available in your tool schema.",
    ]
    if spec.names_en:
        lines.append("Printed as (EN): " + "; ".join(spec.names_en))
    if spec.names_fr:
        lines.append("Printed as (FR): " + "; ".join(spec.names_fr))
    if spec.notes:
        lines.append("About this statement: " + " ".join(spec.notes.split()))
    if spec.never_extract:
        lines.append("NEVER extract these look-alikes:")
        lines.extend(f"  - {trap}" for trap in spec.never_extract)
    return "\n".join(lines)


# --- scanned-page batching --------------------------------------------------


def _image_page_batches(
    pdf_bytes: bytes,
    threshold: int,
    *,
    batch: int = DEFAULT_IMAGE_BATCH,
    overlap: int = DEFAULT_IMAGE_OVERLAP,
) -> list[tuple[str, list[int]]]:
    """Group the no-text-layer pages into small overlapping PDF batches.

    Returns [(base64 sub-PDF, [1-based page numbers]), ...]; [] if every page has a
    text layer. Each batch is at most `batch` consecutive low-text pages, sliding by
    `batch - overlap` so adjacent batches share a page.
    """
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(BytesIO(pdf_bytes))
    low = [
        i for i, p in enumerate(reader.pages)
        if len((p.extract_text() or "").strip()) < threshold
    ]
    if not low:
        return []

    step = max(1, batch - overlap)
    batches: list[tuple[str, list[int]]] = []
    i = 0
    n = len(low)
    while True:
        group = low[i:i + batch]
        writer = PdfWriter()
        for idx in group:
            writer.add_page(reader.pages[idx])
        buf = BytesIO()
        writer.write(buf)
        batches.append((base64.standard_b64encode(buf.getvalue()).decode("utf-8"), [g + 1 for g in group]))
        if i + batch >= n:
            break
        i += step
    return batches


# --- cross-chunk merge ------------------------------------------------------


def _within_merge_tolerance(values: list) -> bool:
    """Do these Decimals all describe the same figure (relative spread <= 0.5%)?

    spread = (max - min) / max(|max|, |min|). A rounded summary (12,060,000,000) and an
    exact statement (12,059,032,000) of the same total agree; a real restatement 1.2%
    apart does not. Guards the all-zero / zero-denominator case as agreement. Shared
    with eval/replay.py so the offline replay applies the identical rule.
    """
    max_v = max(values)
    min_v = min(values)
    denom = max(abs(max_v), abs(min_v))
    if denom == 0:  # every value is zero -> already equal
        return True
    return (max_v - min_v) / denom <= MERGE_REL_TOLERANCE


def _trailing_zeros(value: Decimal) -> int:
    """Count trailing zeros of the value's integer part (precision proxy: a rounded
    12,060,000,000 has more than the exact 12,059,032,000)."""
    digits = str(abs(int(value)))
    return len(digits) - len(digits.rstrip("0"))


def merge_values(values: list) -> list:
    """De-dupe values across chunks on (metric, period).

    One reading -> kept. Several agreeing (exactly equal OR within MERGE_REL_TOLERANCE)
    -> the most precise reading, lifted to the group's max confidence. Several that
    DISAGREE beyond tolerance -> highest-confidence one, dropped to REVIEW_CONFIDENCE
    with every candidate in the note (a chunk boundary or OCR slip surfaces for a human).
    """
    groups: dict = {}
    order: list = []
    for v in values:
        k = _key(v)
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(v)

    out: list = []
    for k in order:
        vs = groups[k]
        if len(vs) == 1:
            out.append(vs[0])
            continue
        best = max(vs, key=lambda v: v.confidence)
        max_conf = max(v.confidence for v in vs)
        if len({v.value for v in vs}) == 1:
            out.append(best)
        elif _within_merge_tolerance([v.value for v in vs]):
            # Agreement within 0.5%: keep the most precise reading (fewest trailing
            # zeros in the integer part; tie -> highest confidence), corroborated to max.
            precise = max(vs, key=lambda v: (-_trailing_zeros(v.value), v.confidence))
            out.append(
                replace(
                    precise,
                    confidence=max_conf,
                    note=_with_note(precise.note, f"✓ {len(vs)} readings agree within 0.5%"),
                )
            )
        else:
            detail = ", ".join(str(v.value) for v in sorted(vs, key=lambda v: -v.confidence))
            out.append(
                replace(
                    best,
                    confidence=min(best.confidence, REVIEW_CONFIDENCE),
                    note=_with_note(best.note, f"⚠ chunks disagree — {detail} (reviewer confirm)"),
                )
            )
    return out


# --- component readings: code adds, the model only transcribes ---------------
#
# The prompt forbids the model from doing arithmetic. When a statement prints the
# sub-lines that make up one of our metrics but no total line, the model emits one
# row per printed sub-line with `component_label` set; the deterministic aggregator
# below adds them up, keeps every addend's quote + page as provenance, and marks the
# result as summed-from-components so the reviewer can see it was never printed.



def _component_sum(values: list):
    """Fold one (metric, period, scope, basis) group of component rows into one value.

    Duplicate readings of the SAME printed sub-line (the same `component_label`
    seen in two chunks) collapse to the highest-confidence one first, so a chunk
    overlap can never double-count an addend. Confidence is the MINIMUM across
    the addends (a sum is only as good as its weakest line); the quotes, labels,
    and pages of every addend are kept in the note.
    """
    by_label: dict = {}
    for v in values:
        label = v.component_label or v.printed_label or str(v.page_number)
        prev = by_label.get(label)
        if prev is None or v.confidence > prev.confidence:
            by_label[label] = v
    addends = list(by_label.values())
    total = sum((v.value for v in addends), Decimal(0))
    detail = ", ".join(f"{v.component_label or '?'} {v.value} (p{v.page_number})" for v in addends)
    base = max(addends, key=lambda v: v.confidence)
    return replace(
        base,
        value=total,
        confidence=min(v.confidence for v in addends),
        component_label=None,
        note=_with_note(base.note, f"{COMPONENT_SUM_MARKER}: {detail}"),
        source_quote=" | ".join(v.source_quote for v in addends if v.source_quote) or None,
    )


def aggregate_components(values: list) -> list:
    """Sum component readings; cross-check them against a whole-metric reading.

    Splits `values` into whole-metric readings and `component_label` readings.
    Whole readings go through `merge_values` unchanged. Each component group is
    summed by `_component_sum`, then:

      * no whole reading for that key -> the sum IS the value (marked as summed);
      * a whole reading exists      -> the PRINTED total wins and the sum is only
        a cross-check. Agreement within MERGE_REL_TOLERANCE annotates the kept
        reading; a wider gap drops it to REVIEW_CONFIDENCE with a conflict note --
        the same pattern `merge_values` uses for chunk disagreement.
    """
    wholes = [v for v in values if not v.component_label]
    parts = [v for v in values if v.component_label]
    merged = merge_values(wholes)
    if not parts:
        return merged

    groups: dict = {}
    order: list = []
    for v in parts:
        k = _key(v)
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(v)

    by_key = {_key(v): i for i, v in enumerate(merged)}
    for k in order:
        summed = _component_sum(groups[k])
        idx = by_key.get(k)
        if idx is None:
            merged.append(summed)
            continue
        whole = merged[idx]
        if _within_merge_tolerance([whole.value, summed.value]):
            merged[idx] = replace(
                whole,
                note=_with_note(whole.note, f"✓ printed total agrees with its components ({summed.value})"),
            )
        else:
            merged[idx] = replace(
                whole,
                confidence=min(whole.confidence, REVIEW_CONFIDENCE),
                note=_with_note(
                    whole.note,
                    f"⚠ printed total {whole.value} disagrees with its components "
                    f"{summed.value} (reviewer confirm)",
                ),
            )
    return merged


# --- restated vs actual ------------------------------------------------------


def _basis_key(v):
    """`_key` without the basis: an actual and a restated reading of the same figure."""
    return (v.metric_code, v.period_kind, v.period_year, v.period_month, v.service_scope)


def prefer_restated(values: list) -> list:
    """Collapse an actual + restated pair for the SAME figure into one value.

    `MetricValueRecord` has no `basis` column, so an actual and a restated reading
    of one (metric, period, scope) would otherwise stage as two indistinguishable
    pending rows. A restatement is the publisher's own correction of that period,
    so the RESTATED reading is kept and the superseded actual is folded into its
    note. When the two disagree beyond the merge tolerance the kept value drops to
    REVIEW_CONFIDENCE so a human decides (same pattern as a chunk disagreement).
    """
    groups: dict = {}
    order: list = []
    for v in values:
        k = _basis_key(v)
        if k not in groups:
            groups[k] = []
            order.append(k)
        groups[k].append(v)

    out: list = []
    for k in order:
        vs = groups[k]
        restated = [v for v in vs if v.basis == "restated"]
        actuals = [v for v in vs if v.basis == "actual"]
        if not restated or not actuals:
            out.extend(vs)
            continue
        keep = max(restated, key=lambda v: v.confidence)
        dropped = max(actuals, key=lambda v: v.confidence)
        agrees = _within_merge_tolerance([keep.value, dropped.value])
        out.append(
            replace(
                keep,
                confidence=keep.confidence if agrees else min(keep.confidence, REVIEW_CONFIDENCE),
                note=_with_note(
                    keep.note,
                    f"restated figure kept; as-reported actual was {dropped.value}"
                    + ("" if agrees else " (reviewer confirm which applies)"),
                ),
            )
        )
        out.extend(v for v in vs if v is not keep and v is not dropped)
    return out


# --- one segment's Claude call ----------------------------------------------


def _segment_values(
    client, model: str, max_tokens: int, content: list, system: str, currency: str = "CAD",
    tool: Optional[dict] = None, allowed_codes: Optional[frozenset] = None,
) -> tuple[list, int, int]:
    """Run one segment's Claude call. Returns (values, input_tokens, off_statement).

    `tool` defaults to the full-canon EXTRACTION_TOOL; a specialist passes its
    statement-restricted schema. `allowed_codes` is the belt to that schema's
    braces: a row naming a code outside the specialist's statement is DROPPED
    (counted, never recorded) rather than trusted.
    """
    tool = tool or EXTRACTION_TOOL
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        tools=[tool],
        tool_choice={"type": "tool", "name": tool["name"]},
        messages=[{"role": "user", "content": content}],
    )
    rows = []
    for b in message.content:
        if getattr(b, "type", None) == "tool_use" and b.name == tool["name"]:
            rows = b.input.get("values", [])
    values = []
    off_statement = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        if allowed_codes is not None and r.get("metric_code") not in allowed_codes:
            off_statement += 1
            continue
        try:
            values.append(_row_to_value(r, currency))
        except (KeyError, ValueError, TypeError):
            continue
    usage = getattr(message, "usage", None)
    in_tok = 0
    if usage is not None:
        in_tok = (
            int(getattr(usage, "input_tokens", 0) or 0)
            + int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
            + int(getattr(usage, "cache_read_input_tokens", 0) or 0)
        )
    return values, in_tok, off_statement


class ChunkedHybridExtractor:
    """Default extractor: chunked markitdown text + batched scanned-page images.

    Builds one Claude segment per markdown chunk and per image batch, runs them in
    parallel, and merges the results. `_client` is injectable for the offline tests.
    """

    def __init__(
        self,
        api_key=None,
        *,
        model: str = DEFAULT_IMAGE_MODEL,
        text_model: Optional[str] = None,
        max_tokens: int = 8192,
        target_lines: int = DEFAULT_TARGET_LINES,
        include_image_pages: bool = True,
        image_text_threshold: int = IMAGE_TEXT_THRESHOLD,
        image_batch: int = DEFAULT_IMAGE_BATCH,
        image_overlap: int = DEFAULT_IMAGE_OVERLAP,
        max_workers: int = DEFAULT_MAX_WORKERS,
        _client=None,
    ) -> None:
        self._api_key = api_key
        self._model = model  # strong model for the scanned-image batches
        self._text_model = text_model or DEFAULT_TEXT_MODEL  # cheaper model for text chunks
        self._max_tokens = max_tokens
        self._target_lines = target_lines
        self._include_image_pages = include_image_pages
        self._image_text_threshold = image_text_threshold
        self._image_batch = image_batch
        self._image_overlap = image_overlap
        self._max_workers = max_workers
        self._client = _client
        # Enrich the system prompt with the metric-definition canon. The dictionary
        # is YAML-backed (a third-party dep); the offline/stdlib-only test env has no
        # PyYAML, so degrade gracefully to the base prompt there -- the canon only
        # matters on the real API path, where PyYAML is installed.
        #
        # Three prompt variants are built ONCE here and reused verbatim on every call
        # (generalist + one per financial statement), so each caches independently
        # under `cache_control` instead of thrashing a single moving prefix.
        self._statements: dict = {}         # statement code -> StatementSpec (router cues)
        self._statement_prompts: dict = {}  # statement code -> specialist system prompt
        self._statement_tools: dict = {}    # statement code -> code-restricted tool schema
        self._statement_codes: dict = {}    # statement code -> frozenset of its metric codes
        try:
            from ..dictionary import (  # lazy: needs PyYAML
                extraction_guidance,
                load_statements,
                metrics_for_statement,
            )

            self._system_prompt = (
                EXTRACTION_SYSTEM_PROMPT
                + "\n\nMetric definitions (the canon — map printed figures onto these, nothing else):\n"
                + extraction_guidance()
            )
            self._statements = load_statements()
            for code, spec in self._statements.items():
                # Derived metrics are computed downstream, never read off a page.
                codes = [c for c in metrics_for_statement(code) if c in _SOURCED]
                self._statement_prompts[code] = (
                    extraction_system_prompt(codes)  # its codes, not all 41
                    + "\n\n"
                    + statement_prompt_block(spec)
                    + f"\n\nMetric definitions for the {spec.display_name} (the ONLY codes "
                    "you may record — map printed figures onto these, nothing else):\n"
                    + extraction_guidance(statement=code)
                )
                self._statement_codes[code] = frozenset(codes)
                self._statement_tools[code] = extraction_tool(codes)
        except ImportError:
            # No dictionary available: no cues -> every chunk routes general, and the
            # extractor behaves exactly as it did before the split.
            self._system_prompt = EXTRACTION_SYSTEM_PROMPT

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        segments, image_pages, route_stats = self._segments(request)

        currency = agency_currency(request.agency_slug)
        client = self._ensure_client()
        results: list[Optional[tuple[list, int, int]]] = [None] * len(segments)
        errors: dict[str, str] = {}

        def run(idx):
            label, content, route, kind = segments[idx]
            seg_model = self._model if kind == "img" else self._text_model
            system, tool, allowed = self._prompt_for(route)
            try:
                return idx, _segment_values(
                    client, seg_model, self._max_tokens, content, system, currency,
                    tool=tool, allowed_codes=allowed,
                ), None
            except Exception as exc:  # one segment failing must not sink the run
                return idx, ([], 0, 0), f"{type(exc).__name__}: {exc}"

        if segments:
            with ThreadPoolExecutor(max_workers=min(self._max_workers, len(segments))) as pool:
                for idx, payload, err in pool.map(run, range(len(segments))):
                    results[idx] = payload
                    if err:
                        errors[segments[idx][0]] = err

        all_values: list = []
        total_in = 0
        off_statement = 0  # specialist rows naming another statement's code (dropped)
        tokens_by_model: dict[str, int] = {}  # split text vs image tokens for an honest cost
        segments_raw: list[dict] = []
        for idx, r in enumerate(results):
            label, _, route, kind = segments[idx]
            seg_model = self._model if kind == "img" else self._text_model
            if r is None:
                segments_raw.append({
                    "label": label, "route": route, "values": [], "input_tokens": 0,
                    "error": errors.get(label),
                })
                continue
            vals, in_tok, off = r
            all_values.extend(vals)
            total_in += in_tok
            off_statement += off
            tokens_by_model[seg_model] = tokens_by_model.get(seg_model, 0) + in_tok
            segments_raw.append({
                "label": label,
                "route": route,
                "values": [value_to_dict(v) for v in vals],
                "input_tokens": in_tok,
                "error": errors.get(label),
            })

        # Drop sub-floor noise BEFORE merging so garbage can't poison a good reading into
        # a false conflict (exactly CONFIDENCE_FLOOR survives, keeping 1.4's mismatch-caps visible).
        kept = [v for v in all_values if v.confidence >= CONFIDENCE_FLOOR]
        dropped_below_floor = len(all_values) - len(kept)

        # Component readings are summed deterministically (never by the model) and
        # cross-checked against any printed total; whole readings merge as before.
        merged = aggregate_components(kept)
        component_sums = sum(1 for v in merged if v.note and COMPONENT_SUM_MARKER in v.note)

        # An actual + a restated reading of the same figure collapse to one row
        # (the staged record has no basis column to tell them apart).
        before_basis_dedup = len(merged)
        merged = prefer_restated(merged)
        restated_collapsed = before_basis_dedup - len(merged)

        # Drop out-of-scope figures the metric set does not want at agency level (step 2.3):
        # single-mode/whole-city scopes and budget/forecast bases. 'restated' is an actual, kept.
        dropped_scope = sum(1 for v in merged if v.service_scope in DROPPED_SCOPES)
        dropped_basis = sum(
            1 for v in merged if v.service_scope not in DROPPED_SCOPES and v.basis in DROPPED_BASES
        )
        merged = [
            v for v in merged
            if v.service_scope not in DROPPED_SCOPES and v.basis not in DROPPED_BASES
        ]

        md_chunks = route_stats["md_chunks"]
        img_batches = sum(1 for s in segments if s[3] == "img")
        est_cost = sum(
            tok * _INPUT_USD_PER_MTOK.get(m, 5.0) / 1_000_000
            for m, tok in tokens_by_model.items()
        )
        return ExtractionResult(
            values=merged,
            diagnostics={
                "extractor": "chunked_hybrid",
                "model": self._model,             # image/strong model
                "text_model": self._text_model,   # text/cheap model
                "md_chunks": md_chunks,
                "image_batches": img_batches,
                "segments": len(segments),
                "image_pages": sorted(set(image_pages)),
                # Deterministic statement routing (image batches count as general).
                "routed_income": route_stats["routed_income"],
                "routed_balance": route_stats["routed_balance"],
                "routed_both": route_stats["routed_both"],
                "routed_general": route_stats["routed_general"],
                "dropped_off_statement": off_statement,
                "values_raw": len(all_values),
                "dropped_below_floor": dropped_below_floor,
                "dropped_scope": dropped_scope,
                "dropped_basis": dropped_basis,
                "component_sums": component_sums,
                "restated_collapsed": restated_collapsed,
                "values_merged": len(merged),
                "input_tokens": total_in,
                "input_tokens_by_model": tokens_by_model,
                "est_cost_usd": est_cost,
                "errors": errors,
                "segments_raw": segments_raw,
            },
        )

    def _segments(self, request: ExtractionRequest) -> tuple[list, list[int], int]:
        """Build (label, content_blocks, route, kind) for every chunk and image batch.

        A text chunk whose text (plus its context header) names one financial
        statement becomes that statement's specialist segment; a chunk naming BOTH
        becomes two segments, one per specialist, whose readings meet again in the
        normal merge. Everything else stays a full-canon generalist segment, and an
        image batch -- no text to route on -- always does.

        Also returns the markdown chunk count (a 'both' chunk is two segments but
        still one chunk).
        """
        agency_intro = self._agency_intro(request)
        segments: list[tuple[str, list, str, str]] = []
        image_pages: list[int] = []
        route_counts: dict[str, int] = {}

        if request.pdf_bytes is not None:
            md = _to_markdown(request.pdf_bytes)
        else:
            md = "\n\n".join(text for _, text in (request.pages or []))

        chunks = chunk_markdown_with_context(md, target_lines=self._target_lines)
        for n, (chunk, context) in enumerate(chunks):
            intro = f"{agency_intro}\n\nReport text, section {n + 1} of {len(chunks)} -- extract every metric you can read here:"
            if context:
                intro += f"\n\n{context}"  # carries a lost units header / section title (never inside the chunk)
            # Route on the context header TOO: the statement's title is often in the
            # heading the chunker carried forward, not in the chunk's own lines.
            route = route_chunk(f"{context}\n{chunk}", self._statements)
            route_counts[route] = route_counts.get(route, 0) + 1
            routes = list(self._statements) if route == ROUTE_BOTH else [route]
            for r in routes:
                label = f"md{n}" if r == ROUTE_GENERAL else f"md{n}:{r}"
                segments.append((
                    label,
                    [
                        {"type": "text", "text": intro},
                        {"type": "text", "text": chunk},
                    ],
                    r,
                    "md",
                ))

        if request.pdf_bytes is not None and self._include_image_pages:
            for b64, pages in _image_page_batches(
                request.pdf_bytes, self._image_text_threshold,
                batch=self._image_batch, overlap=self._image_overlap,
            ):
                image_pages.extend(pages)
                # No text to match cues against -> the generalist reads the scan.
                route_counts[ROUTE_GENERAL] = route_counts.get(ROUTE_GENERAL, 0) + 1
                segments.append((
                    f"img{_page_label(pages)}",
                    [
                        {"type": "text", "text": f"{agency_intro}\n\nScanned report pages {_page_label(pages)} (no text layer) -- read the figures visually and extract every metric:"},
                        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
                    ],
                    ROUTE_GENERAL,
                    "img",
                ))

        return segments, image_pages, {
            "md_chunks": len(chunks),
            "routed_income": route_counts.get("income_statement", 0),
            "routed_balance": route_counts.get("balance_sheet", 0),
            "routed_both": route_counts.get(ROUTE_BOTH, 0),
            "routed_general": route_counts.get(ROUTE_GENERAL, 0),
        }

    def _prompt_for(self, route: str) -> tuple[str, dict, Optional[frozenset]]:
        """(system prompt, tool schema, allowed codes) for a segment's route.

        A statement route gets its specialist prompt and the tool whose metric_code
        enum holds only that statement's codes; anything else gets today's
        full-canon generalist prompt and the unrestricted tool.
        """
        if route in self._statement_prompts:
            return (
                self._statement_prompts[route],
                self._statement_tools[route],
                self._statement_codes[route],
            )
        return self._system_prompt, EXTRACTION_TOOL, None

    def _agency_intro(self, request: ExtractionRequest) -> str:
        """`Agency: {slug}` plus the catalog row's document context (step 2.5b).

        Each line is appended only when its source field is present; a request built
        the old way (all three fields None) yields just the bare agency line.
        """
        lines = [f"Agency: {request.agency_slug}"]
        if request.doc_type is not None and request.doc_year is not None and request.author_label is not None:
            published_by = (
                "the transit agency itself."
                if request.author_label == "T"
                else "the CITY government (consolidated city-wide financial statements)."
            )
            lines.append(f"Document: {request.doc_type} for {request.doc_year}, published by {published_by}")
        if request.author_label == "C":
            lines.append(
                "*** CITY-PUBLISHED DOCUMENT — THE SINGLE BIGGEST SOURCE OF WRONG VALUES ***\n"
                "This report belongs to the MUNICIPALITY, not to the transit agency. Its "
                "consolidated financial statements (Statement of Financial Position, "
                "Statement of Operations, Consolidated Statement of Cash Flows, and every "
                "schedule/note that rolls up the whole corporation) cover police, fire, "
                "roads, parks, utilities and transit TOGETHER. Those figures are NOT the "
                "transit agency's and must NEVER be recorded as the agency's numbers.\n"
                "RULE: every consolidated/city-wide financial figure is "
                "service_scope='city_wide' (which is dropped). A figure may use a transit "
                "scope ('total'/'conventional'/'specialized'/'system_wide') ONLY when it "
                "comes from a schedule, segment note, or table that names the transit "
                "service specifically (e.g. 'Segment Disclosure — Transit', 'Schedule of "
                "Transit Operations', a Transit line inside a departmental schedule) — and "
                "then set `table_reference` to that schedule/note.\n"
                "If the statements contain no transit segment breakout, emit NO financial "
                "figures at all for this agency and say so in `note`. A city's total "
                "assets, total liabilities, accumulated surplus, long-term debt, tangible "
                "capital assets, total revenue or total expenses are city_wide by default: "
                "when in doubt, city_wide."
            )
        if request.doc_type in {"budget", "business_plan", "service_plan"} and request.doc_year is not None:
            lines.append(
                f"This is a plan/budget document: figures for {request.doc_year} and later "
                "are basis='budget' or 'forecast' unless explicitly reported as actual "
                "results; prior-year actuals are basis='actual'."
            )
        return "\n".join(lines)

    def _ensure_client(self):
        if self._client is None:
            import anthropic  # lazy: real path only

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client
