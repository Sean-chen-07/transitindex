"""Tests for the fiscal-aware monthly->annual period rollup (stdlib + pytest)."""

from __future__ import annotations

from decimal import Decimal

from transitindex_ingest.periods import (
    fiscal_year_months,
    quarterly_period,
    roll_up,
    ytd_period,
)


def test_quarterly_period_calendar_quarters():
    q1 = quarterly_period(2024, 1)
    assert q1.period_type == "quarterly"
    assert q1.label == "2024-Q1"
    assert (q1.start.month, q1.end.month) == (1, 3)
    q4 = quarterly_period(2024, 4)
    assert q4.label == "2024-Q4"
    assert (q4.start.month, q4.end.month) == (10, 12)
    import pytest

    with pytest.raises(ValueError):
        quarterly_period(2024, 5)


# --- fiscal_year_months -----------------------------------------------------


def test_calendar_agency_months_are_jan_to_dec():
    months = fiscal_year_months("ttc", 2025)  # ttc ends in December
    assert months == tuple((2025, m) for m in range(1, 13))


def test_fiscal_agency_months_span_apr_to_mar():
    months = fiscal_year_months("metrolinx", 2024)  # ends in March
    expected = tuple([(2024, m) for m in range(4, 13)] + [(2025, m) for m in (1, 2, 3)])
    assert months == expected


# --- complete rollups -------------------------------------------------------


def _twelve(months, value=Decimal("100")):
    return {m: value for m in months}


def test_complete_calendar_year_rolls_to_annual():
    months = fiscal_year_months("ttc", 2025)
    r = roll_up("ttc", 2025, _twelve(months))
    assert r is not None
    assert r.complete is True
    assert r.value == Decimal("1200")
    assert r.period.period_type == "annual_calendar"
    assert r.period.label == "2025"
    assert r.months_present == 12


def test_complete_fiscal_year_rolls_to_annual_fiscal():
    months = fiscal_year_months("metrolinx", 2024)
    r = roll_up("metrolinx", 2024, _twelve(months, Decimal("10")))
    assert r is not None
    assert r.complete is True
    assert r.value == Decimal("120")
    assert r.period.period_type == "annual_fiscal"
    assert r.period.label == "FY2024-25"


# --- partial (year-to-date) rollups -----------------------------------------


def test_partial_year_rolls_to_ytd():
    months = fiscal_year_months("ttc", 2025)
    monthly = {m: Decimal("100") for m in months[:8]}  # Jan..Aug present
    r = roll_up("ttc", 2025, monthly)
    assert r is not None
    assert r.complete is False
    assert r.months_present == 8
    assert r.value == Decimal("800")
    assert r.period.period_type == "ytd"
    assert r.period.label == "2025 YTD (Jan–Aug)"


def test_interior_gap_stops_the_contiguous_run():
    # Jan, Feb, Mar present; Apr missing; May..Aug present -> YTD through Mar only.
    monthly = {
        (2025, 1): Decimal("100"),
        (2025, 2): Decimal("100"),
        (2025, 3): Decimal("100"),
        (2025, 5): Decimal("100"),
        (2025, 6): Decimal("100"),
    }
    r = roll_up("ttc", 2025, monthly)
    assert r is not None
    assert r.complete is False
    assert r.months_present == 3
    assert r.value == Decimal("300")  # never sums across the April hole
    assert r.period.label == "2025 YTD (Jan–Mar)"


def test_partial_fiscal_year_labels_from_fiscal_start():
    months = fiscal_year_months("metrolinx", 2024)
    monthly = {m: Decimal("10") for m in months[:2]}  # Apr, May
    r = roll_up("metrolinx", 2024, monthly)
    assert r is not None
    assert r.period.period_type == "ytd"
    assert r.period.label == "FY2024-25 YTD (Apr–May)"


def test_missing_first_month_yields_no_rollup():
    monthly = {(2025, 2): Decimal("100"), (2025, 3): Decimal("100")}  # Jan missing
    assert roll_up("ttc", 2025, monthly) is None


def test_ytd_period_rejects_full_year_count():
    import pytest

    with pytest.raises(ValueError):
        ytd_period("ttc", 2025, 12)
