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

It implements the `Extractor` seam (drop-in for run_pdf / scan / pdf-smoke).
`markitdown`, `anthropic`, and `pypdf` import lazily; `_to_markdown` /
`_image_page_batches` are module seams the offline tests monkeypatch, and `_client`
is injectable. No verify pass (cross-chunk merge + the pending-review queue cover it).
"""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from typing import Optional

from .ensemble import _key, _with_note
from .extractor import ExtractionRequest, ExtractionResult
from .llm import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_TOOL, _row_to_value
from .markitdown_path import IMAGE_TEXT_THRESHOLD, _INPUT_USD_PER_MTOK, _to_markdown

DEFAULT_TARGET_LINES = 350   # soft target lines per chunk; a single paragraph/table bigger than this is kept whole
DEFAULT_IMAGE_BATCH = 5      # scanned pages per image call -- not the whole 30-page scan at once
DEFAULT_IMAGE_OVERLAP = 0    # no overlap: each scanned page is sent in exactly one batch (no duplicate send)
DEFAULT_MAX_WORKERS = 4      # parallel segment calls (SDK retries 429s)
REVIEW_CONFIDENCE = Decimal("0.5")  # stamped on a cross-chunk disagreement so it surfaces for review


# --- markdown chunking (paragraph boundaries only) --------------------------


def _is_blank(line: str) -> bool:
    return not line.strip()


def chunk_markdown(md: str, *, target_lines: int = DEFAULT_TARGET_LINES) -> list[str]:
    """Split markdown into chunks, cutting ONLY at paragraph boundaries (blank lines).

    A run of consecutive non-blank lines -- a paragraph, or a whole table (which has
    no blank line inside it, so its header stays with its rows) -- is the atomic unit.
    Blocks are packed up to ~target_lines and never split, so every chunk boundary
    falls at the end of a paragraph and NO content is duplicated between chunks. A
    single block larger than target_lines is kept whole as its own chunk rather than
    cut mid-paragraph.
    """
    blocks: list[list[str]] = []
    cur: list[str] = []
    for ln in md.splitlines():
        if _is_blank(ln):
            if cur:
                blocks.append(cur)
                cur = []
        else:
            cur.append(ln)
    if cur:
        blocks.append(cur)

    chunks: list[list[str]] = []
    cur = []
    for blk in blocks:
        if cur and len(cur) + len(blk) > target_lines:
            chunks.append(cur)
            cur = []
        if cur:
            cur.append("")  # preserve the paragraph break between packed blocks
        cur.extend(blk)
    if cur:
        chunks.append(cur)

    return [t for t in ("\n".join(c).strip() for c in chunks) if t]


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


def merge_values(values: list) -> list:
    """De-dupe values across chunks on (metric, period).

    One reading -> kept. Several agreeing -> the highest-confidence one. Several that
    DISAGREE on the value -> highest-confidence one, dropped to REVIEW_CONFIDENCE with
    every candidate in the note (a chunk boundary or OCR slip surfaces for a human).
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
        if len({v.value for v in vs}) == 1:
            out.append(best)
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


def _segment_values(client, model: str, max_tokens: int, content: list) -> tuple[list, int]:
    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": EXTRACTION_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
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
        model: str = "claude-opus-4-8",
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
        self._model = model
        self._max_tokens = max_tokens
        self._target_lines = target_lines
        self._include_image_pages = include_image_pages
        self._image_text_threshold = image_text_threshold
        self._image_batch = image_batch
        self._image_overlap = image_overlap
        self._max_workers = max_workers
        self._client = _client

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        segments, image_pages = self._segments(request)

        client = self._ensure_client()
        results: list[Optional[tuple[list, int]]] = [None] * len(segments)
        errors: dict[str, str] = {}

        def run(idx):
            _, content = segments[idx]
            try:
                return idx, _segment_values(client, self._model, self._max_tokens, content), None
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
        for r in results:
            if r is None:
                continue
            vals, in_tok = r
            all_values.extend(vals)
            total_in += in_tok

        merged = merge_values(all_values)
        md_chunks = sum(1 for label, _ in segments if label.startswith("md"))
        img_batches = sum(1 for label, _ in segments if label.startswith("img"))
        return ExtractionResult(
            values=merged,
            diagnostics={
                "extractor": "chunked_hybrid",
                "model": self._model,
                "md_chunks": md_chunks,
                "image_batches": img_batches,
                "segments": len(segments),
                "image_pages": sorted(set(image_pages)),
                "values_raw": len(all_values),
                "values_merged": len(merged),
                "input_tokens": total_in,
                "est_cost_usd": total_in * _INPUT_USD_PER_MTOK.get(self._model, 5.0) / 1_000_000,
                "errors": errors,
            },
        )

    def _segments(self, request: ExtractionRequest) -> tuple[list, list[int]]:
        """Build (label, content_blocks) for every markdown chunk and image batch."""
        agency = request.agency_slug
        segments: list[tuple[str, list]] = []
        image_pages: list[int] = []

        if request.pdf_bytes is not None:
            md = _to_markdown(request.pdf_bytes)
        else:
            md = "\n\n".join(text for _, text in (request.pages or []))

        chunks = chunk_markdown(md, target_lines=self._target_lines)
        for n, chunk in enumerate(chunks):
            segments.append((
                f"md{n}",
                [
                    {"type": "text", "text": f"Agency: {agency}\n\nReport text, section {n + 1} of {len(chunks)} -- extract every metric you can read here:"},
                    {"type": "text", "text": chunk, "cache_control": {"type": "ephemeral"}},
                ],
            ))

        if request.pdf_bytes is not None and self._include_image_pages:
            for b64, pages in _image_page_batches(
                request.pdf_bytes, self._image_text_threshold,
                batch=self._image_batch, overlap=self._image_overlap,
            ):
                image_pages.extend(pages)
                segments.append((
                    f"img{pages[0]}-{pages[-1]}",
                    [
                        {"type": "text", "text": f"Agency: {agency}\n\nScanned report pages {pages[0]}–{pages[-1]} (no text layer) -- read the figures visually and extract every metric:"},
                        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}, "cache_control": {"type": "ephemeral"}},
                    ],
                ))

        return segments, image_pages

    def _ensure_client(self):
        if self._client is None:
            import anthropic  # lazy: real path only

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client
