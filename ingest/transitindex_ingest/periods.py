"""Reporting-period builders.

Turn a (year, month) or (agency, year) into the (period_type, start, end,
label) tuple that core.reporting_periods stores. Annual periods pick
annual_calendar vs annual_fiscal from the agency's fiscal_year_end_month.
Pure stdlib.
"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Optional

from .contract import PeriodType
from .refdata import AGENCIES

_MONTH_ABBR = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


@dataclass(frozen=True)
class Period:
    """A fully specified reporting period, ready for the repository."""

    period_type: PeriodType
    start: date
    end: date
    label: str


def monthly_period(year: int, month: int) -> Period:
    """Build a calendar-month period, e.g. (2026, 3) -> 'Mar 2026'."""
    if not 1 <= month <= 12:
        raise ValueError(f"month must be 1..12, got {month}")
    start = date(year, month, 1)
    end = date(year, month, monthrange(year, month)[1])
    return Period("monthly", start, end, f"{_MONTH_ABBR[month - 1]} {year}")


def annual_period(agency_slug: str, year: int) -> Period:
    """Build the annual period for an agency in a given calendar/start year.

    If fiscal_year_end_month == 12 the period is the calendar year
    (annual_calendar, label '2024'). Otherwise it is the fiscal year that ENDS
    in `year + 1`, running from the month after fiscal_year_end_month through
    fiscal_year_end_month (annual_fiscal, label 'FY2024-25'). `year` is the
    calendar year in which the fiscal year starts.
    """
    agency = AGENCIES.get(agency_slug)
    if agency is None:
        raise ValueError(f"unknown agency_slug: {agency_slug!r}")
    fy_end_month = agency["fiscal_year_end_month"]

    if fy_end_month == 12:
        return Period(
            "annual_calendar",
            date(year, 1, 1),
            date(year, 12, 31),
            str(year),
        )

    # Fiscal year: starts the month after fy_end_month in `year`, ends on the
    # last day of fy_end_month in `year + 1`.
    start = date(year, fy_end_month + 1, 1)
    end_year = year + 1
    end = date(end_year, fy_end_month, monthrange(end_year, fy_end_month)[1])
    label = f"FY{year}-{str(end_year)[2:]}"
    return Period("annual_fiscal", start, end, label)


def annual_period_from_end_year(agency_slug: str, end_year: int) -> Period:
    """Build the annual period given the calendar year the reporting year ENDS in.

    This is the convention sources state directly (and that the PDF extractor
    emits): an annual figure is named by the year its reporting period ends in.
    A calendar agency's "2024" ends in 2024, so end_year IS the start year. A
    fiscal agency named by its end year -- e.g. the fiscal year ending March
    2024 (which runs April 2023 -> March 2024) -- started the prior calendar
    year, so the start year is end_year - 1.

    `annual_period` itself keeps its START-year contract (relied on by the
    workbook and rollup jobs); this helper just translates an end-year into it.
    """
    agency = AGENCIES.get(agency_slug)
    if agency is None:
        raise ValueError(f"unknown agency_slug: {agency_slug!r}")
    fy_end_month = agency["fiscal_year_end_month"]
    start_year = end_year if fy_end_month == 12 else end_year - 1
    return annual_period(agency_slug, start_year)


def quarterly_period(year: int, quarter: int) -> Period:
    """Build a calendar-quarter period, e.g. (2024, 1) -> '2024-Q1' (Jan–Mar).

    TransLink is the one agency that publishes a quarterly statement of financial
    position; everyone else reports the balance sheet annually."""
    if not 1 <= quarter <= 4:
        raise ValueError(f"quarter must be 1..4, got {quarter}")
    start_month = (quarter - 1) * 3 + 1
    end_month = start_month + 2
    start = date(year, start_month, 1)
    end = date(year, end_month, monthrange(year, end_month)[1])
    return Period("quarterly", start, end, f"{year}-Q{quarter}")


# --- period rollup (monthly -> annual, fiscal-aware) -------------------------


def fiscal_year_months(agency_slug: str, year: int) -> tuple[tuple[int, int], ...]:
    """The twelve (calendar_year, calendar_month) pairs composing an agency's
    annual period for `year`, in order.

    Calendar agencies (fiscal_year_end_month == 12) return Jan..Dec of `year`.
    Fiscal agencies (e.g. Metrolinx, BC Transit end in March) return the twelve
    months of their fiscal year -- e.g. Apr `year` .. Mar `year + 1`.
    """
    agency = AGENCIES.get(agency_slug)
    if agency is None:
        raise ValueError(f"unknown agency_slug: {agency_slug!r}")
    fy_end_month = agency["fiscal_year_end_month"]
    start_month = (fy_end_month % 12) + 1  # 1 for calendar; month after fy-end otherwise
    out: list[tuple[int, int]] = []
    y, m = year, start_month
    for _ in range(12):
        out.append((y, m))
        m += 1
        if m > 12:
            m, y = 1, y + 1
    return tuple(out)


def ytd_period(agency_slug: str, year: int, through_count: int) -> Period:
    """A partial year-to-date period covering the first `through_count` months
    of the agency's year (1..11). period_type='ytd'; never ranked against a full
    year. Label e.g. '2025 YTD (Jan–Aug)' or 'FY2025-26 YTD (Apr–Aug)'."""
    if not 1 <= through_count <= 11:
        raise ValueError(f"through_count must be 1..11, got {through_count}")
    months = fiscal_year_months(agency_slug, year)
    (first_y, first_m) = months[0]
    (last_y, last_m) = months[through_count - 1]
    start = date(first_y, first_m, 1)
    end = date(last_y, last_m, monthrange(last_y, last_m)[1])
    base = annual_period(agency_slug, year).label  # '2025' or 'FY2025-26'
    label = f"{base} YTD ({_MONTH_ABBR[first_m - 1]}–{_MONTH_ABBR[last_m - 1]})"
    return Period("ytd", start, end, label)


@dataclass(frozen=True)
class Rollup:
    """The result of rolling monthly values up to a year.

    `complete` is True only when all twelve months are present (an annual
    period). Otherwise `period` is a partial `ytd` period covering the
    contiguous run of months present from the start of the year.
    """

    period: Period
    value: Decimal
    complete: bool
    months_present: int
    month_indices: tuple[int, ...]  # 1-based positions within the fiscal year


def roll_up(
    agency_slug: str, year: int, monthly: Mapping[tuple[int, int], Decimal]
) -> Optional[Rollup]:
    """Sum monthly values into an annual figure, fiscal-aware.

    `monthly` maps (calendar_year, calendar_month) -> value. All twelve months
    present -> a complete annual rollup. Fewer -> a partial year-to-date rollup
    over the CONTIGUOUS run of months present from the start of the year (a gap
    stops the run, so we never sum across a hole into a fake "year"). Returns
    None if the first month of the year is missing (no run to roll up). Never
    fabricates a missing month.
    """
    months = fiscal_year_months(agency_slug, year)
    prefix: list[Decimal] = []
    for cal in months:
        v = monthly.get(cal)
        if v is None:
            break
        prefix.append(v)
    if not prefix:
        return None
    k = len(prefix)
    total = sum(prefix, Decimal(0))
    indices = tuple(range(1, k + 1))
    if k == 12:
        return Rollup(annual_period(agency_slug, year), total, True, 12, indices)
    return Rollup(ytd_period(agency_slug, year, k), total, False, k, indices)


# --- calendar-year rollup (month/quarter -> quarter, annual_calendar, ytd) ---
#
# A second, CALENDAR-only family: it sums lower-granularity sourced values within
# a single calendar year into the higher-granularity calendar periods. Used for
# every agency regardless of its fiscal year-end -- a calendar value is NEVER
# synthesized from fiscal-year inputs, so this stays strictly Jan..Dec.

_MONTHS_OF_QUARTER = {q: ((q - 1) * 3 + 1, (q - 1) * 3 + 2, (q - 1) * 3 + 3) for q in (1, 2, 3, 4)}


def calendar_annual_period(year: int) -> Period:
    """The calendar-year period (Jan 1 .. Dec 31), label e.g. '2024'.

    Distinct from `annual_period`, which returns an annual_fiscal period for
    fiscal agencies -- this is always the calendar year."""
    return Period("annual_calendar", date(year, 1, 1), date(year, 12, 31), str(year))


def calendar_ytd_period(year: int, through_month: int) -> Period:
    """A calendar year-to-date period covering Jan .. `through_month` (1..11).

    period_type='ytd'; never ranked against a full year. Label e.g.
    '2025 YTD (Jan–Aug)'. through_month==12 would be a full year, so it is rejected."""
    if not 1 <= through_month <= 11:
        raise ValueError(f"through_month must be 1..11, got {through_month}")
    end = date(year, through_month, monthrange(year, through_month)[1])
    label = f"{year} YTD (Jan–{_MONTH_ABBR[through_month - 1]})"
    return Period("ytd", date(year, 1, 1), end, label)


@dataclass(frozen=True)
class CalendarRollup:
    """One derivable calendar period: its `period`, summed `value`, and the
    component source keys it summed (so the job can cite the exact input rows).

    `inputs` is a tuple of ('month', m) / ('quarter', q) keys, in calendar order.
    `complete` is True for a full annual_calendar or a sourced-quarter-complete
    quarter (used only to set comparable_flag; ytd is always partial)."""

    period: Period
    value: Decimal
    inputs: tuple[tuple[str, int], ...]
    complete: bool


def _sum_inputs(
    keys: tuple[tuple[str, int], ...],
    monthly: Mapping[int, Decimal],
    quarterly: Mapping[int, Decimal],
) -> Decimal:
    src = {"month": monthly, "quarter": quarterly}
    return sum((src[kind][n] for kind, n in keys), Decimal(0))


def plan_calendar_rollups(
    year: int,
    monthly: Mapping[int, Decimal],
    quarterly: Mapping[int, Decimal],
) -> list[CalendarRollup]:
    """Plan the calendar quarter / annual / ytd values derivable from sourced
    month and quarter values, summing WITHIN the calendar `year`.

    `monthly` maps calendar month (1..12) -> value; `quarterly` maps calendar
    quarter (1..4) -> value. Returns one `CalendarRollup` per derivable target:

      - quarter = sum of its 3 calendar months (only when ALL three are present);
      - annual_calendar = sum of 12 months, or of 4 quarters when monthly is
        absent (prefers the finer monthly grain when both are available);
      - ytd = running sum of the calendar year's months to date (the contiguous
        run from January), or of the whole quarters to date when monthly is absent.

    Pure arithmetic. It never fabricates a missing input and never decides what to
    WRITE -- the caller skips a target that is itself already sourced (and instead
    cross-checks it) and only writes into empty slots."""
    out: list[CalendarRollup] = []

    # Quarters: derivable only from a complete set of their 3 calendar months.
    derivable_quarters: set[int] = set()
    for q in (1, 2, 3, 4):
        ms = _MONTHS_OF_QUARTER[q]
        if all(m in monthly for m in ms):
            keys = tuple(("month", m) for m in ms)
            out.append(
                CalendarRollup(
                    quarterly_period(year, q),
                    _sum_inputs(keys, monthly, quarterly),
                    keys,
                    complete=True,
                )
            )
            derivable_quarters.add(q)

    # Available quarter grain = sourced quarters ∪ quarters we can derive from months.
    quarter_keys: dict[int, tuple[tuple[str, int], ...]] = {}
    for q in (1, 2, 3, 4):
        if all(m in monthly for m in _MONTHS_OF_QUARTER[q]):
            quarter_keys[q] = tuple(("month", m) for m in _MONTHS_OF_QUARTER[q])
        elif q in quarterly:
            quarter_keys[q] = (("quarter", q),)

    # Annual: prefer 12 months; else 4 derivable/sourced quarters.
    if all(m in monthly for m in range(1, 13)):
        keys = tuple(("month", m) for m in range(1, 13))
        out.append(
            CalendarRollup(
                calendar_annual_period(year),
                _sum_inputs(keys, monthly, quarterly),
                keys,
                complete=True,
            )
        )
    elif all(q in quarter_keys for q in (1, 2, 3, 4)):
        keys = tuple(k for q in (1, 2, 3, 4) for k in quarter_keys[q])
        out.append(
            CalendarRollup(
                calendar_annual_period(year),
                _sum_inputs(keys, monthly, quarterly),
                keys,
                complete=True,
            )
        )

    # YTD: the contiguous run from January. Prefer the monthly grain; fall back to
    # whole quarters when no month is present. Only emit a PARTIAL ytd (< full year).
    month_run = 0
    for m in range(1, 13):
        if m not in monthly:
            break
        month_run = m
    if 1 <= month_run <= 11:
        keys = tuple(("month", m) for m in range(1, month_run + 1))
        out.append(
            CalendarRollup(
                calendar_ytd_period(year, month_run),
                _sum_inputs(keys, monthly, quarterly),
                keys,
                complete=False,
            )
        )
    elif month_run == 0:
        quarter_run = 0
        for q in (1, 2, 3, 4):
            if q not in quarter_keys:
                break
            quarter_run = q
        if 1 <= quarter_run <= 3:  # 4 whole quarters is the full year, not a ytd
            keys = tuple(k for q in range(1, quarter_run + 1) for k in quarter_keys[q])
            out.append(
                CalendarRollup(
                    calendar_ytd_period(year, quarter_run * 3),
                    _sum_inputs(keys, monthly, quarterly),
                    keys,
                    complete=False,
                )
            )

    return out
