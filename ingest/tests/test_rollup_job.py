"""Tests for the repo-backed monthly->annual ridership rollup job."""

from __future__ import annotations

from decimal import Decimal

from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.jobs.rollup import rollup_ridership
from transitindex_ingest.periods import monthly_period


def _seed_month(repo, slug, year, month, value, *, scope="total", quality="verified") -> int:
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


def _annual(repo, slug, year, period_type="annual_calendar", scope="total"):
    from transitindex_ingest.periods import annual_period

    ap = annual_period(slug, year)
    pid = repo.get_or_create_reporting_period(ap.period_type, ap.start, ap.end, ap.label)
    return repo.get_current_metric_value(
        repo.agency_id(slug), repo.metric_id("ridership"), pid, None, scope
    )


def test_twelve_months_roll_up_to_annual_with_provenance():
    repo = InMemoryRepository()
    month_ids = [_seed_month(repo, "ttc", 2024, m, "100") for m in range(1, 13)]

    ids = rollup_ridership(repo, "ttc", 2024)
    assert len(ids) == 1

    annual = _annual(repo, "ttc", 2024)
    assert annual is not None
    assert annual.value == Decimal("1200")
    assert annual.comparable_flag is True
    deriv = repo.get_derivation(annual.id)
    assert deriv["equation_code"] == "period_rollup"
    assert set(deriv["input_value_ids"]) == set(month_ids)  # all 12 cited


def test_partial_year_rolls_to_ytd_not_ranked():
    repo = InMemoryRepository()
    for m in range(1, 9):  # Jan..Aug only
        _seed_month(repo, "ttc", 2025, m, "100")

    rollup_ridership(repo, "ttc", 2025)

    # No full-year annual row was written...
    assert _annual(repo, "ttc", 2025) is None
    # ...but a partial ytd row exists, flagged not-comparable (never ranked).
    ytd = [
        v
        for v in repo._values.values()
        if v.metric_id == repo.metric_id("ridership")
        and repo._periods[v.reporting_period_id].period_type == "ytd"
    ]
    assert len(ytd) == 1
    assert ytd[0].value == Decimal("800")
    assert ytd[0].comparable_flag is False


def test_rollup_then_recompute_derives_annual_ratios():
    """The rollup populates annual ridership; the solver then derives annual ratios."""
    from transitindex_ingest.jobs.derived_recompute import recompute_derived
    from transitindex_ingest.periods import annual_period

    repo = InMemoryRepository()
    for m in range(1, 13):
        _seed_month(repo, "ttc", 2024, m, "100")  # annual ridership -> 1200
    rollup_ridership(repo, "ttc", 2024)

    # Add annual operating_revenue at the same annual period + scope.
    ap = annual_period("ttc", 2024)
    annual_pid = repo.get_or_create_reporting_period(ap.period_type, ap.start, ap.end, ap.label)
    repo.insert_metric_value(
        agency_id=repo.agency_id("ttc"),
        metric_id=repo.metric_id("operating_revenue"),
        reporting_period_id=annual_pid,
        mode_id=None,
        service_scope="total",
        value=Decimal("3000"),
        unit="CAD",
        quality="verified",
    )

    recompute_derived(repo, "ttc", annual_pid)

    af = repo.get_current_metric_value(
        repo.agency_id("ttc"), repo.metric_id("average_fare"), annual_pid, None, "total"
    )
    assert af is not None
    assert af.value == Decimal("2.5")  # 3000 / 1200, from the rolled-up annual ridership
