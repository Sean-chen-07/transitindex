"""Proves the validation / flagging engine.

One focused positive + negative case per flag, including the 50% yoy boundary,
the crosscheck tolerance edge, unit mismatch (wrong unit and out-of-band
magnitude), and a reconciling vs non-reconciling expense set. Pure stdlib +
pytest; runs fully offline against the in-memory contract.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from transitindex_ingest.validation import flags
from transitindex_ingest.validation.flags import (
    CROSS_SOURCE_DISAGREEMENT,
    SUM_MISMATCH,
    UNIT_MISMATCH,
    YOY_SPIKE,
    sum_mismatch,
    validate,
    validate_cohort,
)


# --- yoy_spike ---------------------------------------------------------------


def test_yoy_spike_fires_above_threshold(make_record):
    rec = make_record(value=Decimal("160"))
    assert flags.yoy_spike(rec, Decimal("100")) == YOY_SPIKE  # +60% > 50%


def test_yoy_spike_silent_within_threshold(make_record):
    rec = make_record(value=Decimal("140"))
    assert flags.yoy_spike(rec, Decimal("100")) is None  # +40%


def test_yoy_spike_boundary_exactly_50pct_does_not_fire(make_record):
    rec = make_record(value=Decimal("150"))
    assert flags.yoy_spike(rec, Decimal("100")) is None  # exactly 50%, strict >


def test_yoy_spike_no_prior_is_silent(make_record):
    rec = make_record(value=Decimal("999999"))
    assert flags.yoy_spike(rec, None) is None


def test_yoy_spike_prior_zero_is_silent(make_record):
    rec = make_record(value=Decimal("5"))
    assert flags.yoy_spike(rec, Decimal("0")) is None  # no ratio against zero


# --- cross_source_disagreement -----------------------------------------------


def test_cross_source_disagreement_fires_beyond_tolerance(make_record):
    rec = make_record(value=Decimal("100"), crosscheck_value=Decimal("110"))
    assert flags.cross_source_disagreement(rec) == CROSS_SOURCE_DISAGREEMENT  # ~9% > 2%


def test_cross_source_disagreement_silent_within_tolerance(make_record):
    rec = make_record(value=Decimal("100"), crosscheck_value=Decimal("101"))
    assert flags.cross_source_disagreement(rec) is None  # 1% < 2%


def test_cross_source_disagreement_boundary_at_tolerance(make_record):
    # Exactly 2% gap -> not strictly greater -> no flag.
    rec = make_record(value=Decimal("102"), crosscheck_value=Decimal("100"))
    assert flags.cross_source_disagreement(rec, tolerance=0.02) is None


def test_cross_source_disagreement_no_crosscheck_is_silent(make_record):
    rec = make_record(crosscheck_value=None)
    assert flags.cross_source_disagreement(rec) is None


# --- unit_mismatch -----------------------------------------------------------


def test_unit_mismatch_fires_on_wrong_unit(make_record):
    # ridership expects unit "count"; record claims "%".
    rec = make_record(metric_code="ridership", unit="%", value=Decimal("100"))
    assert flags.unit_mismatch(rec) == UNIT_MISMATCH


def test_unit_mismatch_silent_on_correct_unit(make_record):
    rec = make_record(metric_code="ridership", unit="count", value=Decimal("100"))
    assert flags.unit_mismatch(rec) is None


def test_unit_mismatch_fires_on_percent_out_of_band(make_record):
    # on_time_performance is a "%" ratio metric; >1000 is impossible.
    rec = make_record(metric_code="on_time_performance", unit="%", value=Decimal("5000"))
    assert flags.unit_mismatch(rec) == UNIT_MISMATCH


def test_unit_mismatch_silent_on_plausible_percent(make_record):
    rec = make_record(metric_code="on_time_performance", unit="%", value=Decimal("92"))
    assert flags.unit_mismatch(rec) is None


def test_unit_mismatch_fires_on_negative_count(make_record):
    rec = make_record(metric_code="fleet_size", unit="count", value=Decimal("-3"))
    assert flags.unit_mismatch(rec) == UNIT_MISMATCH


def test_unit_mismatch_fires_on_tiny_currency(make_record):
    # total_assets is a "currency" metric; 39 CAD is garbage for agency finances.
    rec = make_record(metric_code="total_assets", unit="CAD", value=Decimal("39"))
    assert flags.unit_mismatch(rec) == UNIT_MISMATCH


def test_unit_mismatch_silent_on_plausible_currency(make_record):
    rec = make_record(metric_code="total_assets", unit="CAD", value=Decimal("39000000"))
    assert flags.unit_mismatch(rec) is None


def test_unit_mismatch_silent_on_small_count(make_record):
    # fleet_size is a count, not currency; a small value is fine.
    rec = make_record(metric_code="fleet_size", unit="count", value=Decimal("39"))
    assert flags.unit_mismatch(rec) is None


def test_unit_mismatch_silent_on_zero_currency(make_record):
    # A reported 0 currency value isn't the tiny-magnitude garbage we're catching.
    rec = make_record(metric_code="total_assets", unit="CAD", value=Decimal("0"))
    assert flags.unit_mismatch(rec) is None


# --- sum_mismatch (set-level) ------------------------------------------------


def _expense_cohort(make_record, labour, energy, materials, expenses,
                    revenue=None, subsidy=None):
    """Build a cohort of expense-family records for one agency+period."""
    common = dict(
        agency_slug="ttc",
        period_type="monthly",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        period_label="Mar 2026",
        service_scope="system_wide",
        quality="preliminary",
        unit="CAD",
        currency="CAD",
    )
    rows = [
        make_record(metric_code="labour_cost", value=Decimal(labour), **common),
        make_record(metric_code="energy_fuel_cost", value=Decimal(energy), **common),
        make_record(metric_code="materials_services_cost", value=Decimal(materials), **common),
        make_record(metric_code="operating_expenses", value=Decimal(expenses), **common),
    ]
    if revenue is not None:
        rows.append(make_record(metric_code="operating_revenue", value=Decimal(revenue), **common))
    if subsidy is not None:
        rows.append(
            make_record(metric_code="total_operating_subsidy", value=Decimal(subsidy), **common)
        )
    return rows


def test_sum_mismatch_silent_when_components_reconcile(make_record):
    cohort = _expense_cohort(make_record, labour="60", energy="20", materials="20", expenses="100")
    assert sum_mismatch(cohort) == []


def test_sum_mismatch_fires_when_components_disagree(make_record):
    # 60 + 20 + 30 = 110, but operating_expenses says 100 -> 10% off, > 2%.
    cohort = _expense_cohort(make_record, labour="60", energy="20", materials="30", expenses="100")
    assert sum_mismatch(cohort) == [SUM_MISMATCH]  # de-duped at cohort level


def test_sum_mismatch_silent_within_tolerance(make_record):
    # 60 + 20 + 21 = 101 vs 100 -> 1% off, within 2%.
    cohort = _expense_cohort(make_record, labour="60", energy="20", materials="21", expenses="100")
    assert sum_mismatch(cohort) == []


def test_sum_mismatch_fires_on_subsidy_identity(make_record):
    # expenses 100, revenue 30 -> expected subsidy 70; reported 90 -> off by 20%.
    cohort = _expense_cohort(
        make_record, labour="60", energy="20", materials="20", expenses="100",
        revenue="30", subsidy="90",
    )
    assert sum_mismatch(cohort) == [SUM_MISMATCH]


def test_sum_mismatch_silent_when_subsidy_reconciles(make_record):
    cohort = _expense_cohort(
        make_record, labour="60", energy="20", materials="20", expenses="100",
        revenue="30", subsidy="70",
    )
    assert sum_mismatch(cohort) == []


def test_sum_mismatch_needs_full_component_set(make_record):
    # Drop materials_services_cost -> identity 1 can't be checked, no flag.
    cohort = [
        r for r in _expense_cohort(
            make_record, labour="60", energy="20", materials="30", expenses="100"
        )
        if r.metric_code != "materials_services_cost"
    ]
    assert sum_mismatch(cohort) == []


def test_sum_mismatch_no_anchor_is_silent(make_record):
    # No operating_expenses row at all -> nothing to reconcile against.
    cohort = [
        make_record(metric_code="labour_cost", value=Decimal("60"), unit="CAD"),
        make_record(metric_code="energy_fuel_cost", value=Decimal("20"), unit="CAD"),
    ]
    assert sum_mismatch(cohort) == []


# --- composers ---------------------------------------------------------------


def test_validate_composes_and_dedups(make_record):
    # Wrong unit AND a big crosscheck gap -> both row-level flags, deduped order.
    rec = make_record(
        metric_code="ridership",
        unit="%",
        value=Decimal("200"),
        crosscheck_value=Decimal("100"),
    )
    result = validate(rec, prior_value=Decimal("100"))
    # 200 vs 100 prior is +100% (yoy), crosscheck 100% gap, and unit wrong.
    assert set(result) == {YOY_SPIKE, CROSS_SOURCE_DISAGREEMENT, UNIT_MISMATCH}
    assert len(result) == len(set(result))  # no duplicates


def test_validate_clean_record_has_no_flags(make_record):
    rec = make_record(
        metric_code="ridership",
        unit="count",
        value=Decimal("100"),
        crosscheck_value=Decimal("100"),
    )
    assert validate(rec, prior_value=Decimal("100")) == []


def test_validate_cohort_returns_deduped_sum_flag(make_record):
    cohort = _expense_cohort(make_record, labour="60", energy="20", materials="40", expenses="100")
    assert validate_cohort(cohort) == [SUM_MISMATCH]
