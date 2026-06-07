"""Tests for the rail-weighted fleet_capacity aggregation job + its provenance."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.jobs.fleet_capacity_aggregate import fleet_capacity_aggregate
from transitindex_ingest.refdata import MODE_CAPACITY_WEIGHT


def _period(repo) -> int:
    return repo.get_or_create_reporting_period(
        "annual_calendar", date(2024, 1, 1), date(2024, 12, 31), "2024"
    )


def _fleet(repo, slug, period_id, mode_code, value, *, scope="system_wide", quality="verified"):
    return repo.insert_metric_value(
        agency_id=repo.agency_id(slug),
        metric_id=repo.metric_id("fleet_size"),
        reporting_period_id=period_id,
        mode_id=repo.mode_id(mode_code),
        service_scope=scope,
        value=Decimal(value),
        unit="count",
        quality=quality,
    )


def _capacity(repo, slug, period_id, *, scope="system_wide"):
    return repo.get_current_metric_value(
        repo.agency_id(slug), repo.metric_id("fleet_capacity"), period_id, None, scope
    )


def test_weighted_sum_over_modes_with_provenance():
    repo = InMemoryRepository()
    pid = _period(repo)
    bus = _fleet(repo, "ttc", pid, "bus", "1000")      # weight 1 -> 1000
    sub = _fleet(repo, "ttc", pid, "subway", "100")     # weight 4 -> 400
    sc = _fleet(repo, "ttc", pid, "streetcar", "50")    # weight 2 -> 100

    out = fleet_capacity_aggregate(repo, "ttc", pid)
    assert out.scopes == ["system_wide"]

    cap = _capacity(repo, "ttc", pid)
    assert cap is not None
    assert cap.value == Decimal("1500")  # 1000*1 + 100*4 + 50*2
    assert cap.mode_id is None  # a scope-level aggregate, not a per-mode row

    deriv = repo.get_derivation(cap.id)
    assert deriv["equation_code"] == "mode_weighted_fleet"
    assert set(deriv["input_value_ids"]) == {bus, sub, sc}  # exact per-mode rows cited


def test_null_weight_modes_excluded():
    repo = InMemoryRepository()
    pid = _period(repo)
    _fleet(repo, "translink", pid, "bus", "100")      # weight 1
    _fleet(repo, "translink", pid, "ferry", "5")      # NULL weight -> excluded
    assert "ferry" not in MODE_CAPACITY_WEIGHT

    fleet_capacity_aggregate(repo, "translink", pid)
    cap = _capacity(repo, "translink", pid)
    assert cap.value == Decimal("100")  # ferry not counted
    assert repo.mode_id("ferry") not in repo.get_derivation(cap.id)["input_value_ids"]


def test_never_overwrites_sourced_capacity():
    repo = InMemoryRepository()
    pid = _period(repo)
    _fleet(repo, "ttc", pid, "bus", "1000")
    # A sourced fleet_capacity already present for this scope.
    sourced = repo.insert_metric_value(
        agency_id=repo.agency_id("ttc"),
        metric_id=repo.metric_id("fleet_capacity"),
        reporting_period_id=pid,
        mode_id=None,
        service_scope="system_wide",
        value=Decimal("999"),
        unit="count",
        quality="verified",
    )

    out = fleet_capacity_aggregate(repo, "ttc", pid)
    assert out.value_ids == []  # wrote nothing into the occupied slot

    cap = _capacity(repo, "ttc", pid)
    assert cap.id == sourced and cap.value == Decimal("999")  # untouched
    assert repo.get_derivation(cap.id) is None  # still sourced


def test_partitions_by_service_scope():
    repo = InMemoryRepository()
    pid = _period(repo)
    _fleet(repo, "ttc", pid, "bus", "100", scope="system_wide")
    _fleet(repo, "ttc", pid, "subway", "10", scope="total")  # different scope

    out = fleet_capacity_aggregate(repo, "ttc", pid)
    assert set(out.scopes) == {"system_wide", "total"}
    assert _capacity(repo, "ttc", pid, scope="system_wide").value == Decimal("100")
    assert _capacity(repo, "ttc", pid, scope="total").value == Decimal("40")  # 10*4


def test_quality_inherited_from_weakest_input():
    repo = InMemoryRepository()
    pid = _period(repo)
    _fleet(repo, "ttc", pid, "bus", "100", quality="verified")
    _fleet(repo, "ttc", pid, "subway", "10", quality="estimated")

    fleet_capacity_aggregate(repo, "ttc", pid)
    assert _capacity(repo, "ttc", pid).quality == "estimated"  # weakest wins


def test_idempotent_rerun_supersedes_not_duplicates():
    repo = InMemoryRepository()
    pid = _period(repo)
    _fleet(repo, "ttc", pid, "bus", "100")
    fleet_capacity_aggregate(repo, "ttc", pid)
    # A second run with the SAME inputs writes nothing new (slot already current).
    out2 = fleet_capacity_aggregate(repo, "ttc", pid)
    assert out2.value_ids == []
    assert _capacity(repo, "ttc", pid).value == Decimal("100")
