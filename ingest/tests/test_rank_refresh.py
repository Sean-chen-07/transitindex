"""Tests for the rank-refresh job (jobs/rank_refresh.py).

Offline: pure stdlib + pytest, driven entirely through the in-memory repo.
Covers the pure `compute_ranks` helper (ordering, ties, denominator) and the
`refresh_ranks` orchestration (comparable filter, subdivision grouping,
period-comparability, direction strings).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from transitindex_ingest.jobs.rank_refresh import compute_ranks, refresh_ranks


# --- helpers ----------------------------------------------------------------


def _period(repo, agency_slug: str = "ttc") -> int:
    """A shared reporting period id all agencies' values point at."""
    return repo.get_or_create_reporting_period(
        repo.agency_id(agency_slug),
        "annual_calendar",
        date(2024, 1, 1),
        date(2024, 12, 31),
        "2024",
    )


def _put(repo, slug, metric_code, period_id, value, *, comparable=True,
         scope="system_wide"):
    """Insert a current metric value for an agency in `period_id`."""
    return repo.insert_metric_value(
        agency_id=repo.agency_id(slug),
        metric_id=repo.metric_id(metric_code),
        reporting_period_id=period_id,
        mode_id=None,
        service_scope=scope,
        value=Decimal(value),
        unit="count",
        quality="verified",
        comparable_flag=comparable,
    )


def _ranks(repo, metric_code, period_id, comparison_set):
    """Read back the stored MetricRankRows for a (metric, period, set)."""
    metric_id = repo.metric_id(metric_code)
    return repo._ranks.get((metric_id, period_id, comparison_set), [])


# --- compute_ranks (pure helper) --------------------------------------------


def test_compute_ranks_higher_is_better_descending():
    vals = [
        SimpleNamespace(agency_id=1, value=Decimal("10")),
        SimpleNamespace(agency_id=2, value=Decimal("30")),
        SimpleNamespace(agency_id=3, value=Decimal("20")),
    ]
    result = compute_ranks(vals, higher_is_better=True)
    # rank 1 = highest value (agency 2), denominator = 3 for all
    assert result == [(2, 1, 3), (3, 2, 3), (1, 3, 3)]


def test_compute_ranks_lower_is_better_ascending():
    vals = [
        SimpleNamespace(agency_id=1, value=Decimal("10")),
        SimpleNamespace(agency_id=2, value=Decimal("30")),
        SimpleNamespace(agency_id=3, value=Decimal("20")),
    ]
    result = compute_ranks(vals, higher_is_better=False)
    # rank 1 = lowest value (agency 1)
    assert result == [(1, 1, 3), (3, 2, 3), (2, 3, 3)]


def test_compute_ranks_neutral_ranks_descending():
    vals = [
        SimpleNamespace(agency_id=1, value=Decimal("10")),
        SimpleNamespace(agency_id=2, value=Decimal("30")),
    ]
    # None (neutral) still ranks by value descending
    assert compute_ranks(vals, higher_is_better=None) == [(2, 1, 2), (1, 2, 2)]


def test_compute_ranks_ties_share_rank():
    vals = [
        SimpleNamespace(agency_id=1, value=Decimal("50")),
        SimpleNamespace(agency_id=2, value=Decimal("50")),
        SimpleNamespace(agency_id=3, value=Decimal("10")),
    ]
    result = compute_ranks(vals, higher_is_better=True)
    # competition ranking: 1, 1, 3 ; agency_id breaks the order of the tie
    assert result == [(1, 1, 3), (2, 1, 3), (3, 3, 3)]


def test_compute_ranks_empty():
    assert compute_ranks([], higher_is_better=True) == []


# --- refresh_ranks: ordering & direction ------------------------------------


def test_refresh_ranks_higher_is_better(repo):
    pid = _period(repo)
    _put(repo, "ttc", "annual_ridership", pid, "300")
    _put(repo, "stm", "annual_ridership", pid, "100")
    _put(repo, "translink", "annual_ridership", pid, "200")

    refresh_ranks(repo, "annual_ridership", pid)

    rows = _ranks(repo, "annual_ridership", pid, "all")
    by_agency = {r.agency_id: r for r in rows}
    # highest ridership -> rank 1
    assert by_agency[repo.agency_id("ttc")].rank == 1
    assert by_agency[repo.agency_id("translink")].rank == 2
    assert by_agency[repo.agency_id("stm")].rank == 3
    assert all(r.denominator == 3 for r in rows)
    assert all(r.direction == "higher" for r in rows)


def test_refresh_ranks_lower_is_better(repo):
    pid = _period(repo)
    _put(repo, "ttc", "cost_per_rider", pid, "5")
    _put(repo, "stm", "cost_per_rider", pid, "1")
    _put(repo, "translink", "cost_per_rider", pid, "3")

    refresh_ranks(repo, "cost_per_rider", pid)

    by_agency = {r.agency_id: r for r in _ranks(repo, "cost_per_rider", pid, "all")}
    # lowest cost -> rank 1
    assert by_agency[repo.agency_id("stm")].rank == 1
    assert by_agency[repo.agency_id("translink")].rank == 2
    assert by_agency[repo.agency_id("ttc")].rank == 3
    assert all(r.direction == "lower" for r in by_agency.values())


def test_refresh_ranks_neutral_direction(repo):
    pid = _period(repo)
    _put(repo, "ttc", "operating_revenue", pid, "200")
    _put(repo, "stm", "operating_revenue", pid, "100")

    refresh_ranks(repo, "operating_revenue", pid)

    rows = _ranks(repo, "operating_revenue", pid, "all")
    assert all(r.direction == "neutral" for r in rows)
    by_agency = {r.agency_id: r for r in rows}
    assert by_agency[repo.agency_id("ttc")].rank == 1  # higher value first


