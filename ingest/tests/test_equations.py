"""Tests for the equation graph + pure fixpoint solver (stdlib + pytest)."""

from __future__ import annotations

from decimal import Decimal

from transitindex_ingest.equations import (
    CROSS_SOURCE_DISAGREEMENT,
    EQUATIONS,
    SUM_MISMATCH,
    defining_equation,
    derived_codes,
    display_formula,
    metric_operands,
    solve,
)
from transitindex_ingest.refdata import METRICS


# --- catalog <-> refdata parity ---------------------------------------------


def test_every_derived_metric_has_one_defining_equation():
    refdata_derived = {c for c, m in METRICS.items() if m["is_derived"]}
    assert derived_codes() == refdata_derived
    for code in refdata_derived:
        assert defining_equation(code) is not None


def test_sourced_metrics_are_not_defined_by_any_equation():
    for code, m in METRICS.items():
        if not m["is_derived"]:
            assert defining_equation(code) is None


def test_display_formula_matches_refdata_formula():
    for code, m in METRICS.items():
        if m["is_derived"]:
            assert display_formula(code) == m["formula"]


def test_all_metric_operands_exist_in_refdata():
    for eq in EQUATIONS:
        for op in metric_operands(eq):
            assert op in METRICS, f"{eq.code} references unknown metric {op}"


def test_equation_codes_are_unique():
    codes = [e.code for e in EQUATIONS]
    assert len(codes) == len(set(codes))


# --- forward computation (regression vs the old one-directional job) ---------


def test_forward_ratios_and_backsolved_subsidy():
    # 4 observed sourced inputs -> subsidy back-solved, then all 6 ratios.
    res = solve(
        {
            "operating_revenue": Decimal("2500"),
            "operating_expenses": Decimal("5000"),
            "ridership": Decimal("1000"),
            "revenue_service_hours": Decimal("200"),
        }
    )
    s = res.solved
    assert s["total_operating_subsidy"].value == Decimal("2500")  # expenses - revenue
    assert s["average_fare"].value == Decimal("2.5")  # 2500 / 1000
    assert s["cost_per_hour"].value == Decimal("25")  # 5000 / 200
    assert s["cost_per_rider"].value == Decimal("5")  # 5000 / 1000
    assert s["farebox_recovery_ratio"].value == Decimal("0.5")  # 2500 / 5000
    assert s["subsidy_per_rider"].value == Decimal("2.5")  # 2500 / 1000
    assert s["trips_per_revenue_hour"].value == Decimal("5")  # 1000 / 200
    assert res.flags == []  # subsidy is 'solved' -> its identity is not cross-checked


# --- back-solving (the flagship goal) ---------------------------------------


def test_backsolve_expenses_from_farebox_and_revenue():
    res = solve(
        {
            "operating_revenue": Decimal("2500"),
            "farebox_recovery_ratio": Decimal("0.5"),
        }
    )
    exp = res.solved["operating_expenses"]
    assert exp.value == Decimal("5000")  # 2500 / 0.5
    assert exp.origin == "solved"
    assert exp.equation_code == "farebox_recovery_def"
    # provenance names the exact operands consumed
    assert exp.inputs == ("farebox_recovery_ratio", "operating_revenue")
    assert res.flags == []


def test_chaining_to_fixpoint():
    # farebox + revenue -> expenses; expenses + ridership -> cost_per_rider.
    res = solve(
        {
            "operating_revenue": Decimal("2500"),
            "farebox_recovery_ratio": Decimal("0.5"),
            "ridership": Decimal("1000"),
        }
    )
    assert res.solved["operating_expenses"].value == Decimal("5000")
    cpr = res.solved["cost_per_rider"]
    assert cpr.value == Decimal("5")  # 5000 / 1000, from a SOLVED expenses
    assert cpr.equation_code == "cost_per_rider_def"


def test_observed_value_is_never_overwritten():
    # expenses is sourced AND derivable; it stays observed, never re-solved.
    res = solve(
        {
            "operating_revenue": Decimal("2500"),
            "farebox_recovery_ratio": Decimal("0.5"),
            "operating_expenses": Decimal("5000"),
        }
    )
    assert "operating_expenses" not in res.solved
    assert res.values["operating_expenses"].origin == "observed"


