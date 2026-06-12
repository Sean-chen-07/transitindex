"""Offline replay report against the recorded smoke fixture (Plan A step 1.7).

Re-runs Phase 1's two key offline fixes over the FROZEN smoke recording
(`tests/fixtures/smoke/`) without any API call, to size the review-burden
improvement before a live run pays for one:

  1. Conflict collapse -- every recorded ``⚠ chunks disagree — v1, v2[, ...]``
     note is re-parsed into its candidate list and run through step 1.2's merge
     spread rule (`_within_merge_tolerance`); a group within 0.5% collapses to one
     reading (no longer a review item), a wider spread survives as a real conflict.
  2. Quote check -- step 1.4's `quote_supports_value` is run over each recorded
     (value, quote) pair. Recorded values are post-scaling, so the as-printed
     digits are approximated leniently: the value's integer digits with trailing
     zeros stripped must appear in the quote's normalized digits.

It prints a per-doc + totals table and writes `ingest/_replay_report.json`
(untracked, like the smoke file). This is a REPORT, not a gate -- it imports the
real merge-tolerance helper and quote checker so the numbers track the code.
Pure stdlib; no API, no PDF.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ..pdf.chunked_hybrid import REVIEW_CONFIDENCE, _within_merge_tolerance
from ..pdf.llm import quote_supports_value

# The committed smoke recording is the default "before" baseline (parents[2] is ingest/).
_DEFAULT_SMOKE = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "smoke" / "smoke10_2026-06-12.json"
)
# Untracked replay output lands directly under ingest/, beside _smoke10_result.json.
_REPORT_PATH = Path(__file__).resolve().parents[2] / "_replay_report.json"

# Matches the conflict note `merge_values` stamps: `⚠ chunks disagree — <v1>, <v2>
# [, ...] (reviewer confirm)`, anywhere in the note (a caveat prefix may precede it).
_CONFLICT_RE = re.compile(r"⚠ chunks disagree — (.+?) \(reviewer confirm\)")


def _conflict_candidates(note: str | None) -> list[Decimal] | None:
    """The candidate Decimals from a disagree note, or None if the note is not one.

    `12060661000, 12059032000, 12060661000` -> [Decimal, Decimal, Decimal]. A note
    whose candidates don't all parse as numbers is skipped (returns None)."""
    if not note:
        return None
    m = _CONFLICT_RE.search(note)
    if not m:
        return None
    try:
        return [Decimal(part.strip()) for part in m.group(1).split(",")]
    except InvalidOperation:
        return None


def _printed_digits(value: str) -> str:
    """Lenient as-printed approximation of a post-scaling recorded value: the integer
    part's digits with trailing zeros stripped (`525500000.0` -> `5255`). Empty when
    the value rounds to zero -- such a reading can't be quote-checked this way."""
    try:
        magnitude = abs(int(Decimal(value)))
    except (InvalidOperation, ValueError):
        return ""
    digits = str(magnitude).rstrip("0")
    return digits


def _replay_doc(entry: dict) -> dict:
    """Replay the conflict-collapse and quote-check fixes over one doc's values."""
    values = entry["values"]
    collapsed = 0
    surviving = 0
    for v in values:
        candidates = _conflict_candidates(v.get("note"))
        if candidates is None:
            continue
        if _within_merge_tolerance(candidates):
            collapsed += 1
        else:
            surviving += 1

    quote_match = quote_missing = quote_mismatch = 0
    for v in values:
        printed = _printed_digits(v["value"])
        if not printed:  # zero-magnitude reading: skip the digit check
            continue
        support = quote_supports_value(printed, v.get("quote"))
        if support is None:
            quote_match += 1
        elif support == "missing":
            quote_missing += 1
        else:
            quote_mismatch += 1

    # conf<=0.5 before vs an estimate after: collapsed conflicts climb back above
    # the review line, and unit-label false conflicts (a low-conf reading whose only
    # demerit is a stale unit) no longer exist -- approximated here as the collapsed
    # conflicts plus any other recorded conf<=0.5 value that is NOT a surviving conflict.
    lowconf_before = sum(1 for v in values if Decimal(v["conf"]) <= REVIEW_CONFIDENCE)
    lowconf_after = lowconf_before - collapsed
    return {
        "doc_id": entry["doc_id"],
        "slug": entry["slug"],
        "year": entry["year"],
        "values": len(values),
        "conflicts_before": collapsed + surviving,
        "conflicts_after": surviving,
        "collapsed": collapsed,
        "lowconf_before": lowconf_before,
        "lowconf_after": lowconf_after,
        "quote_match": quote_match,
        "quote_missing": quote_missing,
        "quote_mismatch": quote_mismatch,
    }


def replay(smoke_json: Path) -> dict:
    """Replay every doc in a smoke fixture; return {'docs': [...], 'totals': {...}}."""
    smoke = json.loads(Path(smoke_json).read_text(encoding="utf-8"))
    docs = [_replay_doc(entry) for entry in smoke]
    totals_keys = (
        "values", "conflicts_before", "conflicts_after", "collapsed",
        "lowconf_before", "lowconf_after", "quote_match", "quote_missing", "quote_mismatch",
    )
    totals = {k: sum(d[k] for d in docs) for k in totals_keys}
    return {"docs": docs, "totals": totals}


_HEADER = (
    f"{'doc':>4}  {'slug':<16} {'year':>4} {'vals':>5} "
    f"{'conf<=.5 before':>15} {'conf<=.5 after':>14} "
    f"{'confl before':>12} {'confl after':>11}"
)


def _format_row(d: dict) -> str:
    return (
        f"{d['doc_id']:>4}  {d['slug']:<16} {d['year']:>4} {d['values']:>5} "
        f"{d['lowconf_before']:>15} {d['lowconf_after']:>14} "
        f"{d['conflicts_before']:>12} {d['conflicts_after']:>11}"
    )


def _format_totals(t: dict) -> str:
    return (
        f"{'TOT':>4}  {'(all docs)':<16} {'':>4} {t['values']:>5} "
        f"{t['lowconf_before']:>15} {t['lowconf_after']:>14} "
        f"{t['conflicts_before']:>12} {t['conflicts_after']:>11}"
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Replay Phase 1's offline fixes over a recorded smoke fixture."
    )
    parser.add_argument(
        "smoke_json", type=Path, nargs="?", default=_DEFAULT_SMOKE,
        help="path to a smoke fixture JSON (default: the committed smoke10 fixture)",
    )
    args = parser.parse_args()

    report = replay(args.smoke_json)
    print(_HEADER)
    for d in report["docs"]:
        print(_format_row(d))
    print(_format_totals(report["totals"]))

    t = report["totals"]
    print(
        f"\nquote check (all docs): {t['quote_match']} match, "
        f"{t['quote_missing']} missing, {t['quote_mismatch']} mismatch"
    )
    _REPORT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("wrote", _REPORT_PATH)


if __name__ == "__main__":  # pragma: no cover
    main()