# --- refresh_ranks: comparable filter & missing period ----------------------


def test_refresh_ranks_excludes_non_comparable(repo):
    pid = _period(repo)
    _put(repo, "ttc", "annual_ridership", pid, "300")
    _put(repo, "stm", "annual_ridership", pid, "200")
    _put(repo, "translink", "annual_ridership", pid, "999", comparable=False)

    refresh_ranks(repo, "annual_ridership", pid)

    rows = _ranks(repo, "annual_ridership", pid, "all")
    agency_ids = {r.agency_id for r in rows}
    # non-comparable translink absent; denominator reflects only the 2 included
    assert repo.agency_id("translink") not in agency_ids
    assert len(rows) == 2
    assert all(r.denominator == 2 for r in rows)


def test_refresh_ranks_missing_agency_absent(repo):
    pid = _period(repo)
    # only ttc and stm have a value for this period; the other 8 agencies do not
    _put(repo, "ttc", "annual_ridership", pid, "300")
    _put(repo, "stm", "annual_ridership", pid, "200")

    refresh_ranks(repo, "annual_ridership", pid)

    rows = _ranks(repo, "annual_ridership", pid, "all")
    assert {r.agency_id for r in rows} == {
        repo.agency_id("ttc"),
        repo.agency_id("stm"),
    }
    assert all(r.denominator == 2 for r in rows)


def test_refresh_ranks_ignores_other_periods(repo):
    """A value in a different period must not leak into this period's ranks."""
    pid = _period(repo)
    other_pid = repo.get_or_create_reporting_period(
        repo.agency_id("ttc"),
        "annual_calendar",
        date(2023, 1, 1),
        date(2023, 12, 31),
        "2023",
    )
    _put(repo, "ttc", "annual_ridership", pid, "300")
    _put(repo, "stm", "annual_ridership", pid, "200")
    # translink only has a 2023 value -> must be absent from 2024 ranks
    _put(repo, "translink", "annual_ridership", other_pid, "999")

    refresh_ranks(repo, "annual_ridership", pid)

    rows = _ranks(repo, "annual_ridership", pid, "all")
    assert repo.agency_id("translink") not in {r.agency_id for r in rows}
    assert len(rows) == 2


# --- refresh_ranks: subdivision grouping ------------------------------------


def test_refresh_ranks_subdivision_groups_isolated(repo):
    pid = _period(repo)
    # ON: ttc, oc-transpo, miway ; AB: calgary-transit, edmonton-ets
    _put(repo, "ttc", "annual_ridership", pid, "300")
    _put(repo, "oc-transpo", "annual_ridership", pid, "100")
    _put(repo, "miway", "annual_ridership", pid, "200")
    _put(repo, "calgary-transit", "annual_ridership", pid, "50")
    _put(repo, "edmonton-ets", "annual_ridership", pid, "80")

    refresh_ranks(repo, "annual_ridership", pid)

    sub_rows = _ranks(repo, "annual_ridership", pid, "subdivision")
    by_agency = {r.agency_id: r for r in sub_rows}

    # Ontario group (3 agencies): ttc 1, miway 2, oc-transpo 3, denom 3
    assert by_agency[repo.agency_id("ttc")].rank == 1
    assert by_agency[repo.agency_id("ttc")].denominator == 3
    assert by_agency[repo.agency_id("miway")].rank == 2
    assert by_agency[repo.agency_id("oc-transpo")].rank == 3

    # Alberta group (2 agencies): edmonton 1, calgary 2, denom 2 -- isolated
    assert by_agency[repo.agency_id("edmonton-ets")].rank == 1
    assert by_agency[repo.agency_id("edmonton-ets")].denominator == 2
    assert by_agency[repo.agency_id("calgary-transit")].rank == 2
    assert by_agency[repo.agency_id("calgary-transit")].denominator == 2


def test_refresh_ranks_writes_both_comparison_sets(repo):
    pid = _period(repo)
    _put(repo, "ttc", "annual_ridership", pid, "300")
    _put(repo, "calgary-transit", "annual_ridership", pid, "100")

    refresh_ranks(repo, "annual_ridership", pid)

    metric_id = repo.metric_id("annual_ridership")
    assert (metric_id, pid, "all") in repo._ranks
    assert (metric_id, pid, "subdivision") in repo._ranks
    # ttc (ON) and calgary (AB) each alone in their subdivision -> rank 1
    sub = {r.agency_id: r for r in repo._ranks[(metric_id, pid, "subdivision")]}
    assert sub[repo.agency_id("ttc")].rank == 1
    assert sub[repo.agency_id("ttc")].denominator == 1
    assert sub[repo.agency_id("calgary-transit")].rank == 1


def test_refresh_ranks_ignores_other_scope(repo):
    """Only the matched service_scope participates (single-scope ranking)."""
    pid = _period(repo)
    _put(repo, "ttc", "annual_ridership", pid, "300", scope="system_wide")
    _put(repo, "stm", "annual_ridership", pid, "200", scope="system_wide")
    # a conventional-scope row for translink must not enter the system_wide rank
    _put(repo, "translink", "annual_ridership", pid, "999", scope="conventional")

    refresh_ranks(repo, "annual_ridership", pid)

    rows = _ranks(repo, "annual_ridership", pid, "all")
    assert repo.agency_id("translink") not in {r.agency_id for r in rows}
    assert len(rows) == 2
