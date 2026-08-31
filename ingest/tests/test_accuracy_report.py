"""Offline accuracy report + gold-index loading (Phase 3 "measuring stick").

Two guards:

  * `load_gold_index` sees only CONFIRMED real-document fixtures -- the promoted
    ones at the top level of tests/fixtures/gold/, never the invented
    `synthetic/` scenarios and never the unconfirmed `candidates/`. A synthetic
    scenario scored against a real document is exactly the false measurement
    this phase exists to remove.
  * `accuracy_report` arithmetic on a tiny hand-built input: flag derivation,
    counts, review rate, and precision / flag_recall against a gold fixture.

Pure stdlib + pytest, no API, no PDF.
"""

from __future__ import annotations

import json
from pathlib import Path

from transitindex_ingest.eval.accuracy_report import (
    accuracy_report,
    format_report,
    value_flags,
)
from transitindex_ingest.eval.smoke import load_gold_index

GOLD_DIR = Path(__file__).parent / "fixtures" / "gold"


# --- gold index -------------------------------------------------------------


def test_index_holds_the_promoted_real_document_fixtures():
    index = load_gold_index(GOLD_DIR)
    assert index[("ttc", 2019)].name == "ttc_annual_2019.json"
    assert index[("calgary-transit", 2019)].name == "calgary-transit_annual_2019.json"


def test_index_excludes_synthetic_and_candidate_fixtures():
    """The 2024 scenarios are invented; the 2019 candidates are unconfirmed."""
    index = load_gold_index(GOLD_DIR)
    assert ("ttc", 2024) not in index
    assert ("translink", 2024) not in index
    assert ("edmonton-ets", 2019) not in index  # candidate only: nothing promoted
    names = {p.name for p in index.values()}
    assert not any("doc" in n for n in names)  # candidate files carry a _docNN suffix


def test_index_skips_a_synthetic_marked_file_even_at_top_level(tmp_path):
    """`synthetic: true` wins wherever the file sits."""
    (tmp_path / "ttc_annual_2024.json").write_text(json.dumps({
        "agency_slug": "ttc", "period_year": 2024, "period_kind": "annual",
        "synthetic": True, "records": [],
    }), encoding="utf-8")
    (tmp_path / "ttc_annual_2019.json").write_text(json.dumps({
        "agency_slug": "ttc", "period_year": 2019, "period_kind": "annual",
        "records": [],
    }), encoding="utf-8")

    index = load_gold_index(tmp_path)
    assert set(index) == {("ttc", 2019)}


def test_every_promoted_row_keeps_its_candidate_evidence():
    """A promoted row is the candidate row verbatim -- no invented values."""
    for name, candidate in (
        ("ttc_annual_2019.json", "candidates/ttc_annual_2019_doc59.json"),
        ("calgary-transit_annual_2019.json", "candidates/calgary-transit_annual_2019_doc13.json"),
    ):
        promoted = json.loads((GOLD_DIR / name).read_text(encoding="utf-8"))
        cand = json.loads((GOLD_DIR / candidate).read_text(encoding="utf-8"))
        cand_rows = {r["metric_code"]: r for r in cand["records"]}
        assert promoted["records"], name
        for row in promoted["records"]:
            assert row == cand_rows[row["metric_code"]]


# --- flags ------------------------------------------------------------------


def _value(metric, value, conf, *, quote=None, note=None, year=2019, **kw):
    return {
        "metric": metric, "value": value, "conf": conf, "quote": quote,
        "note": note, "year": year, "period_kind": "annual", **kw,
    }


def test_value_flags_reads_confidence_conflict_and_quote():
    clean = _value("ridership", "100", "0.9", quote="Trips 100")
    assert value_flags(clean) == ()

    lowconf = _value("ridership", "100", "0.6", quote="Trips 100")
    assert value_flags(lowconf) == ("low_confidence",)

    conflict = _value(
        "ridership", "100", "0.5", quote="Trips 100",
        note="⚠ chunks disagree — 100, 200 (reviewer confirm)",
    )
    assert value_flags(conflict) == ("low_confidence", "review_confidence", "conflict")

    assert "quote_missing" in value_flags(_value("ridership", "100", "0.9"))
    assert "quote_mismatch" in value_flags(
        _value("ridership", "100", "0.9", quote="Trips 250")
    )


def test_a_decimal_printed_figure_is_not_a_false_mismatch():
    """525.5 under a millions header scales to 525,500,000 -- the quote supports it."""
    scaled = _value("ridership", "525500000.0", "0.9",
                    quote="Revenue Passenger Trips (Millions) 525.5")
    assert "quote_mismatch" not in value_flags(scaled)


