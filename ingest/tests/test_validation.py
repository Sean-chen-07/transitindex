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
    cohorts,
    sum_mismatch,
    sum_mismatch_records,
    validate,
    validate_cohort,
    validate_cohort_records,
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
                    amortization="0", other="0", revenue=None, subsidy=None):
    """Build a cohort of expense-family records for one agency+period.

    The PSAB expense identity is 5-term (labour + energy + materials +
    amortization + other_operating_expenses == operating_expenses); all five are
    included so the identity can be exercised (amortization/other default to 0).
    """
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
        make_record(metric_code="amortization", value=Decimal(amortization), **common),
        make_record(metric_code="other_operating_expenses", value=Decimal(other), **common),
        make_record(metric_code="operating_expenses", value=Decimal(expenses), **common),
    ]
    if revenue is not None:
        rows.append(make_record(metric_code="total_revenue_excluding_subsidy", value=Decimal(revenue), **common))
    if subsidy is not None:
        rows.append(
            make_record(metric_code="subsidy", value=Decimal(subsidy), **common)
        )
    return rows


def test_sum_mismatch_silent_when_components_reconcile(make_record):
    # 60 + 20 + 10 + 8 + 2 = 100 == operating_expenses.
    cohort = _expense_cohort(
        make_record, labour="60", energy="20", materials="10",
        amortization="8", other="2", expenses="100",
    )
    assert sum_mismatch(cohort) == []


def test_sum_mismatch_fires_when_components_disagree(make_record):
    # 60 + 20 + 30 + 0 + 0 = 110, but operating_expenses says 100 -> 10% off, > 2%.
    cohort = _expense_cohort(make_record, labour="60", energy="20", materials="30", expenses="100")
    assert sum_mismatch(cohort) == [SUM_MISMATCH]  # de-duped at cohort level


def test_sum_mismatch_silent_within_tolerance(make_record):
    # 60 + 20 + 10 + 8 + 3 = 101 vs 100 -> 1% off, within 2%.
    cohort = _expense_cohort(
        make_record, labour="60", energy="20", materials="10",
        amortization="8", other="3", expenses="100",
    )
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


# --- sum_mismatch: PSAB balance-sheet identities -----------------------------


def _balance_sheet_cohort(make_record, financial, non_financial, assets,
                          surplus=None, liabilities=None):
    """Build a cohort of statement-of-financial-position records (one agency+period).

    Anchored on total_assets. Identity 3: financial + non_financial == assets.
    Identity 4 (when surplus + liabilities given): surplus == assets - liabilities.
    """
    common = dict(
        agency_slug="ttc",
        period_type="annual_calendar",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        period_label="2024",
        service_scope="system_wide",
        quality="preliminary",
        unit="CAD",
        currency="CAD",
    )
    rows = [
        make_record(metric_code="total_financial_assets", value=Decimal(financial), **common),
        make_record(metric_code="total_non_financial_assets", value=Decimal(non_financial), **common),
        make_record(metric_code="total_assets", value=Decimal(assets), **common),
    ]
    if liabilities is not None:
        rows.append(make_record(metric_code="total_liabilities", value=Decimal(liabilities), **common))
    if surplus is not None:
        rows.append(make_record(metric_code="accumulated_surplus", value=Decimal(surplus), **common))
    return rows


def test_sum_mismatch_silent_when_asset_split_reconciles(make_record):
    # Identity 3: 40 + 60 = 100 == total_assets.
    cohort = _balance_sheet_cohort(make_record, financial="40", non_financial="60", assets="100")
    assert sum_mismatch(cohort) == []


def test_sum_mismatch_fires_on_broken_asset_split(make_record):
    # Identity 3: 40 + 50 = 90, but total_assets says 100 -> 10% off, > 2%.
    cohort = _balance_sheet_cohort(make_record, financial="40", non_financial="50", assets="100")
    assert sum_mismatch(cohort) == [SUM_MISMATCH]


def test_sum_mismatch_fires_on_broken_accumulated_surplus(make_record):
    # Identity 4: assets 100 - liabilities 30 = expected surplus 70; reported 90 -> 20% off.
    cohort = _balance_sheet_cohort(
        make_record, financial="40", non_financial="60", assets="100",
        liabilities="30", surplus="90",
    )
    assert sum_mismatch(cohort) == [SUM_MISMATCH]


def test_sum_mismatch_silent_when_accumulated_surplus_reconciles(make_record):
    # Identity 4: assets 100 - liabilities 30 = surplus 70, exact.
    cohort = _balance_sheet_cohort(
        make_record, financial="40", non_financial="60", assets="100",
        liabilities="30", surplus="70",
    )
    assert sum_mismatch(cohort) == []


def test_sum_mismatch_no_assets_anchor_is_silent(make_record):
    # No total_assets row -> neither PSAB identity can be checked.
    cohort = [
        make_record(metric_code="total_financial_assets", value=Decimal("40"), unit="CAD"),
        make_record(metric_code="total_non_financial_assets", value=Decimal("60"), unit="CAD"),
    ]
    assert sum_mismatch(cohort) == []