# --- guardrails -------------------------------------------------------------


def test_backsolve_denominator_ridership_from_fare_and_revenue():
    # average_fare = revenue / ridership; back out ridership = revenue / fare.
    res = solve(
        {
            "operating_revenue": Decimal("2500"),
            "average_fare": Decimal("2.5"),
        }
    )
    rid = res.solved["ridership"]
    assert rid.value == Decimal("1000")  # 2500 / 2.5
    assert rid.equation_code == "average_fare_def"


def test_zero_quotient_denominator_solve_is_skipped():
    # farebox = 0 would make expenses = revenue / 0; must be skipped, not raised.
    res = solve(
        {
            "operating_revenue": Decimal("2500"),
            "farebox_recovery_ratio": Decimal("0"),
        }
    )
    assert "operating_expenses" not in res.solved


def test_zero_denominator_is_skipped_not_divided():
    res = solve(
        {
            "operating_revenue": Decimal("2500"),
            "operating_expenses": Decimal("5000"),
            "ridership": Decimal("0"),
            "revenue_service_hours": Decimal("200"),
        }
    )
    # ratios dividing by ridership are skipped (no ZeroDivision, no fabrication)
    assert "average_fare" not in res.solved
    assert "cost_per_rider" not in res.solved
    # ratios with a non-zero denominator still resolve
    assert res.solved["cost_per_hour"].value == Decimal("25")
    assert res.solved["farebox_recovery_ratio"].value == Decimal("0.5")


# --- over-determination & cross-checks --------------------------------------


def test_overdetermination_disagreement_writes_nothing_and_flags():
    # expenses solvable two ways that disagree > 2%: 5300 vs 5000.
    res = solve(
        {
            "operating_revenue": Decimal("2500"),
            "total_operating_subsidy": Decimal("2800"),  # -> 5300
            "labour_cost": Decimal("2000"),
            "energy_fuel_cost": Decimal("1000"),
            "materials_services_cost": Decimal("2000"),  # -> 5000
        }
    )
    assert "operating_expenses" not in res.solved
    assert SUM_MISMATCH in res.flags


def test_overdetermination_agreement_writes_once_deterministically():
    # both paths give 5000; the first equation by sorted code is cited.
    res = solve(
        {
            "operating_revenue": Decimal("2500"),
            "total_operating_subsidy": Decimal("2500"),  # -> 5000
            "labour_cost": Decimal("2000"),
            "energy_fuel_cost": Decimal("1000"),
            "materials_services_cost": Decimal("2000"),  # -> 5000
        }
    )
    exp = res.solved["operating_expenses"]
    assert exp.value == Decimal("5000")
    assert exp.equation_code == "expense_components"  # sorts before expense_revenue_subsidy
    assert SUM_MISMATCH not in res.flags


def test_sum_mismatch_on_inconsistent_observed_components():
    # all observed: components sum 5500 vs sourced expenses 5000 -> sum_mismatch.
    res = solve(
        {
            "operating_expenses": Decimal("5000"),
            "labour_cost": Decimal("1000"),
            "energy_fuel_cost": Decimal("1000"),
            "materials_services_cost": Decimal("3500"),
        }
    )
    assert SUM_MISMATCH in res.flags


def test_cross_source_disagreement_on_published_vs_computed_ratio():
    # published farebox 0.6 vs computed 2500/5000 = 0.5 -> cross_source_disagreement.
    res = solve(
        {
            "farebox_recovery_ratio": Decimal("0.6"),
            "operating_revenue": Decimal("2500"),
            "operating_expenses": Decimal("5000"),
        }
    )
    assert CROSS_SOURCE_DISAGREEMENT in res.flags


def test_no_false_confidence_solved_value_not_cross_checked():
    # subsidy is back-solved from expenses - revenue; the identity that produced
    # it must NOT then 'verify' it (no flag, no green check).
    res = solve(
        {
            "operating_revenue": Decimal("2500"),
            "operating_expenses": Decimal("5000"),
        }
    )
    assert res.solved["total_operating_subsidy"].value == Decimal("2500")
    assert res.flags == []
