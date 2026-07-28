"""Validation checks that flag suspicious metric values.

Each check is a small pure function over `MetricValueRecord`s (plus whatever
context it needs) and returns flag strings drawn from the fixed vocabulary the
schema stores in `core.pending_values.flags` (text[]):

    yoy_spike, cross_source_disagreement, unit_mismatch, sum_mismatch

The row-level checks (`yoy_spike`, `cross_source_disagreement`,
`unit_mismatch`) return a single flag string or None; `validate` composes them.
`sum_mismatch` is inherently set-level (it reconciles several metrics within one
agency+period), so it takes a cohort and returns the flags it found.

All math is done in `Decimal` because record values are `Decimal`; thresholds
are converted through `str` to avoid binary-float drift.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Optional

from ..contract import MetricValueRecord
from ..refdata import ALL_AGENCIES, METRICS

# Flag vocabulary (mirrors the DOMAIN FACTS / db text[] values).
YOY_SPIKE = "yoy_spike"
CROSS_SOURCE_DISAGREEMENT = "cross_source_disagreement"
UNIT_MISMATCH = "unit_mismatch"
SUM_MISMATCH = "sum_mismatch"

# Thresholds.
_YOY_THRESHOLD = Decimal("0.50")  # |Δ| vs prior-year same period must EXCEED this
_PCT_SANITY_CEILING = Decimal("1000")  # a "%" ratio metric above this is implausible
_CURRENCY_FLOOR = Decimal("10000")  # a nonzero currency metric below this is implausible


def _rel_gap(a: Decimal, b: Decimal) -> Decimal:
    """Relative gap |a - b| / |b|. Caller guarantees b != 0."""
    return (a - b).copy_abs() / b.copy_abs()


def yoy_spike(record: MetricValueRecord, prior_value: Optional[Decimal]) -> Optional[str]:
    """Flag when the value swings >50% from the same period a year earlier.

    `prior_value` is the prior-year same-period value (the caller looks it up).
    Returns the flag only when there is a prior value, it is non-zero, and the
    relative change strictly exceeds 50%. Exactly 50% does NOT flag.
    """
    if prior_value is None:
        return None
    prior = Decimal(prior_value)
    if prior == 0:
        # No meaningful ratio against zero; nothing to compare.
        return None
    if _rel_gap(record.value, prior) > _YOY_THRESHOLD:
        return YOY_SPIKE
    return None


def cross_source_disagreement(
    record: MetricValueRecord, tolerance: float = 0.02
) -> Optional[str]:
    """Flag when the value and its crosscheck_value disagree beyond `tolerance`.

    Relative gap is measured against the crosscheck (the independent second
    source). No crosscheck -> nothing to compare. Exactly at tolerance does NOT
    flag; it must be strictly exceeded.
    """
    cross = record.crosscheck_value
    if cross is None:
        return None
    cross = Decimal(cross)
    if cross == 0:
        # Can't take a relative gap against zero; treat as not comparable.
        return None
    if _rel_gap(record.value, cross) > Decimal(str(tolerance)):
        return CROSS_SOURCE_DISAGREEMENT
    return None


def unit_mismatch(record: MetricValueRecord) -> Optional[str]:
    """Flag when the unit looks wrong for the metric.

    Three simple, documented heuristics:
      1. The recorded unit differs from the metric's expected unit
         (refdata.METRICS[code]['unit']).
      2. The magnitude is out of band for the unit_type:
           - a "%" ratio metric with value > 1000 (a true percentage can't),
           - a count metric with a negative value.
      3. A nonzero SOURCED "currency" metric whose magnitude is below
         _CURRENCY_FLOOR (e.g. total_assets=39) is implausible for agency-level
         finances. Derived per-unit currency metrics (average_fare, cost_per_hour,
         subsidy_per_rider, net_debt_per_capita) are legitimately small, so the
         floor is restricted to is_derived=False metrics.
    Unknown metric codes can't be checked here, so they pass.
    """
    meta = METRICS.get(record.metric_code)
    if meta is None:
        return None

    # Catalog units are CAD-denominated ("CAD", "CAD/hr"); the expected unit for
    # a currency metric follows the AGENCY's currency (USD for US agencies).
    expected_unit = meta["unit"]
    if meta["unit_type"] == "currency":
        agency_currency = ALL_AGENCIES.get(record.agency_slug, {}).get("currency", "CAD")
        expected_unit = expected_unit.replace("CAD", agency_currency)
    if record.unit != expected_unit:
        return UNIT_MISMATCH

    unit_type = meta["unit_type"]
    if meta["unit"] == "%" and unit_type == "ratio" and record.value > _PCT_SANITY_CEILING:
        return UNIT_MISMATCH
    if unit_type == "count" and record.value < 0:
        return UNIT_MISMATCH
    if (
        unit_type == "currency"
        and not meta["is_derived"]
        and record.value != 0
        and record.value.copy_abs() < _CURRENCY_FLOOR
    ):
        return UNIT_MISMATCH
    return None


# The subsidy identity (subsidy == operating_expenses - total_revenue_excluding_subsidy)
# is only exact when the annual result is ~0; a non-zero annual surplus/deficit
# (deferred capital contributions, gas-tax/carbon timing, one-time program funding)
# makes it an approximation. With annual_surplus_deficit available we prefer the
# honest bottom-line check (total_revenue - total_expenses == annual_surplus_deficit)
# and treat the subsidy gap-closure check as INFORMATIONAL only, at a widened
# tolerance, so a genuinely-correct statement is not flagged. (metric-set-build-plan
# Phase 5 item 2.)
_SUBSIDY_IDENTITY_TOLERANCE = Decimal("0.10")


def sum_mismatch(
    records_for_agency_period: Iterable[MetricValueRecord], tolerance: float = 0.02
) -> list[str]:
    """Flag a cohort whose expense/revenue/balance-sheet figures fail reconciliation.

    Given the records for ONE agency in ONE period, several accounting identities
    are checked (each only when all of its parts are present in the cohort):

    Income statement:
      * labour + energy + materials + amortization + other_operating_expenses
        == operating_expenses  (the PSAB 5-component basis)
      * total_revenue - total_expenses == annual_surplus_deficit  (honest bottom line)
      * subsidy == operating_expenses - total_revenue_excluding_subsidy
        (INFORMATIONAL: exact only when the annual result is ~0, so checked at a
        widened tolerance)

    Balance sheet (PSAB statement of financial position):
      * total_financial_assets + total_non_financial_assets == total_assets
      * accumulated_surplus == total_assets - total_liabilities
      * net_debt == total_liabilities - total_financial_assets

    Component + residual == total identities (income statement + balance
    sheet, addendum #2 -- same SumEquation shape as earned_revenue_components /
    financial_assets_components / liabilities_components /
    non_financial_assets_components in equations.py):
      * farebox_revenue + other_revenue == total_revenue_excluding_subsidy
      * cash_and_investments + other_financial_assets == total_financial_assets
      * long_term_debt + other_liabilities == total_liabilities
      * tangible_capital_assets + other_non_financial_assets == total_non_financial_assets
    Component bounds: farebox_revenue <= total_revenue_excluding_subsidy,
      cash_and_investments <= total_financial_assets,
      long_term_debt <= total_liabilities,
      tangible_capital_assets <= total_non_financial_assets

    Each identity's tolerance is relative to its anchor (the total it reconciles
    to). Returns ``[sum_mismatch]`` if any identity fails, else ``[]`` -- the flag
    lands on the cohort, so it is reported once regardless of which identity broke.
    """
    by_code: dict[str, MetricValueRecord] = {
        r.metric_code: r for r in records_for_agency_period
    }

    def _val(code: str) -> Optional[Decimal]:
        rec = by_code.get(code)
        return rec.value if rec is not None else None

    def _off(actual: Decimal, expected: Decimal, anchor: Decimal) -> bool:
        """True when |actual - expected| exceeds `tolerance` * |anchor|."""
        return (actual - expected).copy_abs() > anchor.copy_abs() * Decimal(str(tolerance))

    expenses = _val("operating_expenses")
    if expenses is not None:
        # Identity 1: the five expense components sum to operating_expenses (PSAB basis).
        components = (
            "labour_cost", "energy_fuel_cost", "materials_services_cost",
            "amortization", "other_operating_expenses",
        )
        if all(c in by_code for c in components):
            total = sum((by_code[c].value for c in components), Decimal(0))
            if _off(total, expenses, expenses):
                return [SUM_MISMATCH]

        # Identity 2 (INFORMATIONAL): subsidy == expenses - revenue, at a widened
        # tolerance since it holds exactly only when the annual result is ~0.
        subsidy = _val("subsidy")
        revenue = _val("total_revenue_excluding_subsidy")
        if subsidy is not None and revenue is not None:
            expected = expenses - revenue
            if (subsidy - expected).copy_abs() > expenses.copy_abs() * _SUBSIDY_IDENTITY_TOLERANCE:
                return [SUM_MISMATCH]

    # Identity 3: honest bottom line -- total_revenue - total_expenses == annual_surplus_deficit.
    total_revenue = _val("total_revenue")
    total_expenses = _val("total_expenses")
    surplus_deficit = _val("annual_surplus_deficit")
    if total_revenue is not None and total_expenses is not None and surplus_deficit is not None:
        if _off(surplus_deficit, total_revenue - total_expenses, total_revenue):
            return [SUM_MISMATCH]

    assets = _val("total_assets")
    if assets is not None:
        # Identity 4 (PSAB): financial + non-financial assets == total assets.
        financial = _val("total_financial_assets")
        non_financial = _val("total_non_financial_assets")
        if financial is not None and non_financial is not None:
            if _off(financial + non_financial, assets, assets):
                return [SUM_MISMATCH]

        # Identity 5 (PSAB): accumulated surplus == assets - liabilities.
        surplus = _val("accumulated_surplus")
        liabilities = _val("total_liabilities")
        if surplus is not None and liabilities is not None:
            if _off(surplus, assets - liabilities, assets):
                return [SUM_MISMATCH]

    # Identity 6 (PSAB net-debt model): net_debt == total_liabilities - total_financial_assets.
    net_debt = _val("net_debt")
    liabilities = _val("total_liabilities")
    financial = _val("total_financial_assets")
    if net_debt is not None and liabilities is not None and financial is not None:
        if _off(net_debt, liabilities - financial, liabilities):
            return [SUM_MISMATCH]

    # Component + residual == total identities (income statement + balance
    # sheet, addendum #2) + bounds. Each fires only when all its terms are
    # present, matching the expense-components behaviour; a residual solving
    # negative IS the bound violation, so the equality subsumes the bound
    # where both sides are sourced.
    _component_families = (
        ("total_revenue_excluding_subsidy", "farebox_revenue", "other_revenue"),
        ("total_financial_assets", "cash_and_investments", "other_financial_assets"),
        ("total_liabilities", "long_term_debt", "other_liabilities"),
        ("total_non_financial_assets", "tangible_capital_assets", "other_non_financial_assets"),
    )
    for total_code, part_code, residual_code in _component_families:
        total = _val(total_code)
        part = _val(part_code)
        residual = _val(residual_code)
        # Component identity: part + residual == total (all three present).
        if total is not None and part is not None and residual is not None:
            if _off(part + residual, total, total):
                return [SUM_MISMATCH]
        # Component bound: the sourced part must not exceed its total.
        if total is not None and part is not None and part > total:
            return [SUM_MISMATCH]

    return []


def validate(
    record: MetricValueRecord,
    *,
    prior_value: Optional[Decimal] = None,
    cohort: Optional[Iterable[MetricValueRecord]] = None,
) -> list[str]:
    """Run the row-level checks for one record; return de-duplicated flags.

    `prior_value` feeds yoy_spike. `cohort` is accepted for a future set-aware
    caller but the set-level reconciliation lives in `validate_cohort`; passing
    it here has no effect beyond documenting intent.
    """
    candidates = [
        yoy_spike(record, prior_value),
        cross_source_disagreement(record),
        unit_mismatch(record),
    ]
    return _dedup(f for f in candidates if f is not None)


def validate_cohort(records: Iterable[MetricValueRecord]) -> list[str]:
    """Set-level validation for one agency+period: the sum_mismatch identities.

    Returns de-duplicated flags for the cohort as a whole. (Row-level flags come
    from `validate` per record; this layer only adds reconciliation flags.)
    """
    records = list(records)
    return _dedup(sum_mismatch(records))


def _dedup(flags: Iterable[str]) -> list[str]:
    """Order-preserving de-duplication."""
    return list(dict.fromkeys(flags))
