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

from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.eval.gold import (
    ExtractedAssessment,
    load_gold,
    run_eval,
    run_eval_through_pipeline,
)
from transitindex_ingest.pdf.extract import pages_from_text
from transitindex_ingest.pdf.llm import ExtractedValue, FakeLLMClient, _row_to_value
from transitindex_ingest.pdf.pipeline import SourceRefMeta, run_pdf
from transitindex_ingest.validation.flags import validate

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
        _ev("ridership", "256900000", "count", "0.97"),
        _ev("total_revenue_excluding_subsidy", "1310000000", "CAD", "0.95"),
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
    ridership = next(r for r in report.rows if r.metric_code == "ridership")
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
            ExtractedAssessment("ridership", Decimal("999999999")),  # clean + wrong
            ExtractedAssessment("total_revenue_excluding_subsidy", Decimal("1310000000")),  # clean + right
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


# --- should-flag traps: the wrong-number failure modes, end-to-end -----------
# Synthetic values throughout: these prove the flagging machinery catches the
# traps, not that the figures are real. (Re-seeding gold fixtures with verified
# published numbers is a separate data task.)


def _validator(priors=None):
    """The production-style validator: validation.flags.validate per record.

    `priors` (metric_code -> prior-year Decimal) stands in for the prior-year
    repo lookup that does not exist yet; production passes prior_value=None.
    """
    priors = priors or {}

    def _run(repo, record):
        return validate(record, prior_value=priors.get(record.metric_code))

    return _run


def test_thousandfold_value_vs_prior_year_earns_yoy_spike():
    """The in-thousands mistake: a figure 1000x last year's comes back flagged."""
    scenario = [_ev("total_revenue_excluding_subsidy", "1310000000000", "CAD", "0.95")]  # 1000x
    report = run_eval_through_pipeline(
        GOLD,
        scenario,
        "ttc",
        PAGES,
        source_ref_meta=META,
        validator=_validator(priors={"total_revenue_excluding_subsidy": Decimal("1310000000")}),
    )
    rev = next(r for r in report.rows if r.metric_code == "total_revenue_excluding_subsidy")
    assert rev.flagged and "yoy_spike" in rev.flags


def test_bracketed_negative_arrives_signed_and_lands_negative():
    """An accounting-bracketed figure reported as printed_sign='negative' must
    land negative in the staged row (code applies scale and sign, not the model)."""
    row = {
        "metric_code": "accumulated_surplus",
        "value": "1,234",
        "unit": "CAD",
        "period_kind": "annual",
        "period_year": 2024,
        "page_number": 4,
        "confidence": 0.9,
        "printed_scale": "thousands",
        "printed_sign": "negative",
    }
    ev = _row_to_value(row)
    assert ev.value == Decimal("-1234000")  # raw * 1000 * -1, applied in code

    repo = InMemoryRepository()
    (pid,) = run_pdf(
        repo,
        PAGES,
        "ttc",
        source_ref_meta=META,
        llm_client=FakeLLMClient([ev]),
        validator=_validator(),
    )
    assert repo.get_pending_value(pid).value == Decimal("-1234000")


def test_non_reconciling_expense_cohort_earns_sum_mismatch():
    """labour+energy+materials deliberately != operating_expenses -> the cohort
    earns sum_mismatch through run_pdf's own validate_cohort wiring."""
    scenario = [
        _ev("labour_cost", "60000000", "CAD", "0.95"),
        _ev("energy_fuel_cost", "20000000", "CAD", "0.95"),
        _ev("materials_services_cost", "50000000", "CAD", "0.95"),
        _ev("operating_expenses", "100000000", "CAD", "0.95"),  # parts sum to 130M
    ]
    report = run_eval_through_pipeline(
        GOLD, scenario, "ttc", PAGES, source_ref_meta=META, validator=_validator()
    )
    exp = next(r for r in report.rows if r.metric_code == "operating_expenses")
    assert exp.flagged and "sum_mismatch" in exp.flags


def test_broken_asset_split_identity_earns_sum_mismatch():
    """total_financial + total_non_financial deliberately != total_assets ->
    every record in the cohort carries sum_mismatch (the PSAB identity)."""
    scenario = [
        _ev("total_financial_assets", "60000000", "CAD", "0.95"),
        _ev("total_non_financial_assets", "20000000", "CAD", "0.95"),
        _ev("total_assets", "100000000", "CAD", "0.95"),  # split sums to 80M
    ]
    repo = InMemoryRepository()
    pending_ids = run_pdf(
        repo,
        PAGES,
        "ttc",
        source_ref_meta=META,
        llm_client=FakeLLMClient(scenario),
        validator=_validator(),
    )
    assert pending_ids
    for pid in pending_ids:
        assert "sum_mismatch" in repo.get_pending_value(pid).flags
