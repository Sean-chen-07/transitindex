"""Plan B eval/smoke runner -- measures the chunked-hybrid extractor on real PDFs.

This replaces the ad-hoc smoke script. For each catalog doc id it loads the
catalog row, downloads the PDF from Supabase Storage, runs `ChunkedHybridExtractor`
DIRECTLY (not run_pdf -- no staging side-effects), and records the per-doc result in
the same shape as the committed smoke fixture (`tests/fixtures/smoke/`) plus the Plan B
diagnostics (`segments_raw`, `dropped_scope`/`dropped_basis`/`dropped_below_floor`,
timing and cost). It then aggregates totals (values, review rate, conflicts, dropped
counts, est cost), optionally prints a before/after delta against a prior result file
(`--baseline`), and optionally scores any doc with a confirmed gold fixture (`--gold`).

This module writes the runner but DOES NOT run it here: `main()` is step 2.7 (paid,
held for the user). Importing this module needs no network and no API -- the config,
repository, storage and extractor are all constructed lazily inside `main`. The
offline tests drive `run_smoke` / `delta_table` with a FakeExtractor and fake
storage/repo. Pure stdlib otherwise.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Callable, Optional

from ..pdf.chunked_hybrid import REVIEW_CONFIDENCE
from ..pdf.extractor import ExtractionRequest
from ..pdf.llm import LOW_CONFIDENCE_THRESHOLD
from .gold import ExtractedAssessment, EvalReport, load_gold, run_eval

# The 10 docs the Plan B eval run measures (step 2.6 / 2.7).
DEFAULT_DOC_IDS: tuple[int, ...] = (59, 64, 53, 31, 13, 19, 25, 44, 1, 7)

# Default gold directory: confirmed fixtures only (candidates/ is excluded).
_DEFAULT_GOLD_DIR = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "gold"
)

# A value's period_year is "weird" when it falls outside [doc_year - WEIRD_YEAR_BACK,
# doc_year] -- a comparative prior-year column is normal, a decade-old or future year is
# not (forecasts/historical series the metric set does not want at agency level).
WEIRD_YEAR_BACK = 3

# Marker `merge_values` stamps on a cross-chunk disagreement (a real review item).
_CONFLICT_MARKER = "chunks disagree"

# Gold scoring (step 2.6): only annual figures, the agency total, reported actuals.
# A value below the pipeline's low-confidence threshold scores as 'low_confidence'.
_GOLD_SCOPE = "total"
_GOLD_BASIS = "actual"


# --- per-value + per-doc shaping --------------------------------------------


def _value_dict(v) -> dict:
    """One merged ExtractedValue in the smoke-fixture value shape."""
    return {
        "metric": v.metric_code,
        "value": str(v.value),
        "unit": v.unit,
        "period_kind": v.period_kind,
        "year": v.period_year,
        "month": v.period_month,
        "page": v.page_number,
        "conf": str(v.confidence),
        "note": v.note,
        "quote": v.source_quote,
        "scope": v.service_scope,
        "basis": v.basis,
    }


def _is_conflict(v) -> bool:
    return bool(v.note) and _CONFLICT_MARKER in v.note


def _weird_years(values: list, doc_year: int) -> list[int]:
    """Sorted distinct period_years outside the normal [doc_year-N, doc_year] window."""
    low = doc_year - WEIRD_YEAR_BACK
    return sorted({v.period_year for v in values if not (low <= v.period_year <= doc_year)})


def _dups(values: list) -> list[list]:
    """Merge keys that still appear more than once after merge (should be none)."""
    seen: dict[tuple, int] = {}
    for v in values:
        key = (v.metric_code, v.period_kind, v.period_year, v.period_month, v.service_scope, v.basis)
        seen[key] = seen.get(key, 0) + 1
    return [list(k) for k, n in seen.items() if n > 1]


def build_doc_result(doc, slug: str, result, *, elapsed_s: float) -> dict:
    """Shape one extractor run into the smoke-fixture dict (+ Plan B diagnostics).

    `doc` is a catalog Document row, `result` an ExtractionResult. Pure: it reads only
    the result's values and diagnostics, so the offline test drives it with a
    FakeExtractor's output.
    """
    values = result.values
    diag = result.diagnostics
    metrics = sorted({v.metric_code for v in values})
    return {
        "doc_id": doc.id,
        "slug": slug,
        "year": doc.year,
        "doc_type": doc.doc_type,
        "author_label": doc.author_label,
        "time_s": round(elapsed_s, 1),
        "segments": diag.get("segments", 0),
        "md_chunks": diag.get("md_chunks", 0),
        "image_batches": diag.get("image_batches", 0),
        "image_pages": diag.get("image_pages", []),
        "values_merged": len(values),
        "values_raw": diag.get("values_raw", 0),
        "distinct_metrics": len(metrics),
        "metrics": metrics,
        "cost_usd": round(float(diag.get("est_cost_usd", 0.0)), 4),
        "tokens": diag.get("input_tokens", 0),
        "segment_errors": diag.get("errors", {}),
        "conflicts": sum(1 for v in values if _is_conflict(v)),
        "weird_years": _weird_years(values, doc.year),
        "dups": _dups(values),
        "lowconf": sum(1 for v in values if v.confidence <= REVIEW_CONFIDENCE),
        "dropped_below_floor": diag.get("dropped_below_floor", 0),
        "dropped_scope": diag.get("dropped_scope", 0),
        "dropped_basis": diag.get("dropped_basis", 0),
        "segments_raw": diag.get("segments_raw", []),
        "values": [_value_dict(v) for v in values],
    }


# --- aggregation ------------------------------------------------------------


def aggregate(docs: list[dict]) -> dict:
    """Totals across every per-doc result: counts, review rate, est cost."""
    values = sum(d["values_merged"] for d in docs)
    lowconf = sum(d["lowconf"] for d in docs)
    return {
        "docs": len(docs),
        "values_merged": values,
        "values_raw": sum(d["values_raw"] for d in docs),
        "lowconf": lowconf,
        "review_rate": (lowconf / values) if values else 0.0,
        "conflicts": sum(d.get("conflicts", 0) for d in docs),
        # .get: a pre-Plan-B baseline result lacks the dropped_* diagnostic keys.
        "dropped_below_floor": sum(d.get("dropped_below_floor", 0) for d in docs),
        "dropped_scope": sum(d.get("dropped_scope", 0) for d in docs),
        "dropped_basis": sum(d.get("dropped_basis", 0) for d in docs),
        "cost_usd": round(sum(d["cost_usd"] for d in docs), 4),
        "tokens": sum(d["tokens"] for d in docs),
    }


# --- before/after delta (--baseline) ----------------------------------------

# Totals fields the delta table reports (review_rate/cost are floats, the rest ints).
_DELTA_KEYS: tuple[str, ...] = (
    "values_merged", "lowconf", "review_rate", "conflicts",
    "dropped_scope", "dropped_basis", "cost_usd",
)


def _result_totals(result: list[dict] | dict) -> dict:
    """Accept either a raw per-doc list or a {'docs': [...], 'totals': {...}} report."""
    if isinstance(result, dict):
        return result.get("totals") or aggregate(result.get("docs", []))
    return aggregate(result)


def delta_table(baseline: list[dict] | dict, current: list[dict] | dict) -> dict:
    """Per-metric before/after/delta over the two runs' totals (pure math)."""
    before = _result_totals(baseline)
    after = _result_totals(current)
    out: dict[str, dict] = {}
    for k in _DELTA_KEYS:
        b = before.get(k, 0)
        a = after.get(k, 0)
        out[k] = {"before": b, "after": a, "delta": a - b}
    return out


