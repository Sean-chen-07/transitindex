"""Derive *candidate* gold fixtures from recorded smoke data.

A gold fixture (`tests/fixtures/gold/<slug>_annual_<year>.json`,
format in `eval/gold.py:load_gold`) is hand-verified. To seed that human review
without re-keying numbers from the PDF, this module distills the recorded smoke
run (`tests/fixtures/smoke/`) into one candidate record per metric for a single
doc-year, in the exact gold record shape plus an `evidence` block the reviewer
can check against (`load_gold` ignores extra keys).

A candidate is NOT gold. Its `description` says so, and nothing here writes into
`gold/` -- the project owner confirms each file by hand and moves it there. Pure
stdlib; no API, no PDF.
"""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

from ..refdata import METRICS

# Only annual figures for the doc's own reporting year are gold candidates; the
# tolerance every candidate row carries (relative), and the flag default the
# human flips on genuinely ambiguous figures.
_PERIOD_KIND = "annual"
_TOLERANCE = "0.005"
_SHOULD_FLAG = False

_DESCRIPTION = (
    "CANDIDATE — UNCONFIRMED, do not use in eval until moved to gold/. "
    "Auto-derived from the recorded smoke run: one record per metric (highest "
    "confidence reading), restricted to annual figures for the document's own "
    "year. Units are the canonical refdata unit. The reviewer checks each row "
    "against its `evidence` (page / quote / note), fixes or deletes wrong rows, "
    "sets `should_flag: true` on ambiguous figures, then renames to "
    "<slug>_annual_<year>.json and moves the file into gold/."
)


def _doc_entry(smoke: list[dict], doc_id: int) -> dict:
    """The smoke entry for `doc_id` (raises if absent)."""
    for entry in smoke:
        if entry["doc_id"] == doc_id:
            return entry
    raise ValueError(f"doc_id {doc_id} not found in smoke fixture")


def _best_per_metric(values: list[dict], year: int) -> dict[str, dict]:
    """Highest-confidence annual reading for the doc's own year, keyed by metric.

    Ties keep the first reading seen (recorded order).
    """
    best: dict[str, dict] = {}
    for v in values:
        if v["period_kind"] != _PERIOD_KIND or v["year"] != year:
            continue
        code = v["metric"]
        current = best.get(code)
        if current is None or Decimal(v["conf"]) > Decimal(current["conf"]):
            best[code] = v
    return best


def _record(value: dict) -> dict:
    """One gold-shaped record (canonical unit) plus an `evidence` block."""
    code = value["metric"]
    return {
        "metric_code": code,
        "true_value": value["value"],
        "unit": METRICS[code]["unit"],
        "tolerance": _TOLERANCE,
        "should_flag": _SHOULD_FLAG,
        "evidence": {
            "page": value["page"],
            "conf": value["conf"],
            "quote": value["quote"],
            "note": value["note"],
        },
    }


def derive_candidates(smoke_json: Path, doc_id: int, out_dir: Path) -> Path:
    """Write a candidate gold fixture for one smoke doc; return its path.

    Keeps only annual values for the doc's own year, one record per metric (the
    highest-confidence reading), with the canonical refdata unit. The file lands
    in `out_dir` named `<slug>_annual_<year>_doc<doc_id>.json` (the doc_id keeps
    same-agency-year candidates from different documents distinct).
    """
    smoke = json.loads(Path(smoke_json).read_text(encoding="utf-8"))
    entry = _doc_entry(smoke, doc_id)
    year = entry["year"]
    slug = entry["slug"]

    best = _best_per_metric(entry["values"], year)
    records = [_record(best[code]) for code in sorted(best)]

    candidate = {
        "agency_slug": slug,
        "period_year": year,
        "period_kind": _PERIOD_KIND,
        "description": _DESCRIPTION,
        "records": records,
    }

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{slug}_annual_{year}_doc{doc_id}.json"
    out_path.write_text(
        json.dumps(candidate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Derive a candidate gold fixture from recorded smoke data."
    )
    parser.add_argument("smoke_json", type=Path, help="path to a smoke fixture JSON")
    parser.add_argument(
        "--doc", type=int, required=True, dest="doc_id", help="doc_id to derive"
    )
    parser.add_argument(
        "--out", type=Path, required=True, dest="out_dir",
        help="output directory for the candidate file",
    )
    args = parser.parse_args()
    path = derive_candidates(args.smoke_json, args.doc_id, args.out_dir)
    print("wrote", path)


if __name__ == "__main__":  # pragma: no cover
    main()
