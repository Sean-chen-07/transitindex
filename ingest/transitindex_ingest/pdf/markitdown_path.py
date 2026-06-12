"""Path (b), markitdown: PDF text -> markdown + scanned pages as images -> Claude.

Microsoft's `markitdown` converts a PDF's *text layer* to markdown (via pdfminer) --
it does NOT OCR, so a page with no text layer (a scan or a figure) comes back empty.
This extractor handles that gap: it sends Claude the markdown for everything that is
machine-readable AND attaches the pages markitdown couldn't read (detected by an
almost-empty text layer) as a `document` block in the SAME call, so Claude reads
those visually. Markdown for the text, vision for the scans, one request.

Why markdown helps at all: on a clean digital report the model reads numbers off a
real markdown table (with column/year headers intact) at higher confidence than off
a rendered image, and text tokens are cheaper than image tokens.

It implements the `Extractor` seam (drop-in for pdf-smoke / run_pdf). `markitdown`,
`anthropic`, and `pypdf` import lazily, so this module imports with none installed;
`_to_markdown` / `_image_pages_pdf` are module-level seams the offline tests
monkeypatch, and `_client` is injectable.

max_tokens defaults to 8192 on purpose: a multi-year stats table is 30-40 tool rows
and 4096 truncates the tool-call JSON to nothing (stop_reason 'max_tokens').
Single pass (no verify) and whole-document markdown (no prefilter) -- an experiment,
not the production default.
"""

from __future__ import annotations

import base64
from typing import Optional

from .extractor import ExtractionRequest, ExtractionResult
from .llm import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_TOOL, _row_to_value

# A page whose stripped text layer is shorter than this is treated as a scan/
# figure and sent to Claude as an image instead of trusting markitdown's (empty)
# markdown for it. Matches the router's threshold.
IMAGE_TEXT_THRESHOLD = 120

# Input $/MTok by model -- display aid for the cost line, computed from the call's
# real reported input tokens (not billing).
_INPUT_USD_PER_MTOK = {
    "claude-fable-5": 10.0,
    "claude-opus-4-8": 5.0,
    "claude-opus-4-7": 5.0,
    "claude-opus-4-6": 5.0,
    "claude-sonnet-4-6": 3.0,
    "claude-haiku-4-5": 1.0,
}


def _to_markdown(pdf_bytes: bytes) -> str:
    """PDF text layer -> markdown via markitdown (lazy import; module seam)."""
    import os
    import tempfile

    from markitdown import MarkItDown

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(pdf_bytes)
        tmp.close()
        return MarkItDown().convert(tmp.name).text_content
    finally:
        os.unlink(tmp.name)


def _image_pages_pdf(pdf_bytes: bytes, threshold: int) -> tuple[Optional[str], list[int]]:
    """Return (base64 sub-PDF of the no-text-layer pages, their 1-based numbers).

    These are the pages markitdown can't read; bundling just them into a small PDF
    lets Claude read them visually without re-sending the whole document. Returns
    (None, []) when every page has a usable text layer.
    """
    from io import BytesIO

    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(BytesIO(pdf_bytes))
    low = [
        i for i, p in enumerate(reader.pages)
        if len((p.extract_text() or "").strip()) < threshold
    ]
    if not low:
        return None, []
    writer = PdfWriter()
    for i in low:
        writer.add_page(reader.pages[i])
    buf = BytesIO()
    writer.write(buf)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8"), [i + 1 for i in low]


def _framing(agency_slug: str, has_images: bool) -> str:
    base = (
        f"Agency: {agency_slug}\n\n"
        "The markdown below is the report's machine-readable text."
    )
    if has_images:
        base += (
            " The attached PDF holds the pages whose text could not be extracted "
            "(scans or figures) -- read those visually."
        )
    return base


def _rows(message) -> list:
    for block in message.content:
        if getattr(block, "type", None) == "tool_use" and block.name == EXTRACTION_TOOL["name"]:
            return block.input.get("values", [])
    return []


def _input_tokens(message) -> int:
    usage = getattr(message, "usage", None)
    if usage is None:
        return 0
    return (
        int(getattr(usage, "input_tokens", 0) or 0)
        + int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
        + int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    )


class MarkitdownExtractor:
    """Read metrics off markitdown markdown, with scanned pages attached as images.

    `_client` is injectable for the offline tests (a scripted fake exposing
    messages.create); in production it builds an `anthropic.Anthropic` on the key.
    """

    def __init__(
        self,
        api_key=None,
        *,
        model: str = "claude-opus-4-8",
        max_tokens: int = 8192,
        include_image_pages: bool = True,
        image_text_threshold: int = IMAGE_TEXT_THRESHOLD,
        _client=None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._include_image_pages = include_image_pages
        self._image_text_threshold = image_text_threshold
        self._client = _client

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        image_b64: Optional[str] = None
        image_pages: list[int] = []
        if request.pdf_bytes is not None:
            markdown = _to_markdown(request.pdf_bytes)
            if self._include_image_pages:
                image_b64, image_pages = _image_pages_pdf(
                    request.pdf_bytes, self._image_text_threshold
                )
        else:
            markdown = "\n\n".join(text for _, text in (request.pages or []))

        content = [
            {"type": "text", "text": _framing(request.agency_slug, bool(image_b64))},
            {"type": "text", "text": markdown, "cache_control": {"type": "ephemeral"}},
        ]
        if image_b64:
            content.append(
                {
                    "type": "document",
                    "source": {"type": "base64", "media_type": "application/pdf", "data": image_b64},
                    "cache_control": {"type": "ephemeral"},
                }
            )

        message = self._ensure_client().messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            system=[
                {"type": "text", "text": EXTRACTION_SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": EXTRACTION_TOOL["name"]},
            messages=[{"role": "user", "content": content}],
        )

        values = []
        for r in _rows(message):
            if not isinstance(r, dict):
                continue
            try:
                values.append(_row_to_value(r))
            except (KeyError, ValueError, TypeError):
                continue

        in_tok = _input_tokens(message)
        return ExtractionResult(
            values=values,
            diagnostics={
                "extractor": "markitdown_hybrid",
                "model": self._model,
                "markdown_chars": len(markdown),
                "image_pages": image_pages,
                "image_page_count": len(image_pages),
                "input_tokens": in_tok,
                "est_cost_usd": in_tok * _INPUT_USD_PER_MTOK.get(self._model, 5.0) / 1_000_000,
                "stop_reason": getattr(message, "stop_reason", None),
            },
        )

    def _ensure_client(self):
        if self._client is None:
            import anthropic  # lazy: real path only

            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client