# --- sum_mismatch: Phase 5 additions (honest surplus, net-debt, components) ---


def _bs_record(make_record, code, value):
    return make_record(
        metric_code=code,
        value=Decimal(value),
        agency_slug="ttc",
        period_type="annual_calendar",
        period_start=date(2024, 1, 1),
        period_end=date(2024, 12, 31),
        period_label="2024",
        service_scope="total",
        quality="preliminary",
        unit="CAD",
        currency="CAD",
    )


def test_honest_surplus_identity_fires_when_broken(make_record):
    # total_revenue 100 - total_expenses 90 = 10, but reported surplus is 30 -> off.
    cohort = [
        _bs_record(make_record, "total_revenue", "100"),
        _bs_record(make_record, "total_expenses", "90"),
        _bs_record(make_record, "annual_surplus_deficit", "30"),
    ]
    assert sum_mismatch(cohort) == [SUM_MISMATCH]


def test_honest_surplus_identity_silent_when_reconciles(make_record):
    # 100 - 90 = 10 == reported surplus 10.
    cohort = [
        _bs_record(make_record, "total_revenue", "100"),
        _bs_record(make_record, "total_expenses", "90"),
        _bs_record(make_record, "annual_surplus_deficit", "10"),
    ]
    assert sum_mismatch(cohort) == []


def test_honest_surplus_identity_handles_deficit(make_record):
    # A negative annual result (deficit) reconciles exactly: 90 - 100 = -10.
    cohort = [
        _bs_record(make_record, "total_revenue", "90"),
        _bs_record(make_record, "total_expenses", "100"),
        _bs_record(make_record, "annual_surplus_deficit", "-10"),
    ]
    assert sum_mismatch(cohort) == []


def test_subsidy_identity_is_informational_widened(make_record):
    # expenses 100, revenue 30 -> expected subsidy 70. A 5% gap (subsidy 73.5) is
    # within the widened 10% subsidy tolerance -> no flag (the annual result absorbs it).
    cohort = _expense_cohort(
        make_record, labour="60", energy="20", materials="20", expenses="100",
        revenue="30", subsidy="73.5",
    )
    assert sum_mismatch(cohort) == []


def test_subsidy_identity_still_fires_beyond_widened_tolerance(make_record):
    # A 20% gap (subsidy 90 vs expected 70) exceeds even the widened 10% tolerance.
    cohort = _expense_cohort(
        make_record, labour="60", energy="20", materials="20", expenses="100",
        revenue="30", subsidy="90",
    )
    assert sum_mismatch(cohort) == [SUM_MISMATCH]


def test_net_debt_identity_fires_when_broken(make_record):
    # net_debt should be liabilities 300 - financial 100 = 200; reported 250 -> off.
    cohort = [
        _bs_record(make_record, "total_liabilities", "300"),
        _bs_record(make_record, "total_financial_assets", "100"),
        _bs_record(make_record, "net_debt", "250"),
    ]
    assert sum_mismatch(cohort) == [SUM_MISMATCH]


def test_net_debt_identity_silent_when_reconciles(make_record):
    cohort = [
        _bs_record(make_record, "total_liabilities", "300"),
        _bs_record(make_record, "total_financial_assets", "100"),
        _bs_record(make_record, "net_debt", "200"),
    ]
    assert sum_mismatch(cohort) == []


def test_component_identity_fires_when_broken(make_record):
    # cash 40 + other 40 = 80, but total_financial_assets says 100 -> 20% off.
    cohort = [
        _bs_record(make_record, "total_financial_assets", "100"),
        _bs_record(make_record, "cash_and_investments", "40"),
        _bs_record(make_record, "other_financial_assets", "40"),
    ]
    assert sum_mismatch(cohort) == [SUM_MISMATCH]


def test_component_identity_silent_when_reconciles(make_record):
    # long_term_debt 70 + other_liabilities 30 = 100 == total_liabilities.
    cohort = [
        _bs_record(make_record, "total_liabilities", "100"),
        _bs_record(make_record, "long_term_debt", "70"),
        _bs_record(make_record, "other_liabilities", "30"),
    ]
    assert sum_mismatch(cohort) == []


def test_component_bound_fires_when_part_exceeds_total(make_record):
    # tangible_capital_assets 120 > total_non_financial_assets 100 -> impossible.
    cohort = [
        _bs_record(make_record, "total_non_financial_assets", "100"),
        _bs_record(make_record, "tangible_capital_assets", "120"),
    ]
    assert sum_mismatch(cohort) == [SUM_MISMATCH]


def test_component_bound_silent_when_part_within_total(make_record):
    cohort = [
        _bs_record(make_record, "total_non_financial_assets", "100"),
        _bs_record(make_record, "tangible_capital_assets", "80"),
    ]
    assert sum_mismatch(cohort) == []


