"""Roll a monthly metric up to an annual (or partial year-to-date) value.

Reads an agency's current MONTHLY values for one metric spanning its fiscal
year, sums the contiguous run from the start of the year (`periods.roll_up`),
and writes the result as a DERIVED value via `repo.insert_derived_value` with the
summed monthly rows as provenance (equation_code = `period_rollup`). A complete
year becomes an annual period (comparable_flag=True); an incomplete year becomes
a partial `ytd` period that never ranks against full years (comparable_flag=False).
One rollup per (mode_id, service_scope) partition.

This runs BEFORE the within-period equation solver for the annual period: once
the annual ridership/revenue exists, `recompute_derived` can derive average_fare,
cost_per_rider, etc. for that year.

`ridership` and `operating_revenue` are the two monthly-native feeds (StatCan
23-10-0307 publishes both); `rollup_metric` is parameterized by metric so both
fold up identically. `rollup_ridership` is the thin back-compat wrapper.
"""

from __future__ import annotations

from typing import NamedTuple

from ..equations import PERIOD_ROLLUP, SUM_MISMATCH
from ..periods import (
    fiscal_year_months,
    monthly_period,
    plan_calendar_rollups,
    quarterly_period,
    roll_up,
)
from ..equations import _close  # tolerance shared with the solver's cross-check
from ..refdata import METRICS
from .derived_recompute import weakest_quality

from decimal import Decimal


class RollupWritten(NamedTuple):
    """What a rollup wrote: the derived value ids and the period ids they landed in."""

    value_ids: list[int]
    period_ids: list[int]


def rollup_metric(repo, agency_slug: str, year: int, metric_code: str) -> RollupWritten:
    """Roll the agency's monthly `metric_code` up to `year`. Returns ids written."""
    meta = METRICS[metric_code]
    unit = meta["unit"]
    currency = "CAD" if meta["unit_type"] == "currency" else None

    agency_id = repo.agency_id(agency_slug)
    metric_id = repo.metric_id(metric_code)
    months = fiscal_year_months(agency_slug, year)

    # Locate the reporting_period for each composing month (if it exists).
    period_by_dates = {
        (p.start_date, p.end_date): p
        for p in repo.list_reporting_periods()
        if p.period_type == "monthly"
    }

    # Gather current monthly values per (mode_id, service_scope) partition.
    partitions: dict[tuple, dict[tuple[int, int], object]] = {}
    for (cy, cm) in months:
        mp = monthly_period(cy, cm)
        period = period_by_dates.get((mp.start, mp.end))
        if period is None:
            continue
        for v in repo.list_current_values_for_agency_period(agency_id, period.id):
            if v.metric_id != metric_id:
                continue
            partitions.setdefault((v.mode_id, v.service_scope), {})[(cy, cm)] = v

    value_ids: list[int] = []
    period_ids: list[int] = []
    for (mode_id, scope), mvs in partitions.items():
        result = roll_up(agency_slug, year, {cal: mv.value for cal, mv in mvs.items()})
        if result is None:
            continue
        summed = [mvs[months[i - 1]] for i in result.month_indices]
        period_id = repo.get_or_create_reporting_period(
            result.period.period_type,
            result.period.start,
            result.period.end,
            result.period.label,
        )
        vid = repo.insert_derived_value(
            agency_id=agency_id,
            metric_id=metric_id,
            reporting_period_id=period_id,
            mode_id=mode_id,
            service_scope=scope,
            value=result.value,
            unit=unit,
            quality=weakest_quality([mv.quality for mv in summed]),
            equation_code=PERIOD_ROLLUP,
            input_value_ids=[mv.id for mv in summed],
            currency=currency,
            # A partial year-to-date rollup is never ranked against full years.
            comparable_flag=result.complete,
        )
        value_ids.append(vid)
        period_ids.append(period_id)
    return RollupWritten(value_ids=value_ids, period_ids=period_ids)


def rollup_ridership(repo, agency_slug: str, year: int) -> list[int]:
    """Roll the agency's monthly ridership up to `year`. Returns written value ids."""
    return rollup_metric(repo, agency_slug, year, "ridership").value_ids


# --- generalized CALENDAR roll-up (month/quarter -> quarter/annual/ytd) -------


class CalendarRollupWritten(NamedTuple):
    """What a calendar roll-up wrote, plus any cross-check flags it raised.

    A flag is `'<SUM_MISMATCH> (<slug> <metric> <period.label> scope <scope>)'`
    raised when a target period is BOTH sourced and derivable but the two
    disagree beyond tolerance -- the sourced value is kept untouched."""

    value_ids: list[int]
    period_ids: list[int]
    warnings: list[str]


