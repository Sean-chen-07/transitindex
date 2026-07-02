"""Tests for the solver-based derived recompute job (pure stdlib + pytest)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.jobs.derived_recompute import recompute_derived, weakest_quality


# --- helpers ----------------------------------------------------------------


def _period(repo: InMemoryRepository) -> int:
    return repo.get_or_create_reporting_period(
        "annual_calendar", date(2024, 1, 1), date(2024, 12, 31), "2024"
    )


def _seed(
    repo, period_id, code, value, *, scope="system_wide", quality="verified",
    cost_basis="operating",
) -> int:
    return repo.insert_metric_value(
        agency_id=repo.agency_id("ttc"),
        metric_id=repo.metric_id(code),
        reporting_period_id=period_id,
        mode_id=None,
        service_scope=scope,
        value=Decimal(value),
        unit="x",
        quality=quality,
        cost_basis=cost_basis,
    )


def _current(repo, period_id, code, scope="system_wide"):
    return repo.get_current_metric_value(
        repo.agency_id("ttc"), repo.metric_id(code), period_id, None, scope
    )


# --- forward derivation + provenance ----------------------------------------


def test_recompute_writes_ratios_and_backsolved_subsidy_with_provenance():
    repo = InMemoryRepository()
    pid = _period(repo)
    fb = _seed(repo, pid, "farebox_revenue", "2500")
    _seed(repo, pid, "total_revenue_excluding_subsidy", "2500")
    _seed(repo, pid, "operating_expenses", "5000")
    rid = _seed(repo, pid, "ridership", "1000")
    _seed(repo, pid, "revenue_service_hours", "200")

    res = recompute_derived(repo, "ttc", pid)

    # 6 ratios + back-solved subsidy + total_revenue + other_revenue (residual) = 9.
    assert len(res.ids) == 9
    assert _current(repo, pid, "average_fare").value == Decimal("2.5")  # farebox / ridership
    assert _current(repo, pid, "subsidy_per_rider").value == Decimal("2.5")
    assert _current(repo, pid, "subsidy").value == Decimal("2500")
    # total_revenue = total_revenue_excluding_subsidy + subsidy = 2500 + 2500.
    assert _current(repo, pid, "total_revenue").value == Decimal("5000")

    # average_fare carries provenance: its equation + the exact input value rows.
    # Its numerator is now farebox_revenue (Phase 3), not the broad revenue line.
    af = _current(repo, pid, "average_fare")
    deriv = repo.get_derivation(af.id)
    assert deriv["equation_code"] == "average_fare_def"
    assert set(deriv["input_value_ids"]) == {fb, rid}


def test_sourced_inputs_have_no_derivation():
    repo = InMemoryRepository()
    pid = _period(repo)
    rev = _seed(repo, pid, "total_revenue_excluding_subsidy", "2500")
    recompute_derived(repo, "ttc", pid)
    assert repo.get_derivation(rev) is None  # sourced -> not derived


# --- back-solving via the job (flagship goal) -------------------------------


def test_recompute_backsolves_a_sourced_metric():
    repo = InMemoryRepository()
    pid = _period(repo)
    fbr = _seed(repo, pid, "farebox_revenue", "2500")
    frr = _seed(repo, pid, "farebox_recovery_ratio", "0.5")  # published ratio

    recompute_derived(repo, "ttc", pid)

    exp = _current(repo, pid, "operating_expenses")
    assert exp.value == Decimal("5000")  # back-solved: farebox 2500 / 0.5
    deriv = repo.get_derivation(exp.id)
    assert deriv["equation_code"] == "farebox_recovery_def"
    assert set(deriv["input_value_ids"]) == {fbr, frr}


# --- quality inheritance ----------------------------------------------------


def test_derived_quality_inherits_weakest_input():
    repo = InMemoryRepository()
    pid = _period(repo)
    _seed(repo, pid, "farebox_revenue", "2500", quality="preliminary")
    _seed(repo, pid, "ridership", "1000", quality="verified")

    recompute_derived(repo, "ttc", pid)

    af = _current(repo, pid, "average_fare")
    assert af.quality == "preliminary"  # never stronger than the weakest input


def test_weakest_quality_ordering():
    assert weakest_quality(["verified", "preliminary"]) == "preliminary"
    assert weakest_quality(["verified", "estimated", "preliminary"]) == "estimated"
    assert weakest_quality([]) == "verified"


# --- restatement on corrected input -----------------------------------------


def test_recompute_restates_after_corrected_input():
    repo = InMemoryRepository()
    pid = _period(repo)
    _seed(repo, pid, "farebox_revenue", "2500")
    _seed(repo, pid, "ridership", "1000")
    recompute_derived(repo, "ttc", pid)
    first = _current(repo, pid, "average_fare")
    assert first.value == Decimal("2.5")

    _seed(repo, pid, "farebox_revenue", "3000")  # correction supersedes the old farebox
    recompute_derived(repo, "ttc", pid)
    current = _current(repo, pid, "average_fare")

    assert current.value == Decimal("3")  # 3000 / 1000
    assert current.id != first.id
    assert current.restatement_of_id == first.id
    assert repo._values[first.id].is_current is False
    currents = [
        v
        for v in repo.list_current_values_for_agency_period(repo.agency_id("ttc"), pid)
        if v.metric_id == repo.metric_id("average_fare")
    ]
    assert len(currents) == 1


def test_recompute_is_idempotent():
    repo = InMemoryRepository()
    pid = _period(repo)
    _seed(repo, pid, "farebox_revenue", "2500")
    _seed(repo, pid, "ridership", "1000")
    recompute_derived(repo, "ttc", pid)

    recompute_derived(repo, "ttc", pid)  # re-run, no input change
    currents = [
        v
        for v in repo.list_current_values_for_agency_period(repo.agency_id("ttc"), pid)
        if v.metric_id == repo.metric_id("average_fare")
    ]
    assert len(currents) == 1
    assert currents[0].value == Decimal("2.5")


# --- scope partitioning -----------------------------------------------------


def test_scopes_solve_independently():
    repo = InMemoryRepository()
    pid = _period(repo)
    _seed(repo, pid, "farebox_revenue", "2500", scope="total")
    _seed(repo, pid, "ridership", "1000", scope="total")
    _seed(repo, pid, "farebox_revenue", "6000", scope="system_wide")
    _seed(repo, pid, "ridership", "2000", scope="system_wide")

    recompute_derived(repo, "ttc", pid)

    assert _current(repo, pid, "average_fare", "total").value == Decimal("2.5")
    assert _current(repo, pid, "average_fare", "system_wide").value == Decimal("3")


# --- cost_basis normalization (Phase 3) -------------------------------------


def test_ratios_normalize_psab_expense_with_amortization():
    # Rule (a): a psab_total operating_expenses (5500) with amortization (500) is
    # normalized to the operating basis (5000) before the ratios use it; the
    # result is fully comparable.
    repo = InMemoryRepository()
    pid = _period(repo)
    _seed(repo, pid, "operating_expenses", "5500", cost_basis="psab_total")
    _seed(repo, pid, "amortization", "500")
    _seed(repo, pid, "ridership", "1000")

    res = recompute_derived(repo, "ttc", pid)

    cpr = _current(repo, pid, "cost_per_rider")
    assert cpr.value == Decimal("5")  # (5500 - 500) / 1000, operating basis
    assert cpr.comparable_flag is True  # rated + comparable
    assert not any("mixed_cost_basis" in w for w in res.warnings)


def test_ratios_flag_psab_expense_without_amortization():
    # Rule (b): a psab_total operating_expenses with no amortization to subtract
    # still computes, but the derived ratios are not comparable and are flagged.
    repo = InMemoryRepository()
    pid = _period(repo)
    _seed(repo, pid, "operating_expenses", "5000", cost_basis="psab_total")
    _seed(repo, pid, "ridership", "1000")

    res = recompute_derived(repo, "ttc", pid)

    cpr = _current(repo, pid, "cost_per_rider")
    assert cpr.value == Decimal("5")  # computed anyway (5000 / 1000)
    assert cpr.comparable_flag is False  # not comparable across bases
    assert cpr.notes == "mixed_cost_basis"
    assert any("mixed_cost_basis" in w for w in res.warnings)
    # subsidy_per_rider transitively depends on the tainted expense -> also flagged.
    _seed(repo, pid, "total_revenue_excluding_subsidy", "2500")
    res2 = recompute_derived(repo, "ttc", pid)
    spr = _current(repo, pid, "subsidy_per_rider")
    assert spr.comparable_flag is False