def test_earned_revenue_components_fires_when_broken(make_record):
    # farebox 40 + other 40 = 80, but total_revenue_excluding_subsidy says 100 -> 20% off.
    cohort = [
        _bs_record(make_record, "total_revenue_excluding_subsidy", "100"),
        _bs_record(make_record, "farebox_revenue", "40"),
        _bs_record(make_record, "other_revenue", "40"),
    ]
    assert sum_mismatch(cohort) == [SUM_MISMATCH]


def test_earned_revenue_components_silent_when_reconciles(make_record):
    # farebox 70 + other 30 = 100 == total_revenue_excluding_subsidy.
    cohort = [
        _bs_record(make_record, "total_revenue_excluding_subsidy", "100"),
        _bs_record(make_record, "farebox_revenue", "70"),
        _bs_record(make_record, "other_revenue", "30"),
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


# --- scope-aware cohorts + row-scoped sum_mismatch ---------------------------


def _bs_row(make_record, code, value, **overrides):
    """One balance-sheet record for the shared agency+period."""
    fields = dict(
        agency_slug="ttc",
        period_type="monthly",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        period_label="Mar 2026",
        service_scope="total",
        quality="preliminary",
        unit="CAD",
        currency="CAD",
    )
    fields.update(overrides)
    return make_record(metric_code=code, value=Decimal(value), **fields)


def test_cohorts_split_by_service_scope(make_record):
    rows = [
        _bs_row(make_record, "total_assets", "100", service_scope="total"),
        _bs_row(make_record, "total_assets", "40", service_scope="conventional"),
    ]
    got = cohorts(rows)
    assert len(got) == 2
    assert sorted(c["total_assets"].value for c in got) == [Decimal("40"), Decimal("100")]


def test_cohorts_split_expense_lines_by_cost_basis(make_record):
    """A psab_total expense total and an operating one are different cohorts, but
    the non-expense records (whose cost_basis is meaningless) join both."""
    rows = [
        _bs_row(make_record, "operating_expenses", "130", cost_basis="psab_total"),
        _bs_row(make_record, "operating_expenses", "100", cost_basis="operating"),
        _bs_row(make_record, "total_assets", "999"),
    ]
    got = cohorts(rows)
    assert len(got) == 2
    assert sorted(c["operating_expenses"].value for c in got) == [Decimal("100"), Decimal("130")]
    assert all(c["total_assets"].value == Decimal("999") for c in got)


def test_mixed_cost_basis_no_longer_corrupts_the_expense_identity(make_record):
    """The 5 components reconcile to the OPERATING total (100). A psab_total
    reading of 130 for the same period used to win last-write-wins and break the
    identity; now each basis reconciles inside its own cohort."""
    rows = _expense_cohort(
        make_record, labour="60", energy="20", materials="10",
        amortization="8", other="2", expenses="100",
    ) + [
        _bs_row(
            make_record, "operating_expenses", "130",
            service_scope="system_wide", cost_basis="psab_total",
        )
    ]
    assert sum_mismatch(rows) == []


def test_mixed_service_scope_no_longer_corrupts_the_asset_identity(make_record):
    """A 'total' split that closes plus an unrelated 'conventional' total_assets."""
    rows = [
        _bs_row(make_record, "total_assets", "100"),
        _bs_row(make_record, "total_financial_assets", "60"),
        _bs_row(make_record, "total_non_financial_assets", "40"),
        _bs_row(make_record, "total_assets", "7", service_scope="conventional"),
    ]
    assert sum_mismatch(rows) == []


def test_sum_mismatch_records_names_only_the_participating_rows(make_record):
    """A broken asset split must not stamp the period's ridership row."""
    ridership = _bs_row(make_record, "ridership", "500", unit="count", currency=None)
    rows = [
        _bs_row(make_record, "total_assets", "100"),
        _bs_row(make_record, "total_financial_assets", "60"),
        _bs_row(make_record, "total_non_financial_assets", "20"),  # split sums to 80
        ridership,
    ]
    offenders = sum_mismatch_records(rows)
    assert {r.metric_code for r in offenders} == {
        "total_assets", "total_financial_assets", "total_non_financial_assets"
    }
    assert all(r is not ridership for r in offenders)
    assert sum_mismatch(rows) == [SUM_MISMATCH]  # the cohort-level view is unchanged


def test_validate_cohort_records_keys_only_the_offenders(make_record):
    ridership = _bs_row(make_record, "ridership", "500", unit="count", currency=None)
    assets = _bs_row(make_record, "total_assets", "100")
    rows = [
        assets,
        _bs_row(make_record, "total_financial_assets", "60"),
        _bs_row(make_record, "total_non_financial_assets", "20"),
        ridership,
    ]
    by_row = validate_cohort_records(rows)
    assert by_row[id(assets)] == [SUM_MISMATCH]
    assert id(ridership) not in by_row
