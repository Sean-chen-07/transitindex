"""PDF text extraction.

`extract_pages` reads a real PDF with pdfplumber, imported LAZILY so importing
this module never requires the dependency (the offline suite has no pdfplumber).
`pages_from_text` is the passthrough that lets callers and tests feed
pre-extracted page text without a PDF.
"""

from __future__ import annotations

from pathlib import Path

# A page is (page_number, text); page numbers are 1-based, matching how a human
# cites a PDF and what core.metric_value_sources.page_number stores.
Page = tuple[int, str]


def extract_pages(pdf_path: str | Path) -> list[Page]:
    """Return [(page_number, text), ...] for every page of `pdf_path`.

    pdfplumber is imported here, not at module top, so the rest of the pipeline
    (and the offline test suite) can import this module without the dependency.
    """
    import pdfplumber  # lazy: only needed for real PDF I/O

    pages: list[Page] = []
    with pdfplumber.open(str(pdf_path)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            pages.append((i, page.extract_text() or ""))
    return pages


def pages_from_text(texts: list[str]) -> list[Page]:
    """Wrap a list of page strings into [(page_number, text), ...].

    The offline door into the pipeline: supply page text directly, no PDF.
    """
    return [(i, text) for i, text in enumerate(texts, start=1)]