# --- gold scoring (--gold) --------------------------------------------------


def _gold_key(meta: dict) -> tuple[str, int]:
    return (meta["agency_slug"], int(meta["period_year"]))


def load_gold_index(gold_dir: Path) -> dict[tuple[str, int], Path]:
    """Map every confirmed gold fixture's (slug, year) to its path.

    Only top-level files of `gold_dir` are read; the `candidates/` subdirectory
    (unconfirmed) is excluded by globbing files, not recursing.
    """
    index: dict[tuple[str, int], Path] = {}
    for path in sorted(gold_dir.glob("*.json")):
        meta = json.loads(path.read_text(encoding="utf-8"))
        if "agency_slug" in meta and "period_year" in meta:
            index[_gold_key(meta)] = path
    return index


def gold_assessments(values: list, gold_meta: dict) -> list[ExtractedAssessment]:
    """Map merged values onto ExtractedAssessments for one gold fixture.

    Filters to the gold year + period_kind, the agency total scope, reported actuals;
    a value is flagged 'low_confidence' when its confidence is below the gold flag
    threshold (mirrors the pipeline's low-confidence tagging).
    """
    year = int(gold_meta["period_year"])
    kind = gold_meta["period_kind"]
    out: list[ExtractedAssessment] = []
    for v in values:
        if v.period_year != year or v.period_kind != kind:
            continue
        if v.service_scope != _GOLD_SCOPE or v.basis != _GOLD_BASIS:
            continue
        flags = ("low_confidence",) if v.confidence < LOW_CONFIDENCE_THRESHOLD else ()
        out.append(ExtractedAssessment(metric_code=v.metric_code, value=v.value, flags=flags))
    return out


def score_gold(values: list, gold_path: Path, gold_meta: dict) -> EvalReport:
    """run_eval the merged values against one confirmed gold fixture."""
    return run_eval(load_gold(gold_path), gold_assessments(values, gold_meta))


# --- the run ----------------------------------------------------------------


def _slug_for_agency_id(repo, agency_id: int) -> Optional[str]:
    """Reverse the seeded slug->id map (same approach as scan.py)."""
    from ..refdata import AGENCIES

    for slug in AGENCIES:
        try:
            if repo.agency_id(slug) == agency_id:
                return slug
        except ValueError:
            continue
    return None


