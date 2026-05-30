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
