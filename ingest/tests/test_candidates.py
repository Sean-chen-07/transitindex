"""Gold-candidate derivation guard (Plan A step 0.3).

`derive_candidates` distills the recorded smoke run into one candidate gold
record per metric for a single doc-year. These tests pin the contract the human
reviewer relies on: only annual figures for the doc's own year, exactly one row
per metric (the highest-confidence reading), canonical refdata units, and the
unmistakable CANDIDATE marker so an unconfirmed file can never be mistaken for
gold. Pure stdlib + pytest, no API, no PDF.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from transitindex_ingest.eval.candidates import derive_candidates
from transitindex_ingest.eval.gold import load_gold
from transitindex_ingest.refdata import METRICS

SMOKE = Path(__file__).parent / "fixtures" / "smoke" / "smoke10_2026-06-12.json"
DOC_ID = 59  # ttc 2019 annual_report


def _smoke_entry(doc_id: int) -> dict:
    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    return next(e for e in smoke if e["doc_id"] == doc_id)


def _candidate(tmp_path: Path, doc_id: int = DOC_ID) -> dict:
    out = derive_candidates(SMOKE, doc_id, tmp_path)
    return json.loads(out.read_text(encoding="utf-8"))


def test_only_doc_year_annual_rows(tmp_path):
    """Every record traces to an annual smoke value for the doc's own year."""
    entry = _smoke_entry(DOC_ID)
    year = entry["year"]
    # The (metric, value) pairs the smoke file actually offers for this doc-year.
    eligible = {
        (v["metric"], v["value"])
        for v in entry["values"]
        if v["period_kind"] == "annual" and v["year"] == year
    }
    cand = _candidate(tmp_path)
    assert cand["period_year"] == year
    assert cand["period_kind"] == "annual"
    assert cand["records"], "expected at least one candidate record"
    for rec in cand["records"]:
        assert (rec["metric_code"], rec["true_value"]) in eligible


def test_one_row_per_metric_highest_confidence(tmp_path):
    """No metric repeats, and each kept row is its metric's best annual reading."""
    entry = _smoke_entry(DOC_ID)
    year = entry["year"]
    cand = _candidate(tmp_path)

    codes = [rec["metric_code"] for rec in cand["records"]]
    assert len(codes) == len(set(codes)), "a metric appears more than once"

    # The kept confidence must be the max over that metric's doc-year readings.
    for rec in cand["records"]:
        confs = [
            Decimal(v["conf"])
            for v in entry["values"]
            if v["metric"] == rec["metric_code"]
            and v["period_kind"] == "annual"
            and v["year"] == year
        ]
        assert Decimal(rec["evidence"]["conf"]) == max(confs)


def test_canonical_units(tmp_path):
    """Units are the refdata canonical unit, never the smoke free-text label."""
    cand = _candidate(tmp_path)
    for rec in cand["records"]:
        assert rec["unit"] == METRICS[rec["metric_code"]]["unit"]


def test_candidate_marker_and_loadable(tmp_path):
    """The CANDIDATE marker is present and load_gold still parses the file."""
    out = derive_candidates(SMOKE, DOC_ID, tmp_path)
    cand = json.loads(out.read_text(encoding="utf-8"))
    assert cand["description"].startswith(
        "CANDIDATE — UNCONFIRMED, do not use in eval until moved to gold/"
    )
    for rec in cand["records"]:
        assert rec["tolerance"] == "0.005"
        assert rec["should_flag"] is False
        assert set(rec["evidence"]) == {"page", "conf", "quote", "note"}

    # load_gold ignores the extra `evidence` key and parses the gold shape.
    gold = load_gold(out)
    assert len(gold) == len(cand["records"])
    assert all(g.tolerance == Decimal("0.005") for g in gold)
