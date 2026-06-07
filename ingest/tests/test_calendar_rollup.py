"""Tests for the generalized CALENDAR roll-up: the pure planner
(`periods.plan_calendar_rollups`) and the repo-backed
`jobs.rollup.calendar_rollup_metric` (quarter / annual_calendar / ytd)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.jobs.rollup import calendar_rollup_metric
from transitindex_ingest.periods import (
    monthly_period,
    plan_calendar_rollups,
    quarterly_period,
)


# --- pure planner -----------------------------------------------------------


def _types(plans):
    return {p.period.period_type for p in plans}


def _by_type(plans, period_type):
    return next(p for p in plans if p.period.period_type == period_type)


def test_full_year_of_months_plans_four_quarters_and_annual():
    monthly = {m: Decimal("10") for m in range(1, 13)}
    plans = plan_calendar_rollups(2024, monthly, {})
    quarters = [p for p in plans if p.period.period_type == "quarterly"]
    assert len(quarters) == 4
    assert all(p.value == Decimal("30") for p in quarters)  # 3 months * 10
    annual = _by_type(plans, "annual_calendar")
    assert annual.value == Decimal("120")
    assert annual.complete is True
    assert len(annual.inputs) == 12  # cites all 12 months, not the derived quarters
    assert "ytd" not in _types(plans)  # full year is not a ytd


def test_partial_months_plans_ytd_over_contiguous_run():
    monthly = {m: Decimal("10") for m in range(1, 9)}  # Jan..Aug
    plans = plan_calendar_rollups(2024, monthly, {})
    ytd = _by_type(plans, "ytd")
    assert ytd.value == Decimal("80")
    assert ytd.complete is False
    assert ytd.period.label == "2024 YTD (Jan–Aug)"
    # Q1 + Q2 are complete (6 months); Q3 (Jul,Aug,Sep) is not -> only 2 quarters.
    assert len([p for p in plans if p.period.period_type == "quarterly"]) == 2
    assert "annual_calendar" not in _types(plans)  # not a full year


def test_interior_gap_stops_ytd_run():
    # Jan,Feb,Mar present, Apr missing, May.. present -> ytd through Mar only.
    monthly = {1: Decimal("10"), 2: Decimal("10"), 3: Decimal("10"), 5: Decimal("10")}
    plans = plan_calendar_rollups(2024, monthly, {})
    ytd = _by_type(plans, "ytd")
    assert ytd.value == Decimal("30")  # never sums across the April hole
    assert ytd.period.label == "2024 YTD (Jan–Mar)"


def test_annual_from_quarters_when_months_absent():
    quarterly = {q: Decimal("25") for q in (1, 2, 3, 4)}
    plans = plan_calendar_rollups(2024, {}, quarterly)
    annual = _by_type(plans, "annual_calendar")
    assert annual.value == Decimal("100")
    assert annual.inputs == (("quarter", 1), ("quarter", 2), ("quarter", 3), ("quarter", 4))
    # No quarters are derived (they are themselves sourced), and 4 whole quarters
    # is a full year, not a ytd.
    assert _types(plans) == {"annual_calendar"}


def test_ytd_from_quarters_when_months_absent():
    quarterly = {1: Decimal("25"), 2: Decimal("25")}  # H1 only
    plans = plan_calendar_rollups(2024, {}, quarterly)
    ytd = _by_type(plans, "ytd")
    assert ytd.value == Decimal("50")
    assert ytd.period.label == "2024 YTD (Jan–Jun)"


# --- repo-backed job --------------------------------------------------------


def _seed_month(repo, slug, year, month, value, *, scope="total", quality="verified"):
    mp = monthly_period(year, month)
    pid = repo.get_or_create_reporting_period(mp.period_type, mp.start, mp.end, mp.label)
    return repo.insert_metric_value(
        agency_id=repo.agency_id(slug),
        metric_id=repo.metric_id("ridership"),
        reporting_period_id=pid,
        mode_id=None,
        service_scope=scope,
        value=Decimal(value),
        unit="count",
        quality=quality,
    )


def _current_quarter(repo, slug, year, quarter, *, scope="total"):
    qp = quarterly_period(year, quarter)
    pid = repo.get_or_create_reporting_period(qp.period_type, qp.start, qp.end, qp.label)
    return repo.get_current_metric_value(
        repo.agency_id(slug), repo.metric_id("ridership"), pid, None, scope
    )


def _current_annual(repo, slug, year, *, scope="total"):
    pid = repo.get_or_create_reporting_period(
        "annual_calendar", date(year, 1, 1), date(year, 12, 31), str(year)
    )
    return repo.get_current_metric_value(
        repo.agency_id(slug), repo.metric_id("ridership"), pid, None, scope
    )


def test_job_fills_quarters_and_annual_with_provenance():
    repo = InMemoryRepository()
    month_ids = {m: _seed_month(repo, "ttc", 2024, m, "100") for m in range(1, 13)}

    out = calendar_rollup_metric(repo, "ttc", 2024, "ridership")
    assert out.warnings == []
    assert len(out.value_ids) == 5  # 4 quarters + 1 annual

    q1 = _current_quarter(repo, "ttc", 2024, 1)
    assert q1.value == Decimal("300")
    deriv = repo.get_derivation(q1.id)
    assert deriv["equation_code"] == "period_rollup"
    assert set(deriv["input_value_ids"]) == {month_ids[1], month_ids[2], month_ids[3]}

    annual = _current_annual(repo, "ttc", 2024)
    assert annual.value == Decimal("1200")
    assert annual.comparable_flag is True
    # Annual cites the 12 SOURCED months, not the derived quarters.
    assert set(repo.get_derivation(annual.id)["input_value_ids"]) == set(month_ids.values())


def test_job_never_overwrites_sourced_quarter_and_crosschecks():
    repo = InMemoryRepository()
    for m in range(1, 4):
        _seed_month(repo, "ttc", 2024, m, "100")  # Q1 months -> sum 300
    # A SOURCED Q1 that DISAGREES with the monthly sum.
    qp = quarterly_period(2024, 1)
    qpid = repo.get_or_create_reporting_period(qp.period_type, qp.start, qp.end, qp.label)
    sourced_q1 = repo.insert_metric_value(
        agency_id=repo.agency_id("ttc"),
        metric_id=repo.metric_id("ridership"),
        reporting_period_id=qpid,
        mode_id=None,
        service_scope="total",
        value=Decimal("999"),
        unit="count",
        quality="verified",
    )

    out = calendar_rollup_metric(repo, "ttc", 2024, "ridership")
    # The sourced Q1 is untouched...
    q1 = _current_quarter(repo, "ttc", 2024, 1)
    assert q1.id == sourced_q1 and q1.value == Decimal("999")
    assert repo.get_derivation(q1.id) is None
    # ...and the disagreement is flagged.
    assert any("sum_mismatch" in w for w in out.warnings)


def test_job_agreeing_sourced_quarter_raises_no_flag():
    repo = InMemoryRepository()
    for m in range(1, 4):
        _seed_month(repo, "ttc", 2024, m, "100")  # -> 300
    qp = quarterly_period(2024, 1)
    qpid = repo.get_or_create_reporting_period(qp.period_type, qp.start, qp.end, qp.label)
    repo.insert_metric_value(
        agency_id=repo.agency_id("ttc"),
        metric_id=repo.metric_id("ridership"),
        reporting_period_id=qpid,
        mode_id=None,
        service_scope="total",
        value=Decimal("300"),  # agrees with the monthly sum
        unit="count",
        quality="verified",
    )
    out = calendar_rollup_metric(repo, "ttc", 2024, "ridership")
    assert out.warnings == []


def test_job_partial_year_writes_ytd_not_annual():
    repo = InMemoryRepository()
    for m in range(1, 9):  # Jan..Aug
        _seed_month(repo, "ttc", 2024, m, "100")
    calendar_rollup_metric(repo, "ttc", 2024, "ridership")

    assert _current_annual(repo, "ttc", 2024) is None  # no full-year row
    ytd = [
        v
        for v in repo._values.values()
        if v.metric_id == repo.metric_id("ridership")
        and repo._periods[v.reporting_period_id].period_type == "ytd"
        and v.is_current
    ]
    assert len(ytd) == 1
    assert ytd[0].value == Decimal("800")
    assert ytd[0].comparable_flag is False  # never ranked against full years
