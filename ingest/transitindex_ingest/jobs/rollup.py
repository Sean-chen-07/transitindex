"""Roll monthly ridership up to an annual (or partial year-to-date) value.

Reads the agency's current MONTHLY ridership values spanning its fiscal year,
sums the contiguous run from the start of the year (`periods.roll_up`), and
writes the result as a DERIVED value via `repo.insert_derived_value` with the
summed monthly rows as provenance (equation_code = `period_rollup`). A complete
year becomes an annual period (comparable_flag=True); an incomplete year becomes
a partial `ytd` period that never ranks against full years (comparable_flag=False).
One rollup per (mode_id, service_scope) partition.

This runs BEFORE the within-period equation solver for the annual period: once
the annual ridership exists, `recompute_derived` can derive average_fare,
cost_per_rider, etc. for that year.
"""

from __future__ import annotations

from ..equations import PERIOD_ROLLUP
from ..periods import fiscal_year_months, monthly_period, roll_up
from .derived_recompute import weakest_quality


def rollup_ridership(repo, agency_slug: str, year: int) -> list[int]:
    """Roll the agency's monthly ridership up to `year`. Returns written ids."""
    agency_id = repo.agency_id(agency_slug)
    rid_metric = repo.metric_id("ridership")
    months = fiscal_year_months(agency_slug, year)

    # Locate the reporting_period for each composing month (if it exists).
    period_by_dates = {
        (p.start_date, p.end_date): p
        for p in repo.list_reporting_periods()
        if p.period_type == "monthly"
    }

    # Gather current monthly ridership values per (mode_id, service_scope) partition.
    partitions: dict[tuple, dict[tuple[int, int], object]] = {}
    for (cy, cm) in months:
        mp = monthly_period(cy, cm)
        period = period_by_dates.get((mp.start, mp.end))
        if period is None:
            continue
        for v in repo.list_current_values_for_agency_period(agency_id, period.id):
            if v.metric_id != rid_metric:
                continue
            partitions.setdefault((v.mode_id, v.service_scope), {})[(cy, cm)] = v

    ids: list[int] = []
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
            metric_id=rid_metric,
            reporting_period_id=period_id,
            mode_id=mode_id,
            service_scope=scope,
            value=result.value,
            unit="count",
            quality=weakest_quality([mv.quality for mv in summed]),
            equation_code=PERIOD_ROLLUP,
            input_value_ids=[mv.id for mv in summed],
            # A partial year-to-date rollup is never ranked against full years.
            comparable_flag=result.complete,
        )
        ids.append(vid)
    return ids
