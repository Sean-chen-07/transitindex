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

Each segment is its own Claude call (same EXTRACTION_SYSTEM_PROMPT + record_metrics
tool); results are merged and de-duped on (metric, period): agreeing chunks collapse
to the highest-confidence reading, conflicting chunks are flagged for review. The
system prompt is identical across calls, so prompt caching keeps the per-call
overhead cheap.

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

from .ensemble import _key, _with_note
from .extractor import ExtractionRequest, ExtractionResult
from .llm import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_TOOL, _row_to_value, value_to_dict
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


# --- one segment's Claude call ----------------------------------------------


def _segment_values(client, model: str, max_tokens: int, content: list, system: str) -> tuple[list, int]:
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        tools=[EXTRACTION_TOOL],
        tool_choice={"type": "tool", "name": EXTRACTION_TOOL["name"]},
        messages=[{"role": "user", "content": content}],
    )
    rows = []
    for b in message.content:
        if getattr(b, "type", None) == "tool_use" and b.name == EXTRACTION_TOOL["name"]:
            rows = b.input.get("values", [])
    values = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        try:
            values.append(_row_to_value(r))
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
    return values, in_tok


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
        from ..dictionary import extraction_guidance  # lazy: keeps module import third-party-free

        self._system_prompt = (
            EXTRACTION_SYSTEM_PROMPT
            + "\n\nMetric definitions (the canon — map printed figures onto these, nothing else):\n"
            + extraction_guidance()
        )

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        segments, image_pages = self._segments(request)

        client = self._ensure_client()
        results: list[Optional[tuple[list, int]]] = [None] * len(segments)
        errors: dict[str, str] = {}

        def run(idx):
            label, content = segments[idx]
            seg_model = self._model if label.startswith("img") else self._text_model
            try:
                return idx, _segment_values(client, seg_model, self._max_tokens, content, self._system_prompt), None
            except Exception as exc:  # one segment failing must not sink the run
                return idx, ([], 0), f"{type(exc).__name__}: {exc}"

        if segments:
            with ThreadPoolExecutor(max_workers=min(self._max_workers, len(segments))) as pool:
                for idx, payload, err in pool.map(run, range(len(segments))):
                    results[idx] = payload
                    if err:
                        errors[segments[idx][0]] = err

        all_values: list = []
        total_in = 0
        tokens_by_model: dict[str, int] = {}  # split text vs image tokens for an honest cost
        segments_raw: list[dict] = []
        for idx, r in enumerate(results):
            label = segments[idx][0]
            seg_model = self._model if label.startswith("img") else self._text_model
            if r is None:
                segments_raw.append({"label": label, "values": [], "input_tokens": 0, "error": errors.get(label)})
                continue
            vals, in_tok = r
            all_values.extend(vals)
            total_in += in_tok
            tokens_by_model[seg_model] = tokens_by_model.get(seg_model, 0) + in_tok
            segments_raw.append({
                "label": label,
                "values": [value_to_dict(v) for v in vals],
                "input_tokens": in_tok,
                "error": errors.get(label),
            })

        # Drop sub-floor noise BEFORE merging so garbage can't poison a good reading into
        # a false conflict (exactly CONFIDENCE_FLOOR survives, keeping 1.4's mismatch-caps visible).
        kept = [v for v in all_values if v.confidence >= CONFIDENCE_FLOOR]
        dropped_below_floor = len(all_values) - len(kept)

        merged = merge_values(kept)

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

        md_chunks = sum(1 for label, _ in segments if label.startswith("md"))
        img_batches = sum(1 for label, _ in segments if label.startswith("img"))
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
                "values_raw": len(all_values),
                "dropped_below_floor": dropped_below_floor,
                "dropped_scope": dropped_scope,
                "dropped_basis": dropped_basis,
                "values_merged": len(merged),
                "input_tokens": total_in,
                "input_tokens_by_model": tokens_by_model,
                "est_cost_usd": est_cost,
                "errors": errors,
                "segments_raw": segments_raw,
            },
        )

    def _segments(self, request: ExtractionRequest) -> tuple[list, list[int]]:
        """Build (label, content_blocks) for every markdown chunk and image batch."""
        agency_intro = self._agency_intro(request)
        segments: list[tuple[str, list]] = []
        image_pages: list[int] = []

        if request.pdf_bytes is not None:
            md = _to_markdown(request.pdf_bytes)
        else:
            md = "\n\n".join(text for _, text in (request.pages or []))

        chunks = chunk_markdown_with_context(md, target_lines=self._target_lines)
        for n, (chunk, context) in enumerate(chunks):
            intro = f"{agency_intro}\n\nReport text, section {n + 1} of {len(chunks)} -- extract every metric you can read here:"
            if context:
                intro += f"\n\n{context}"  # carries a lost units header / section title (never inside the chunk)
            segments.append((
                f"md{n}",
                [
                    {"type": "text", "text": intro},
                    {"type": "text", "text": chunk},
                ],
            ))

        if request.pdf_bytes is not None and self._include_image_pages:
            for b64, pages in _image_page_batches(
                request.pdf_bytes, self._image_text_threshold,
                batch=self._image_batch, overlap=self._image_overlap,
            ):
                image_pages.extend(pages)
                segments.append((
                    f"img{_page_label(pages)}",
                    [
                        {"type": "text", "text": f"{agency_intro}\n\nScanned report pages {_page_label(pages)} (no text layer) -- read the figures visually and extract every metric:"},
                        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
                    ],
                ))

        return segments, image_pages

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
                "City-published document: balance-sheet and financial figures that cover "
                "the WHOLE CITY are service_scope='city_wide' — only figures explicitly "
                "broken out for the transit service/segment may use other scopes. If the "
                "statements have no transit segment breakout, emit NO city-wide financials."
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
