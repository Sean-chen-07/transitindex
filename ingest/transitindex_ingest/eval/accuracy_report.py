"""Offline accuracy report -- the free before/after instrument for extraction work.

Given per-doc extraction results in the shape `eval/smoke.py:build_doc_result`
produces (and the frozen smoke recording `eval/replay.py` reads), this emits one
compact summary:

  * totals -- values, flagged values broken down by flag, low-confidence count,
    review rate;
  * per-doc counts;
  * per-gold-doc precision / flag_recall, for every doc whose (slug, year) has a
    CONFIRMED gold fixture (`tests/fixtures/gold/*.json`; the `candidates/` and
    `synthetic/` subdirectories are excluded by `load_gold_index`).

Nothing here calls an API or reads a PDF, so it can be run before and after any
offline change to size the effect for free.

One honest caveat: the two confirmed 2019 fixtures were promoted from rows of
the frozen smoke recording itself, so scoring THAT recording against them is
partly circular -- expect precision 1.00 there. Their value is as a fixed target
for future runs and for changes that alter which value survives a merge.

Pure stdlib.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Optional

from ..pdf.chunked_hybrid import REVIEW_CONFIDENCE
from ..pdf.llm import LOW_CONFIDENCE_THRESHOLD, quote_supports_value
from .gold import ExtractedAssessment, load_gold, run_eval
from .smoke import load_gold_index

# Default gold dir: confirmed fixtures only (ingest/tests/fixtures/gold).
DEFAULT_GOLD_DIR = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "gold"

# Marker `merge_values` stamps on a cross-chunk disagreement.
_CONFLICT_MARKER = "chunks disagree"

# Flag names this module reports, in a stable order.
FLAG_NAMES: tuple[str, ...] = (
    "low_confidence",
    "review_confidence",
    "conflict",
    "quote_missing",
    "quote_mismatch",
)

# Flags gold.py understands (anything else is reporting-only and must not change
# what counts as a 'clean' value in the precision pool).
_GOLD_FLAGS = frozenset({"low_confidence"})

# A recorded value's scope/basis is None on pre-Plan-B recordings; treat that as
# the agency total / reported actual rather than dropping the value.
_TOTAL_SCOPES = (None, "total")
_ACTUAL_BASES = (None, "actual")


def _decimal(raw) -> Optional[Decimal]:
    try:
        return Decimal(str(raw))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _printed_digits(value: str) -> str:
    """Lenient as-printed digits of a post-scaling value (`525500000.0` -> `5255`).

    Empty when the value rounds to zero -- such a reading can't be quote-checked.
    """
    dec = _decimal(value)
    if dec is None:
        return ""
    return str(abs(int(dec))).rstrip("0")


def quote_support(printed: str, quote: Optional[str]) -> Optional[str]:
    """`quote_supports_value`, retried once against a point-stripped quote.

    A decimal-printed figure ("525.5" under a millions header) scales to
    525500000, whose lenient printed digits are "5255" -- the decimal point in
    the quote blocks the substring test and reports a false mismatch.
    """
    support = quote_supports_value(printed, quote)
    if support == "mismatch" and quote and "." in quote:
        support = quote_supports_value(printed, quote.replace(".", ""))
    return support


def value_flags(value: dict) -> tuple[str, ...]:
    """Every flag one recorded value carries, in FLAG_NAMES order.

    Derived from the recording itself (confidence, conflict note, quote support)
    and unioned with any explicit `flags` list a staged record carries.
    """
    found: set[str] = set(value.get("flags") or ())

    conf = _decimal(value.get("conf"))
    if conf is not None:
        if conf < LOW_CONFIDENCE_THRESHOLD:
            found.add("low_confidence")
        if conf <= REVIEW_CONFIDENCE:
            found.add("review_confidence")

    note = value.get("note")
    if note and _CONFLICT_MARKER in note:
        found.add("conflict")

    printed = _printed_digits(str(value.get("value")))
    if printed:
        support = quote_support(printed, value.get("quote"))
        if support == "missing":
            found.add("quote_missing")
        elif support == "mismatch":
            found.add("quote_mismatch")

    ordered = [f for f in FLAG_NAMES if f in found]
    ordered += sorted(f for f in found if f not in FLAG_NAMES)
    return tuple(ordered)


def _doc_summary(doc: dict) -> dict:
    values = doc.get("values") or []
    flags = [value_flags(v) for v in values]
    counts: dict[str, int] = {name: 0 for name in FLAG_NAMES}
    for f in flags:
        for name in f:
            counts[name] = counts.get(name, 0) + 1
    flagged = sum(1 for f in flags if f)
    return {
        "doc_id": doc.get("doc_id"),
        "slug": doc.get("slug"),
        "year": doc.get("year"),
        "values": len(values),
        "flagged": flagged,
        "low_confidence": counts.get("low_confidence", 0),
        "review_rate": (flagged / len(values)) if values else 0.0,
        "flags": counts,
    }


def _gold_assessments(values: Iterable[dict], gold_meta: dict) -> list[ExtractedAssessment]:
    """The recorded values that a gold fixture's rows can be matched against.

    Keeps the gold year + period_kind, the agency total scope and reported
    actuals, and carries only the flags gold.py scores on.
    """
    year = int(gold_meta["period_year"])
    kind = gold_meta["period_kind"]
    out: list[ExtractedAssessment] = []
    for v in values:
        if v.get("year") != year or v.get("period_kind") != kind:
            continue
        if v.get("scope") not in _TOTAL_SCOPES or v.get("basis") not in _ACTUAL_BASES:
            continue
        dec = _decimal(v.get("value"))
        if dec is None:
            continue
        flags = tuple(f for f in value_flags(v) if f in _GOLD_FLAGS)
        out.append(ExtractedAssessment(metric_code=v["metric"], value=dec, flags=flags))
    return out


def _score_gold(doc: dict, gold_path: Path) -> dict:
    gold_meta = json.loads(gold_path.read_text(encoding="utf-8"))
    records = load_gold(gold_path)
    report = run_eval(records, _gold_assessments(doc.get("values") or [], gold_meta))
    return {
        "doc_id": doc.get("doc_id"),
        "slug": doc.get("slug"),
        "year": doc.get("year"),
        "fixture": gold_path.name,
        "gold_rows": len(report.rows),
        "matched": sum(1 for r in report.rows if r.matched),
        "clean_count": report.clean_count,
        "precision": report.precision,
        "flag_recall": report.flag_recall,
    }


def accuracy_report(docs: list[dict], *, gold_dir: Optional[Path] = DEFAULT_GOLD_DIR) -> dict:
    """Summarize a list of per-doc extraction results; score confirmed gold docs.

    `gold_dir=None` skips gold scoring entirely.
    """
    per_doc = [_doc_summary(d) for d in docs]

    values = sum(d["values"] for d in per_doc)
    flagged = sum(d["flagged"] for d in per_doc)
    flag_totals: dict[str, int] = {name: 0 for name in FLAG_NAMES}
    for d in per_doc:
        for name, n in d["flags"].items():
            flag_totals[name] = flag_totals.get(name, 0) + n

    totals = {
        "docs": len(per_doc),
        "values": values,
        "flagged": flagged,
        "low_confidence": flag_totals.get("low_confidence", 0),
        "review_rate": (flagged / values) if values else 0.0,
        "flags": flag_totals,
    }

    gold: list[dict] = []
    if gold_dir is not None:
        index = load_gold_index(Path(gold_dir))
        for doc in docs:
            path = index.get((doc.get("slug"), doc.get("year")))
            if path is not None:
                gold.append(_score_gold(doc, path))

    return {"totals": totals, "docs": per_doc, "gold": gold}


# --- formatting -------------------------------------------------------------


def format_report(report: dict) -> str:
    """The compact human-readable rendering (what replay prints)."""
    t = report["totals"]
    lines = [
        f"accuracy: {t['docs']} docs | {t['values']} values | "
        f"{t['flagged']} flagged ({t['review_rate'] * 100:.1f}% review rate) | "
        f"{t['low_confidence']} low-confidence (conf<{LOW_CONFIDENCE_THRESHOLD})"
    ]
    flags = ", ".join(f"{name} {n}" for name, n in t["flags"].items() if n) or "none"
    lines.append(f"  flags: {flags}")

    if not report["gold"]:
        lines.append("  gold: no confirmed fixture matched any doc")
        return "\n".join(lines)

    lines.append("  gold:")
    for g in report["gold"]:
        lines.append(
            f"    doc {g['doc_id']} {g['fixture']}: precision {g['precision']:.2f} "
            f"flag_recall {g['flag_recall']:.2f} "
            f"(matched {g['matched']}/{g['gold_rows']}, clean {g['clean_count']})"
        )
    return "\n".join(lines)
