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
