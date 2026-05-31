"""The stable extraction seam: document -> extracted values.

`Extractor` is the one interface the pipeline depends on for "turn a document
into ExtractedValues". `ClaudePdfExtractor` (pdf/claude_pdf.py) is the default
real implementation; `LegacyTextExtractor` wraps the old text-only LLMClient so
the existing llm_client= call path keeps working unchanged. `FakeExtractor` is
the deterministic test double. A future, better extractor drops in by
implementing this Protocol -- pipeline.py and cli.py need zero changes.

Pure stdlib: no anthropic, no pypdf imports here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from .extract import Page
from .llm import ExtractedValue, LLMClient


@dataclass(frozen=True)
class ExtractionRequest:
    """One document handed to an Extractor.

    Real path: pdf_bytes is the whole PDF (Claude reads it natively as a
    base64 document block). Offline/text fallback: pages carries pre-extracted
    [(page_number, text), ...] so the legacy text path and the offline tests
    work with no PDF bytes. media_type is the document MIME type Claude expects.
    Exactly one of pdf_bytes / pages is the primary input for a given extractor.
    """

    agency_slug: str
    pdf_bytes: Optional[bytes] = None
    pages: Optional[list[Page]] = None
    media_type: str = "application/pdf"


@dataclass(frozen=True)
class ExtractionResult:
    """What an Extractor returns: the values plus run diagnostics.

    diagnostics is a free-form dict for observability only (the pipeline does
    not branch on it). Conventional keys: model, page_count, input_tokens,
    est_cost_usd, chunks, verify_dropped.
    """

    values: list[ExtractedValue]
    diagnostics: dict = field(default_factory=dict)


@runtime_checkable
class Extractor(Protocol):
    """Turn one document into extracted metric values. Stable seam."""

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        ...


class LegacyTextExtractor:
    """Adapt an old text-only LLMClient to the Extractor seam.

    Joins request.pages into one text blob and calls the wrapped client's
    text-only extract(). This is how the existing `llm_client=` call path (and
    the ~106 offline tests that pass FakeLLMClient) keep working with the new
    seam underneath -- their behavior is identical to before.
    """

    def __init__(self, llm_client: LLMClient, system_prompt: str) -> None:
        self._client = llm_client
        self._system_prompt = system_prompt

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        pages = request.pages or []
        document_text = "\n\n".join(text for _, text in pages)
        values = self._client.extract(
            self._system_prompt, document_text, request.agency_slug
        )
        return ExtractionResult(values=values, diagnostics={"extractor": "legacy_text"})


class FakeExtractor:
    """Deterministic Extractor that returns a caller-supplied canned list.

    The test/eval double for the seam: feed it the ExtractedValues an extractor
    "would" return so the pipeline can be driven with no API and no PDF bytes.
    """

    def __init__(
        self, values: list[ExtractedValue], diagnostics: Optional[dict] = None
    ) -> None:
        self._values = list(values)
        self._diagnostics = dict(diagnostics) if diagnostics else {}

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        return ExtractionResult(
            values=list(self._values), diagnostics=dict(self._diagnostics)
        )
