"""Path (b): PDF -> clean markdown via DocStrange -> metrics via Claude's text path.

The default extractor sends Claude a *picture* of each page. This sends Claude
DocStrange's markdown instead -- clean tables and OCR'd text rather than rendered
pixels -- to test whether a better representation reads the numbers better. It is
a drop-in `Extractor`, so it runs through the same `pdf-smoke` / `run_pdf` seam
for an apples-to-apples comparison against the vision path. The Claude step reuses
the pipeline's existing text client (`AnthropicLLMClient` + `EXTRACTION_SYSTEM_PROMPT`
+ the `record_metrics` tool), so only the document representation changes.

Cloud mode (default) is a single multipart POST to DocStrange's hosted endpoint
over httpx -- no `docstrange` package, so it works even where the numpy-pinned
package won't install. It needs a free Nanonets api key (DOCSTRANGE_API_KEY);
anonymous calls 401. The reports are public government documents, so cloud upload
is fine. mode='cpu'/'gpu' runs the local package instead (downloads a ~7B model).
`docstrange`, `anthropic`, and `httpx` are imported lazily, so this module imports
with none installed; `_pdf_to_markdown` is a module-level seam the offline tests
monkeypatch.

Caveats by design (it's an experiment, not the production default):
- No verify second pass -- a single extraction read, like the legacy text path.
- Markdown flattens page boundaries, so page_number is approximate.
- The whole document's markdown is sent in one call (text is cheap); add the
  prefilter only if a report is large enough to matter.
"""

from __future__ import annotations

from .extractor import ExtractionRequest, ExtractionResult
from .llm import EXTRACTION_SYSTEM_PROMPT

# Input $/MTok by model -- a display aid for the cost comparison only, NOT billing
# (the text path's client doesn't surface token usage, so cost is estimated from
# markdown length + a fixed prompt/framing overhead). Matches the published rates.
_INPUT_USD_PER_MTOK = {
    "claude-fable-5": 10.0,
    "claude-opus-4-8": 5.0,
    "claude-opus-4-7": 5.0,
    "claude-opus-4-6": 5.0,
    "claude-sonnet-4-6": 3.0,
    "claude-haiku-4-5": 1.0,
}
# Rough token overhead of the system prompt + per-call framing, added to the
# markdown's estimated tokens so the cost estimate isn't wildly low on tiny docs.
_PROMPT_OVERHEAD_TOKENS = 1200


def _result_markdown(result) -> str:
    """Pull markdown off a DocStrange result, tolerant of minor API drift."""
    fn = getattr(result, "extract_markdown", None)
    if callable(fn):
        return fn()
    md = getattr(result, "markdown", None)
    if isinstance(md, str):
        return md
    to_md = getattr(result, "to_markdown", None)
    if callable(to_md):
        return to_md()
    raise AttributeError(
        "DocStrange result exposes no markdown accessor "
        "(tried extract_markdown(), .markdown, to_markdown())"
    )


# DocStrange's hosted endpoint. Cloud mode is a single multipart POST, so it
# needs no `docstrange` package (just httpx) -- which is the only path that works
# on a Python the numpy-pinned package can't install into.
_CLOUD_URL = "https://extraction-api.nanonets.com/extract"


def _pdf_to_markdown(pdf_bytes: bytes, *, mode: str, api_key) -> str:
    """Convert PDF bytes to markdown with DocStrange (module seam; lazy imports).

    mode='cloud' (default) POSTs to the hosted endpoint over httpx -- no package
    needed. mode='cpu'/'gpu' runs the local `docstrange` package (downloads a 7B
    model). The cloud endpoint requires an api_key (a free Nanonets key); anonymous
    calls return 401.
    """
    if mode in ("cpu", "gpu"):
        return _local_markdown(pdf_bytes, mode)
    return _cloud_markdown(pdf_bytes, api_key)


def _cloud_markdown(pdf_bytes: bytes, api_key) -> str:
    import httpx  # lazy: cloud path only (already a pipeline dep)

    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    resp = httpx.post(
        _CLOUD_URL,
        files={"file": ("document.pdf", pdf_bytes, "application/pdf")},
        data={"output_type": "markdown"},
        headers=headers,
        timeout=300,
    )
    if resp.status_code == 401:
        raise RuntimeError(
            "DocStrange cloud needs an API key. Set DOCSTRANGE_API_KEY (free key at "
            "https://app.nanonets.com/#/keys), or use --docstrange-mode cpu to run locally."
        )
    resp.raise_for_status()
    content = resp.json().get("content")
    if not isinstance(content, str):
        raise RuntimeError(
            f"DocStrange cloud returned no markdown 'content' (keys: {list(resp.json())[:8]})"
        )
    return content


def _local_markdown(pdf_bytes: bytes, mode: str) -> str:
    import os
    import tempfile

    from docstrange import DocumentExtractor  # lazy: local package path only

    extractor = DocumentExtractor(cpu=True) if mode == "cpu" else DocumentExtractor(gpu=True)
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        tmp.write(pdf_bytes)
        tmp.close()
        return _result_markdown(extractor.extract(tmp.name))
    finally:
        os.unlink(tmp.name)


def _estimate_cost(markdown: str, model: str) -> float:
    """Rough input cost from markdown length -- display aid only, not billing."""
    approx_tokens = len(markdown) / 4 + _PROMPT_OVERHEAD_TOKENS
    rate = _INPUT_USD_PER_MTOK.get(model, 5.0) / 1_000_000
    return approx_tokens * rate


class DocStrangeExtractor:
    """Extractor that reads metrics off DocStrange markdown instead of the image.

    Converts the PDF to markdown (DocStrange), then hands that text to Claude via
    the pipeline's text client. `llm_client` is injectable for the offline tests;
    in production it builds an `AnthropicLLMClient` on the given Anthropic key.
    """

    def __init__(
        self,
        api_key=None,
        *,
        model: str = "claude-opus-4-8",
        max_tokens: int = 4096,
        mode: str = "cloud",
        docstrange_api_key=None,
        llm_client=None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._mode = mode
        self._docstrange_api_key = docstrange_api_key
        self._llm_client = llm_client

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        if request.pdf_bytes is not None:
            markdown = _pdf_to_markdown(
                request.pdf_bytes, mode=self._mode, api_key=self._docstrange_api_key
            )
            source = f"docstrange_{self._mode}"
        else:
            # No PDF to convert: fall back to the pre-extracted page text.
            markdown = "\n\n".join(text for _, text in (request.pages or []))
            source = "pages_text"

        client = self._llm_client or self._build_client()
        values = client.extract(EXTRACTION_SYSTEM_PROMPT, markdown, request.agency_slug)

        return ExtractionResult(
            values=values,
            diagnostics={
                "extractor": "docstrange_markdown",
                "model": self._model,
                "source": source,
                "markdown_chars": len(markdown),
                "est_cost_usd": _estimate_cost(markdown, self._model),
            },
        )

    def _build_client(self):
        from .llm import AnthropicLLMClient  # lazy: pulls anthropic

        return AnthropicLLMClient(self._api_key, model=self._model, max_tokens=self._max_tokens)
