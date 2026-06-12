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
from ..refdata import METRICS

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

    if record.unit != meta["unit"]:
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


def sum_mismatch(
    records_for_agency_period: Iterable[MetricValueRecord], tolerance: float = 0.02
) -> list[str]:
    """Flag a cohort whose expense/subsidy figures fail internal reconciliation.

    Given the records for ONE agency in ONE period, two accounting identities
    are checked (each only when all of its parts are present in the cohort):

      * labour_cost + energy_fuel_cost + materials_services_cost == operating_expenses
      * total_operating_subsidy == operating_expenses - operating_revenue

    The tolerance is relative to operating_expenses (the anchor of both). Returns
    ``[sum_mismatch]`` if either identity fails, else ``[]`` -- the flag lands on
    the cohort, so it is reported once regardless of which identity broke.
    """
    by_code: dict[str, MetricValueRecord] = {
        r.metric_code: r for r in records_for_agency_period
    }
    expenses = by_code.get("operating_expenses")
    if expenses is None:
        # Both identities are anchored on operating_expenses; nothing to do.
        return []

    abs_tol = expenses.value.copy_abs() * Decimal(str(tolerance))

    # Identity 1: cost components sum to operating_expenses.
    components = ("labour_cost", "energy_fuel_cost", "materials_services_cost")
    if all(c in by_code for c in components):
        total = sum((by_code[c].value for c in components), Decimal(0))
        if (total - expenses.value).copy_abs() > abs_tol:
            return [SUM_MISMATCH]

    # Identity 2: subsidy == expenses - revenue.
    subsidy = by_code.get("total_operating_subsidy")
    revenue = by_code.get("operating_revenue")
    if subsidy is not None and revenue is not None:
        expected = expenses.value - revenue.value
        if (subsidy.value - expected).copy_abs() > abs_tol:
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