def run_smoke(
    repo,
    storage,
    doc_ids: list[int],
    extractor_factory: Callable[[], object],
    *,
    gold_dir: Optional[Path] = None,
) -> dict:
    """Run the extractor over every doc id and assemble the full report.

    `extractor_factory` returns the Extractor to run (a fresh one per call so the
    offline test can inject a FakeExtractor). For each doc: load the catalog row,
    download its PDF from `storage`, run the extractor directly with the doc's
    context, and shape the result. When `gold_dir` is given, score any doc whose
    (slug, year) has a confirmed fixture. No staging, no run_pdf.
    """
    gold_index = load_gold_index(gold_dir) if gold_dir is not None else {}

    docs: list[dict] = []
    gold_reports: dict[int, dict] = {}
    for doc_id in doc_ids:
        doc = repo.get_document(doc_id)
        if doc is None:
            raise ValueError(f"unknown document id {doc_id}")
        slug = _slug_for_agency_id(repo, doc.agency_id)
        if slug is None:
            raise RuntimeError(f"could not resolve a slug for agency_id {doc.agency_id}")

        pdf_bytes = storage.download(doc.storage_key)
        request = ExtractionRequest(
            agency_slug=slug,
            pdf_bytes=pdf_bytes,
            doc_type=doc.doc_type,
            author_label=doc.author_label,
            doc_year=doc.year,
        )
        started = time.monotonic()
        result = extractor_factory().extract(request)
        elapsed = time.monotonic() - started

        docs.append(build_doc_result(doc, slug, result, elapsed_s=elapsed))

        gold_path = gold_index.get((slug, doc.year))
        if gold_path is not None:
            gold_meta = json.loads(gold_path.read_text(encoding="utf-8"))
            report = score_gold(result.values, gold_path, gold_meta)
            gold_reports[doc_id] = {
                "fixture": gold_path.name,
                "precision": report.precision,
                "flag_recall": report.flag_recall,
                "clean_count": report.clean_count,
            }

    out: dict = {"docs": docs, "totals": aggregate(docs)}
    if gold_dir is not None:
        out["gold"] = gold_reports
    return out


# --- CLI --------------------------------------------------------------------


def _parse_doc_ids(raw: str) -> list[int]:
    return [int(part) for part in raw.split(",") if part.strip()]


def _print_totals(report: dict) -> None:
    t = report["totals"]
    print(
        f"\n{len(report['docs'])} docs | "
        f"{t['values_merged']} values | review rate {t['review_rate'] * 100:.1f}% "
        f"({t['lowconf']} conf<={REVIEW_CONFIDENCE}) | {t['conflicts']} conflicts | "
        f"dropped scope/basis/floor {t['dropped_scope']}/{t['dropped_basis']}/{t['dropped_below_floor']} | "
        f"est ${t['cost_usd']:.2f} ({t['tokens']} tok)"
    )


def _print_delta(table: dict) -> None:
    print("\nbaseline -> this run:")
    for k, d in table.items():
        print(f"  {k:<20} {d['before']!s:>14} -> {d['after']!s:>14}  ({d['delta']:+})")


def _print_gold(report: dict) -> None:
    gold = report.get("gold") or {}
    if not gold:
        return
    print("\ngold scores:")
    for doc_id, g in gold.items():
        print(
            f"  doc {doc_id} {g['fixture']}: precision {g['precision']:.2f} "
            f"flag_recall {g['flag_recall']:.2f} (clean {g['clean_count']})"
        )


def main(argv: Optional[list[str]] = None) -> int:
    """PAID -- step 2.7 only. Downloads PDFs and calls the Anthropic API."""
    parser = argparse.ArgumentParser(
        description="Plan B eval/smoke run of the chunked-hybrid extractor (PAID)."
    )
    parser.add_argument(
        "--docs", default=",".join(str(d) for d in DEFAULT_DOC_IDS),
        help="comma-separated catalog doc ids (default: the Plan B eval set).",
    )
    parser.add_argument("--out", type=Path, required=True, help="path to write the result JSON.")
    parser.add_argument(
        "--baseline", type=Path, default=None,
        help="a prior result JSON to print a before/after delta against.",
    )
    parser.add_argument(
        "--gold", type=Path, default=None, nargs="?", const=_DEFAULT_GOLD_DIR,
        help="score docs with a confirmed gold fixture (default dir: tests/fixtures/gold).",
    )
    args = parser.parse_args(argv)

    # Lazy: building config/repo/storage/extractor is what touches creds + network.
    from ..config import load_config
    from ..db.postgres import PostgresRepository
    from ..pdf.chunked_hybrid import ChunkedHybridExtractor
    from ..storage import SupabaseStorage

    cfg = load_config()
    if not cfg.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY is not set -- this run calls the Anthropic API.")
    repo = PostgresRepository(cfg.database_url)
    storage = SupabaseStorage.from_config(cfg)

    report = run_smoke(
        repo,
        storage,
        _parse_doc_ids(args.docs),
        lambda: ChunkedHybridExtractor(cfg.anthropic_api_key),
        gold_dir=args.gold,
    )

    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", args.out)
    _print_totals(report)
    _print_gold(report)
    if args.baseline is not None:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        _print_delta(delta_table(baseline, report))
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