def test_value_flags_keeps_explicit_staged_flags():
    staged = _value("ridership", "100", "0.9", quote="Trips 100", flags=["yoy_spike"])
    assert value_flags(staged) == ("yoy_spike",)


# --- report math ------------------------------------------------------------


def _tiny_docs():
    """One doc, four values: one clean, one low-confidence, one conflict, one
    quote mismatch (also low-confidence)."""
    return [{
        "doc_id": 1, "slug": "ttc", "year": 2019,
        "values": [
            _value("ridership", "100", "0.9", quote="Trips 100"),
            _value("fleet_size", "50", "0.6", quote="Fleet 50"),
            _value(
                "labour_cost", "700", "0.5", quote="Wages 700",
                note="⚠ chunks disagree — 700, 800 (reviewer confirm)",
            ),
            _value("operating_expenses", "900", "0.6", quote="Expenses 250"),
        ],
    }]


def test_totals_count_flags_and_review_rate():
    report = accuracy_report(_tiny_docs(), gold_dir=None)
    t = report["totals"]

    assert t["docs"] == 1
    assert t["values"] == 4
    assert t["flagged"] == 3  # the clean row is the only unflagged one
    assert t["low_confidence"] == 3
    assert t["review_rate"] == 0.75
    assert t["flags"]["conflict"] == 1
    assert t["flags"]["review_confidence"] == 1
    assert t["flags"]["quote_mismatch"] == 1
    assert t["flags"]["quote_missing"] == 0
    assert report["gold"] == []


def test_per_doc_summary_mirrors_the_totals():
    report = accuracy_report(_tiny_docs(), gold_dir=None)
    (doc,) = report["docs"]
    assert (doc["doc_id"], doc["slug"], doc["year"]) == (1, "ttc", 2019)
    assert (doc["values"], doc["flagged"], doc["review_rate"]) == (4, 3, 0.75)


def test_empty_input_does_not_divide_by_zero():
    report = accuracy_report([], gold_dir=None)
    assert report["totals"] == {
        "docs": 0, "values": 0, "flagged": 0, "low_confidence": 0,
        "review_rate": 0.0,
        "flags": {
            "low_confidence": 0, "review_confidence": 0, "conflict": 0,
            "quote_missing": 0, "quote_mismatch": 0,
        },
    }
    assert "no confirmed fixture matched" in format_report(report)


def _gold_dir(tmp_path):
    """Gold for ttc 2019: one row the tiny doc gets right, one it gets wrong
    (but flags), one it never returns."""
    (tmp_path / "ttc_annual_2019.json").write_text(json.dumps({
        "agency_slug": "ttc", "period_year": 2019, "period_kind": "annual",
        "records": [
            {"metric_code": "ridership", "true_value": "100", "unit": "count",
             "tolerance": "0.01", "should_flag": False},
            {"metric_code": "operating_expenses", "true_value": "250", "unit": "CAD",
             "tolerance": "0.01", "should_flag": True},
            {"metric_code": "subsidy", "true_value": "42", "unit": "CAD",
             "tolerance": "0.01", "should_flag": False},
        ],
    }), encoding="utf-8")
    return tmp_path


def test_gold_scoring_of_a_matching_doc(tmp_path):
    report = accuracy_report(_tiny_docs(), gold_dir=_gold_dir(tmp_path))
    (g,) = report["gold"]

    assert g["fixture"] == "ttc_annual_2019.json"
    assert g["gold_rows"] == 3
    assert g["matched"] == 2  # subsidy was never returned
    # Clean pool is ridership alone: operating_expenses came back low-confidence.
    assert g["clean_count"] == 1
    assert g["precision"] == 1.0
    # The one should_flag row was flagged.
    assert g["flag_recall"] == 1.0
    assert "precision 1.00" in format_report(report)


def test_gold_scoring_catches_a_wrong_clean_value(tmp_path):
    docs = _tiny_docs()
    docs[0]["values"][0] = _value("ridership", "999", "0.9", quote="Trips 999")

    report = accuracy_report(docs, gold_dir=_gold_dir(tmp_path))
    (g,) = report["gold"]
    assert g["clean_count"] == 1
    assert g["precision"] == 0.0


def test_gold_scoring_skips_a_doc_with_no_fixture(tmp_path):
    docs = _tiny_docs()
    docs[0]["slug"] = "miway"
    assert accuracy_report(docs, gold_dir=_gold_dir(tmp_path))["gold"] == []


def test_gold_scoring_ignores_other_years_and_non_total_scope(tmp_path):
    docs = _tiny_docs()
    docs[0]["values"][0]["year"] = 2018
    docs[0]["values"][3]["scope"] = "bus"

    report = accuracy_report(docs, gold_dir=_gold_dir(tmp_path))
    (g,) = report["gold"]
    assert g["matched"] == 0
