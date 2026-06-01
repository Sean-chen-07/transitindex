"""Tests for the derived-ratio recompute job (pure stdlib + pytest)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.jobs.derived_recompute import (
    compute_derived,
    recompute_derived,
)


# --- helpers ----------------------------------------------------------------


def _period(repo: InMemoryRepository, agency_slug: str) -> int:
    """A reporting period to hang the inputs/derived values off of."""
    return repo.get_or_create_reporting_period(
        "annual_calendar",
        date(2024, 1, 1),
        date(2024, 12, 31),
        "2024",
    )


def _seed_input(
    repo: InMemoryRepository,
    agency_slug: str,
    period_id: int,
    code: str,
    value: Decimal,
    scope: str = "system_wide",
) -> None:
    """Seed one current source metric value the job will read as input."""
    repo.insert_metric_value(
        agency_id=repo.agency_id(agency_slug),
        metric_id=repo.metric_id(code),
        reporting_period_id=period_id,
        mode_id=None,
        service_scope=scope,
        value=value,
        unit="x",
        quality="verified",
    )


def _current_value(
    repo: InMemoryRepository, agency_slug: str, period_id: int, code: str, scope: str
) -> Decimal:
    mv = repo.get_current_metric_value(
        repo.agency_id(agency_slug),
        repo.metric_id(code),
        period_id,
        None,
        scope,
    )
    assert mv is not None
    return mv.value


# --- compute_derived: pure math --------------------------------------------


def test_compute_derived_all_ratios():
    inputs = {
        "annual_ridership": Decimal("1000"),
        "operating_revenue": Decimal("2500"),
        "operating_expenses": Decimal("5000"),
        "revenue_service_hours": Decimal("200"),
    }
    out = compute_derived(inputs)

    assert out["average_fare"] == Decimal("2.5")  # 2500 / 1000
    assert out["trips_per_revenue_hour"] == Decimal("5")  # 1000 / 200
    assert out["farebox_recovery_ratio"] == Decimal("0.5")  # 2500 / 5000
    assert out["cost_per_rider"] == Decimal("5")  # 5000 / 1000
    assert out["cost_per_hour"] == Decimal("25")  # 5000 / 200
    assert out["subsidy_per_rider"] == Decimal("2.5")  # (5000 - 2500) / 1000


def test_compute_derived_skips_on_missing_input():
    # No operating_revenue -> average_fare, farebox, subsidy all skipped.
    inputs = {
        "annual_ridership": Decimal("1000"),
        "operating_expenses": Decimal("5000"),
        "revenue_service_hours": Decimal("200"),
    }
    out = compute_derived(inputs)

    assert "average_fare" not in out
    assert "farebox_recovery_ratio" not in out
    assert "subsidy_per_rider" not in out
    # The ones not needing revenue still compute.
    assert out["cost_per_rider"] == Decimal("5")
    assert out["cost_per_hour"] == Decimal("25")
    assert out["trips_per_revenue_hour"] == Decimal("5")


def test_compute_derived_skips_on_zero_denominator():
    inputs = {
        "annual_ridership": Decimal("0"),  # denominator for several ratios
        "operating_revenue": Decimal("2500"),
        "operating_expenses": Decimal("5000"),
        "revenue_service_hours": Decimal("200"),
    }
    out = compute_derived(inputs)

    # Ratios dividing by ridership are skipped, not zero-division errors.
    assert "average_fare" not in out
    assert "cost_per_rider" not in out
    assert "subsidy_per_rider" not in out
    # Ratios with a non-zero denominator still compute.
    assert out["cost_per_hour"] == Decimal("25")
    assert out["farebox_recovery_ratio"] == Decimal("0.5")


# --- recompute_derived: repo-backed ----------------------------------------


def test_recompute_writes_all_six_as_current():
    repo = InMemoryRepository()
    period_id = _period(repo, "ttc")
    _seed_input(repo, "ttc", period_id, "annual_ridership", Decimal("1000"))
    _seed_input(repo, "ttc", period_id, "operating_revenue", Decimal("2500"))
    _seed_input(repo, "ttc", period_id, "operating_expenses", Decimal("5000"))
    _seed_input(repo, "ttc", period_id, "revenue_service_hours", Decimal("200"))

    result = recompute_derived(repo, "ttc", period_id)

    assert len(result.ids) == 6
    assert result.warnings == []
    assert _current_value(repo, "ttc", period_id, "average_fare", "system_wide") == Decimal("2.5")
    assert _current_value(repo, "ttc", period_id, "cost_per_rider", "system_wide") == Decimal("5")
    assert _current_value(
        repo, "ttc", period_id, "farebox_recovery_ratio", "system_wide"
    ) == Decimal("0.5")


def test_recompute_skips_derived_when_input_missing():
    repo = InMemoryRepository()
    period_id = _period(repo, "ttc")
    # No operating_revenue seeded.
    _seed_input(repo, "ttc", period_id, "annual_ridership", Decimal("1000"))
    _seed_input(repo, "ttc", period_id, "operating_expenses", Decimal("5000"))
    _seed_input(repo, "ttc", period_id, "revenue_service_hours", Decimal("200"))

    result = recompute_derived(repo, "ttc", period_id)

    # Revenue-dependent ratios are absent; only 3 written.
    assert len(result.ids) == 3
    assert (
        repo.get_current_metric_value(
            repo.agency_id("ttc"),
            repo.metric_id("average_fare"),
            period_id,
            None,
            "system_wide",
        )
        is None
    )
    assert _current_value(repo, "ttc", period_id, "cost_per_rider", "system_wide") == Decimal("5")


def test_recompute_restates_after_corrected_input():
    repo = InMemoryRepository()
    period_id = _period(repo, "ttc")
    _seed_input(repo, "ttc", period_id, "annual_ridership", Decimal("1000"))
    _seed_input(repo, "ttc", period_id, "operating_revenue", Decimal("2500"))
    _seed_input(repo, "ttc", period_id, "operating_expenses", Decimal("5000"))
    _seed_input(repo, "ttc", period_id, "revenue_service_hours", Decimal("200"))

    recompute_derived(repo, "ttc", period_id)
    first = repo.get_current_metric_value(
        repo.agency_id("ttc"),
        repo.metric_id("average_fare"),
        period_id,
        None,
        "system_wide",
    )
    assert first.value == Decimal("2.5")

    # Correct operating_revenue upward, then recompute.
    _seed_input(repo, "ttc", period_id, "operating_revenue", Decimal("3000"))
    recompute_derived(repo, "ttc", period_id)

    current = repo.get_current_metric_value(
        repo.agency_id("ttc"),
        repo.metric_id("average_fare"),
        period_id,
        None,
        "system_wide",
    )
    # New current ratio reflects the corrected input...
    assert current.value == Decimal("3")  # 3000 / 1000
    assert current.is_current is True
    # ...and supersedes the old one (restatement chain), which is now stale.
    assert current.id != first.id
    assert current.restatement_of_id == first.id
    assert repo._values[first.id].is_current is False

    # Exactly one current average_fare remains -- no stale ratio.
    currents = [
        v
        for v in repo.list_current_values_for_agency_period(repo.agency_id("ttc"), period_id)
        if v.metric_id == repo.metric_id("average_fare")
    ]
    assert len(currents) == 1


def test_recompute_warns_on_farebox_over_100pct():
    repo = InMemoryRepository()
    period_id = _period(repo, "ttc")
    # Revenue exceeds expenses -> farebox_recovery_ratio > 1.0.
    _seed_input(repo, "ttc", period_id, "annual_ridership", Decimal("1000"))
    _seed_input(repo, "ttc", period_id, "operating_revenue", Decimal("6000"))
    _seed_input(repo, "ttc", period_id, "operating_expenses", Decimal("5000"))
    _seed_input(repo, "ttc", period_id, "revenue_service_hours", Decimal("200"))

    result = recompute_derived(repo, "ttc", period_id)

    assert any("farebox_recovery_ratio>1.0" in w for w in result.warnings)
    # Still written, not rejected.
    assert _current_value(
        repo, "ttc", period_id, "farebox_recovery_ratio", "system_wide"
    ) == Decimal("1.2")


def test_recompute_currency_metrics_carry_cad():
    repo = InMemoryRepository()
    period_id = _period(repo, "ttc")
    _seed_input(repo, "ttc", period_id, "annual_ridership", Decimal("1000"))
    _seed_input(repo, "ttc", period_id, "operating_revenue", Decimal("2500"))
    _seed_input(repo, "ttc", period_id, "operating_expenses", Decimal("5000"))
    _seed_input(repo, "ttc", period_id, "revenue_service_hours", Decimal("200"))

    recompute_derived(repo, "ttc", period_id)

    fare = repo.get_current_metric_value(
        repo.agency_id("ttc"),
        repo.metric_id("average_fare"),
        period_id,
        None,
        "system_wide",
    )
    assert fare.currency == "CAD"  # currency-typed derived metric
    tph = repo.get_current_metric_value(
        repo.agency_id("ttc"),
        repo.metric_id("trips_per_revenue_hour"),
        period_id,
        None,
        "system_wide",
    )
    assert tph.currency is None  # ratio-typed derived metric
