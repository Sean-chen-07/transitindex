"""Gold-fixture eval: the prompt/model regression guard (test requirement T1).

Drives a FakeLLMClient scenario through the real Tier 2 pipeline and scores it
against the hand-verified gold values in tests/fixtures/gold/. The headline
scenario is "mostly correct + one wrong-but-flagged value": it must keep
precision high (the clean values are right) while catching every should_flag
row (flag_recall == 1.0). A regression that silently returns a wrong figure
*clean* drops precision; one that stops flagging the ambiguous row drops
flag_recall. Pure stdlib + pytest, no API.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from transitindex_ingest.eval.gold import (
    ExtractedAssessment,
    load_gold,
    run_eval,
    run_eval_through_pipeline,
)
from transitindex_ingest.pdf.extract import pages_from_text
from transitindex_ingest.pdf.llm import ExtractedValue
from transitindex_ingest.pdf.pipeline import SourceRefMeta

GOLD_DIR = Path(__file__).parent / "fixtures" / "gold"
GOLD = load_gold(GOLD_DIR / "ttc_annual_2024.json")
PAGES = pages_from_text((GOLD_DIR / "ttc_annual_2024_pages.txt").read_text(encoding="utf-8").split("=== PAGE"))

META = SourceRefMeta(
    document_type="annual_report",
    title="TTC 2024 Annual Report",
    source_url="https://example.org/ttc-2024.pdf",
    publication_date=date(2025, 4, 1),
)


def _ev(metric_code, value, unit, confidence, *, note=None):
    """An annual-2024 ExtractedValue for the gold agency-year."""
    return ExtractedValue(
        metric_code=metric_code,
        value=Decimal(value),
        unit=unit,
        period_kind="annual",
        period_year=2024,
        page_number=2,
        confidence=Decimal(confidence),
        note=note,
    )


def _mostly_correct_scenario():
    """Seven correct, high-confidence values + one wrong-but-low-confidence.

    The wrong value is the should_flag gold row (on_time_performance), emitted
    below the 0.7 confidence threshold so the pipeline tags it 'low_confidence'
    -- exactly what a healthy extractor does with the report's "indicative
    only / subject to restatement" blended figure.
    """
    return [
        _ev("annual_ridership", "256900000", "count", "0.97"),
        _ev("operating_revenue", "1310000000", "CAD", "0.95"),
        _ev("operating_expenses", "2240000000", "CAD", "0.95"),
        _ev("revenue_service_hours", "9850000", "hours", "0.92"),
        _ev("fleet_size", "2510", "count", "0.93"),
        _ev("fleet_average_age", "11.2", "years", "0.9"),
        _ev("accessible_fleet_pct", "98.5", "%", "0.9"),
        # Wrong AND uncertain: the blended OTP figure the report flags itself.
        _ev("on_time_performance", "70.0", "%", "0.4", note="blended, indicative only"),
    ]


def test_gold_fixture_has_a_hard_flagged_row():
    """The fixture must include at least one should_flag row (the 'hard' case)."""
    assert any(g.should_flag for g in GOLD)


def test_mostly_correct_scenario_scores_above_threshold():
    report = run_eval_through_pipeline(
        GOLD,
        _mostly_correct_scenario(),
        "ttc",
        PAGES,
        source_ref_meta=META,
    )

    # The 7 clean values are all right -> precision well above the 0.8 floor.
    assert report.precision >= 0.8
    # Every should_flag row was flagged (here: via low_confidence).
    assert report.flag_recall == 1.0

    # The wrong value did NOT pollute precision: it was excluded as flagged.
    otp = next(r for r in report.rows if r.metric_code == "on_time_performance")
    assert otp.should_flag and otp.flagged and not otp.within_tolerance
    # ...and a clean row is scored as correct.
    ridership = next(r for r in report.rows if r.metric_code == "annual_ridership")
    assert ridership.matched and not ridership.flagged and ridership.within_tolerance


def test_hard_row_caught_via_validation_flag_not_just_low_confidence():
    """flag_recall counts a validation flag too, not only low_confidence.

    Here the hard row is returned with HIGH confidence but a validator raises a
    flag on it; the eval must still credit it as flagged.
    """
    scenario = _mostly_correct_scenario()[:-1] + [
        _ev("on_time_performance", "82.0", "%", "0.95"),  # high confidence, correct
    ]

    def validator(repo, record):
        # Stand in for the real cross-source check on the ambiguous OTP figure.
        return ["cross_source_disagreement"] if record.metric_code == "on_time_performance" else []

    report = run_eval_through_pipeline(
        GOLD, scenario, "ttc", PAGES, source_ref_meta=META, validator=validator
    )
    assert report.flag_recall == 1.0
    otp = next(r for r in report.rows if r.metric_code == "on_time_performance")
    assert otp.flagged and "cross_source_disagreement" in otp.flags


def test_regression_unflagged_wrong_value_is_penalized():
    """Guard behaviour: a wrong value returned CLEAN drops precision below 1.0.

    This is the failure mode the eval exists to catch -- a prompt/model change
    that confidently returns a bad figure.
    """
    report = run_eval(
        GOLD,
        [
            ExtractedAssessment("annual_ridership", Decimal("999999999")),  # clean + wrong
            ExtractedAssessment("operating_revenue", Decimal("1310000000")),  # clean + right
        ],
    )
    assert report.precision == 0.5  # one of two clean values is wrong


def test_regression_missed_flag_drops_recall():
    """A should_flag row returned clean (unflagged) drops flag_recall below 1.0."""
    report = run_eval(
        GOLD,
        [ExtractedAssessment("on_time_performance", Decimal("82.0"))],  # right but unflagged
    )
    assert report.flag_recall == 0.0


def test_empty_extraction_has_defined_scores():
    """No values returned: precision is vacuously 1.0, but flag_recall is 0.0."""
    report = run_eval(GOLD, [])
    assert report.precision == 1.0
    assert report.flag_recall == 0.0
    assert all(not r.matched for r in report.rows)
