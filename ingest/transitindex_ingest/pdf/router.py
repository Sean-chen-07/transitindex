"""Per-report model routing: spend the expensive model only where it pays off.

The whole-PDF extractor reads numbers off the rendered page, so the model's job
is hardest on *scanned* pages -- ones with no text layer, where every figure must
be read pixel-by-pixel. `RoutingExtractor` looks at a report once, before any API
call, and picks the model accordingly:

  - mostly scanned / image-heavy  -> a premium model (accuracy is worth the cost)
  - clean digital text            -> a cheap model   (where the savings come from)

The signal is free: the prefilter already pulls per-page text with pypdf, and a
page whose extracted text is near-empty is almost certainly a scan. We classify
only the pages the prefilter would actually send (`select_page_indices`), so the
decision tracks what the model really sees.

It implements the `Extractor` seam, so it drops into `run_pdf` with no pipeline
change -- exactly like `DualModelExtractor`. The model line-up swaps by editing
`claude_routed`'s defaults; nothing else moves.

Pure stdlib at import time: `anthropic` arrives lazily via the wrapped
`ClaudePdfExtractor`s (built only in `claude_routed`), and `pypdf` arrives lazily
inside `_page_texts`. The routing decision itself (`route_from_texts`) is pure --
no pypdf, no network -- so it is unit-testable on plain lists of strings.
"""

from __future__ import annotations

from typing import Optional

from .claude_pdf import select_page_indices  # pure: no anthropic/pypdf pulled
from .extractor import ExtractionRequest, ExtractionResult, Extractor

# A page whose stripped extracted text is shorter than this carries no usable
# text layer -- the signature of a scanned/image page. Generous on purpose: a
# real digital page (even a sparse chart page with a caption) clears it easily.
DEFAULT_IMAGE_TEXT_THRESHOLD = 120

# Route to the premium model once this fraction of the sent pages look scanned.
# Low on purpose: if even a quarter of the report is image-only, the accuracy of
# the strong model is worth paying for across the whole document.
DEFAULT_IMAGE_CUTOFF = 0.25

# The model line-up. Premium = best accuracy-per-dollar for hard scans; cheap =
# the bill-cutter for clean text. Change these two strings to re-tune the trade.
DEFAULT_PREMIUM_MODEL = "claude-opus-4-8"
DEFAULT_CHEAP_MODEL = "claude-haiku-4-5"


def route_from_texts(
    page_texts: list[str],
    *,
    max_pages: int,
    image_text_threshold: int,
    image_cutoff: float,
    premium: str,
    cheap: str,
) -> tuple[str, dict]:
    """Pick a model for a document from its per-page extracted text.

    Looks only at the pages the prefilter would send (`select_page_indices`),
    counts how many carry almost no extractable text (scanned/image pages), and
    routes to `premium` when that fraction reaches `image_cutoff`. Returns the
    chosen model id and a diagnostics dict explaining the decision. Pure: no
    pypdf, no network.
    """
    if not page_texts:
        # No text at all -- can't tell, so don't risk the cheap model.
        return premium, {
            "routed_to": premium,
            "reason": "no_text_extracted",
            "image_fraction": 1.0,
            "pages_scanned": 0,
            "pages_considered": 0,
            "image_cutoff": image_cutoff,
        }

    kept = select_page_indices(page_texts, max_pages)
    considered = len(kept)
    scanned = sum(1 for i in kept if len(page_texts[i].strip()) < image_text_threshold)
    fraction = scanned / considered if considered else 1.0
    model = premium if fraction >= image_cutoff else cheap
    return model, {
        "routed_to": model,
        "reason": "image_heavy" if model == premium else "text_clean",
        "image_fraction": round(fraction, 3),
        "pages_scanned": scanned,
        "pages_considered": considered,
        "image_cutoff": image_cutoff,
    }


def _page_texts(pdf_bytes: bytes) -> list[str]:
    """Per-page extracted text via pypdf (lazy: classification only)."""
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(pdf_bytes))
    return [(page.extract_text() or "") for page in reader.pages]


class RoutingExtractor:
    """Route one document to the right pre-built extractor, then delegate.

    Constructed with a {model_id: Extractor} mapping plus the `premium`/`cheap`
    model ids (both must be keys). On each call it classifies the PDF and hands
    the request to the chosen extractor unchanged, annotating the returned
    diagnostics with a `routing` block so the decision is visible. Use
    `claude_routed()` to build the real Opus/Haiku line-up.
    """

    def __init__(
        self,
        extractors: dict[str, Extractor],
        *,
        premium: str,
        cheap: str,
        image_cutoff: float = DEFAULT_IMAGE_CUTOFF,
        image_text_threshold: int = DEFAULT_IMAGE_TEXT_THRESHOLD,
        max_pages: int = 15,
    ) -> None:
        if premium not in extractors or cheap not in extractors:
            raise ValueError("premium and cheap must both be keys in `extractors`")
        self._by_model = dict(extractors)
        self._premium = premium
        self._cheap = cheap
        self._image_cutoff = image_cutoff
        self._image_text_threshold = image_text_threshold
        self._max_pages = max_pages

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        model, routing = self._route(request)
        result = self._by_model[model].extract(request)
        diag = dict(result.diagnostics)
        diag["extractor"] = "routed"
        diag["routing"] = routing
        return ExtractionResult(values=result.values, diagnostics=diag)

    def _route(self, request: ExtractionRequest) -> tuple[str, dict]:
        if request.pdf_bytes is None:
            # Pages-only fallback: there's no rendered page to scan -- it's
            # already text, so the cheap model is the right call.
            return self._cheap, {"routed_to": self._cheap, "reason": "pages_only_text"}

        try:
            texts: Optional[list[str]] = _page_texts(request.pdf_bytes)
        except Exception:
            texts = None
        if texts is None:
            # pypdf couldn't read it -- treat like an unreadable scan, use premium.
            return self._premium, {
                "routed_to": self._premium,
                "reason": "unreadable_default_premium",
            }

        return route_from_texts(
            texts,
            max_pages=self._max_pages,
            image_text_threshold=self._image_text_threshold,
            image_cutoff=self._image_cutoff,
            premium=self._premium,
            cheap=self._cheap,
        )


def claude_routed(
    api_key: str,
    *,
    premium: str = DEFAULT_PREMIUM_MODEL,
    cheap: str = DEFAULT_CHEAP_MODEL,
    image_cutoff: float = DEFAULT_IMAGE_CUTOFF,
    image_text_threshold: int = DEFAULT_IMAGE_TEXT_THRESHOLD,
    verify: bool = True,
    prefilter: bool = True,
    max_pages: int = 15,
) -> RoutingExtractor:
    """Build a RoutingExtractor over one real ClaudePdfExtractor per model.

    Both models keep the single-model verify pass (verify=True) and the same
    prefilter/max_pages, so the only thing that changes per report is which model
    reads it. `max_pages` is shared with the router so the pages it classifies are
    the pages that actually get sent.
    """
    from .claude_pdf import ClaudePdfExtractor  # lazy: pulls anthropic

    def build(model: str) -> Extractor:
        return ClaudePdfExtractor(
            api_key, model=model, verify=verify, prefilter=prefilter, max_pages=max_pages
        )

    extractors: dict[str, Extractor] = {premium: build(premium)}
    if cheap not in extractors:
        extractors[cheap] = build(cheap)

    return RoutingExtractor(
        extractors,
        premium=premium,
        cheap=cheap,
        image_cutoff=image_cutoff,
        image_text_threshold=image_text_threshold,
        max_pages=max_pages,
    )
