"""Dual-model extraction: run two models independently, then reconcile for review.

`DualModelExtractor` runs each configured model's extractor in parallel (threads --
each call is network-bound), then compares their findings per (metric, period):

  - both models AGREE on the value      -> trusted, kept at the higher confidence
  - they DISAGREE, or only one found it  -> flagged low-confidence, with every
                                            candidate spelled out in the note

Because flagged values land below the pipeline's low-confidence threshold, the
human review queue surfaces exactly the spots a person needs to confirm or fix --
the agreements pass through quietly. It implements the `Extractor` seam, so it
drops into `run_pdf` with no pipeline change; a future model line-up swaps in by
editing only the construction site.

Pure stdlib at import time: `anthropic`/`pypdf` arrive lazily via the wrapped
`ClaudePdfExtractor`s, built only in `claude_dual`.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal

from .extractor import ExtractionRequest, ExtractionResult, Extractor
from .llm import ExtractedValue

# Confidence stamped on a value that needs a human look (disagreement or a
# single-model find). Below the pipeline's 0.7 low_confidence threshold so it
# always surfaces in the review queue.
REVIEW_CONFIDENCE = Decimal("0.5")


def _key(v: ExtractedValue):
    """The identity a value is matched on across models: metric + period."""
    return (v.metric_code, v.period_kind, v.period_year, v.period_month)


def _with_note(existing, addition: str) -> str:
    return addition if not existing else f"{existing}; {addition}"


def reconcile(per_model: dict[str, list[ExtractedValue]]) -> list[ExtractedValue]:
    """Merge each model's values into one review-ready list.

    Agreements keep their (higher) confidence and an agreement note; disagreements
    and single-model finds are dropped to REVIEW_CONFIDENCE with every candidate
    listed in the note. Input order of `per_model` sets model priority (the first
    model's value is the one carried forward on a disagreement).
    """
    labels = list(per_model)
    grouped: dict[str, dict] = {label: {} for label in labels}
    for label in labels:
        for v in per_model[label]:
            grouped[label].setdefault(_key(v), v)  # first occurrence per model wins

    # All keys, in first-seen order across the models.
    ordered_keys: list = []
    seen = set()
    for label in labels:
        for k in grouped[label]:
            if k not in seen:
                seen.add(k)
                ordered_keys.append(k)

    out: list[ExtractedValue] = []
    for k in ordered_keys:
        found = [(label, grouped[label][k]) for label in labels if k in grouped[label]]

        if len(found) == len(labels) and len(labels) > 1:
            values = [v for _, v in found]
            if all(v.value == values[0].value for v in values):
                primary = max(values, key=lambda v: v.confidence)
                names = " + ".join(label for label, _ in found)
                out.append(replace(primary, note=_with_note(primary.note, f"✓ {names} agree")))
            else:
                primary = found[0][1]
                detail = "; ".join(f"{label}={v.value} {v.unit}" for label, v in found)
                out.append(
                    replace(
                        primary,
                        confidence=min(primary.confidence, REVIEW_CONFIDENCE),
                        note=_with_note(primary.note, f"⚠ models disagree — {detail} (reviewer confirm)"),
                    )
                )
        else:
            label, v = found[0]
            out.append(
                replace(
                    v,
                    confidence=min(v.confidence, REVIEW_CONFIDENCE),
                    note=_with_note(v.note, f"⚠ only {label} found this (reviewer confirm)"),
                )
            )
    return out


class DualModelExtractor:
    """Run several extractors over one document in parallel and reconcile them.

    Constructed with a {label: Extractor} mapping (label is usually the model id).
    Each extractor runs in its own thread; one failing is recorded in diagnostics
    rather than sinking the run. The reconciled values implement the review policy
    above. Use `claude_dual()` to build the real Opus+Sonnet line-up.
    """

    def __init__(self, extractors: dict[str, Extractor]) -> None:
        if not extractors:
            raise ValueError("DualModelExtractor needs at least one extractor")
        self._extractors = dict(extractors)

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        per_model: dict[str, list[ExtractedValue]] = {}
        errors: dict[str, str] = {}
        per_model_diag: dict[str, dict] = {}

        with ThreadPoolExecutor(max_workers=len(self._extractors)) as pool:
            futures = {
                label: pool.submit(ext.extract, request)
                for label, ext in self._extractors.items()
            }
            for label, fut in futures.items():
                try:
                    res = fut.result()
                    per_model[label] = res.values
                    per_model_diag[label] = res.diagnostics
                except Exception as exc:  # one model failing must not sink the run
                    errors[label] = f"{type(exc).__name__}: {exc}"

        values = reconcile(per_model)
        diagnostics = {
            "extractor": "dual_model",
            "models": list(self._extractors),
            "per_model_counts": {label: len(v) for label, v in per_model.items()},
            "reconciled_count": len(values),
            "needs_review": sum(1 for v in values if v.confidence < Decimal("0.7")),
            "errors": errors,
            "est_cost_usd": sum(
                float(d.get("est_cost_usd", 0) or 0) for d in per_model_diag.values()
            ),
            "per_model_diagnostics": per_model_diag,
        }
        return ExtractionResult(values=values, diagnostics=diagnostics)


def claude_dual(
    api_key: str,
    models: tuple[str, ...] = ("claude-opus-4-8", "claude-sonnet-4-6"),
    *,
    verify: bool = False,
    prefilter: bool = True,
    max_pages: int = 15,
) -> DualModelExtractor:
    """Build a DualModelExtractor over one real ClaudePdfExtractor per model.

    verify defaults to False: cross-checking two independent models REPLACES the
    single-model verify pass (a second model is a stronger, cheaper check than the
    same model re-reading its own answer).
    """
    from .claude_pdf import ClaudePdfExtractor  # lazy: pulls anthropic

    return DualModelExtractor(
        {
            m: ClaudePdfExtractor(
                api_key, model=m, verify=verify, prefilter=prefilter, max_pages=max_pages
            )
            for m in models
        }
    )