def calendar_rollup_metric(
    repo, agency_slug: str, year: int, metric_code: str
) -> CalendarRollupWritten:
    """Auto-fill the calendar quarter / annual / ytd values of `metric_code` for
    `year` by summing lower-granularity SOURCED values WITHIN the calendar year.

    Per (mode_id, service_scope) partition: gathers the agency's current monthly
    and quarterly values that fall in calendar `year`, plans the derivable targets
    (`periods.plan_calendar_rollups`), and for each target either

      - writes a derived value (equation_code = period_rollup) into an EMPTY slot,
        citing the exact summed input rows; or
      - if the slot already holds a SOURCED value, cross-checks it and raises a
        `sum_mismatch` warning on disagreement -- never overwriting it.

    Only sourced inputs are summed (a value carrying a derivation is skipped), so a
    derived quarter never feeds a derived annual. Returns the ids/periods written
    plus the cross-check warnings.
    """
    meta = METRICS[metric_code]
    unit = meta["unit"]
    currency = "CAD" if meta["unit_type"] == "currency" else None

    agency_id = repo.agency_id(agency_slug)
    metric_id = repo.metric_id(metric_code)

    # Locate the reporting_period rows for this calendar year's months & quarters.
    month_period = {m: monthly_period(year, m) for m in range(1, 13)}
    quarter_period = {q: quarterly_period(year, q) for q in (1, 2, 3, 4)}
    period_by_dates = {
        (p.start_date, p.end_date): p for p in repo.list_reporting_periods()
    }

    def _gather(builder_by_key):
        """key -> {(mode_id, scope): MetricValue} for sourced rows in those periods."""
        by_key: dict[int, dict[tuple, object]] = {}
        for key, bp in builder_by_key.items():
            period = period_by_dates.get((bp.start, bp.end))
            if period is None:
                continue
            for v in repo.list_current_values_for_agency_period(agency_id, period.id):
                if v.metric_id != metric_id:
                    continue
                if repo.get_derivation(v.id) is not None:
                    continue  # only SOURCED inputs roll up; skip derived rows
                by_key.setdefault(key, {})[(v.mode_id, v.service_scope)] = v
        return by_key

    months_by_key = _gather(month_period)
    quarters_by_key = _gather(quarter_period)

    # Partitions = every (mode_id, service_scope) seen at any input granularity.
    partitions: set[tuple] = set()
    for d in (*months_by_key.values(), *quarters_by_key.values()):
        partitions.update(d.keys())

    value_ids: list[int] = []
    period_ids: list[int] = []
    warnings: list[str] = []

    for (mode_id, scope) in sorted(partitions, key=lambda p: (p[0] or 0, p[1])):
        monthly_vals = {
            m: months_by_key[m][(mode_id, scope)].value
            for m in months_by_key
            if (mode_id, scope) in months_by_key[m]
        }
        quarterly_vals = {
            q: quarters_by_key[q][(mode_id, scope)].value
            for q in quarters_by_key
            if (mode_id, scope) in quarters_by_key[q]
        }
        src_value = {"month": months_by_key, "quarter": quarters_by_key}

        for plan in plan_calendar_rollups(year, monthly_vals, quarterly_vals):
            summed = [src_value[kind][n][(mode_id, scope)] for kind, n in plan.inputs]
            period_id = repo.get_or_create_reporting_period(
                plan.period.period_type,
                plan.period.start,
                plan.period.end,
                plan.period.label,
            )
            existing = repo.get_current_metric_value(
                agency_id, metric_id, period_id, mode_id, scope
            )
            if existing is not None:
                # Never overwrite a sourced slot. If it is itself a SOURCED value,
                # cross-check it; a derived value here is our own prior output -> skip.
                if repo.get_derivation(existing.id) is None and not _close(
                    existing.value, plan.value, Decimal("0.02"), Decimal("0")
                ):
                    warnings.append(
                        f"{SUM_MISMATCH} ({agency_slug} {metric_code} "
                        f"{plan.period.label} scope {scope})"
                    )
                continue
            vid = repo.insert_derived_value(
                agency_id=agency_id,
                metric_id=metric_id,
                reporting_period_id=period_id,
                mode_id=mode_id,
                service_scope=scope,
                value=plan.value,
                unit=unit,
                quality=weakest_quality([mv.quality for mv in summed]),
                equation_code=PERIOD_ROLLUP,
                input_value_ids=[mv.id for mv in summed],
                currency=currency,
                # A partial ytd is never ranked against full years.
                comparable_flag=plan.complete,
            )
            value_ids.append(vid)
            period_ids.append(period_id)

    return CalendarRollupWritten(
        value_ids=value_ids, period_ids=period_ids, warnings=warnings
    )
