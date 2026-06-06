"""Balance-sheet family: PSAB identities, ranked ratios, per-capita attribute."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.equations import solve
from transitindex_ingest.jobs.derived_recompute import recompute_derived


# --- pure solver: PSAB identities -------------------------------------------


def test_net_debt_and_assets_and_ratios_solve():
    res = solve(
        {
            "total_liabilities": Decimal("300"),
            "total_financial_assets": Decimal("100"),
            "total_non_financial_assets": Decimal("400"),
        }
    )
    s = res.solved
    assert s["net_debt"].value == Decimal("200")  # 300 - 100
    assert s["total_assets"].value == Decimal("500")  # 100 + 400
    assert s["debt_to_assets"].value == Decimal("0.6")  # 300 / 500
    assert s["accumulated_surplus"].value == Decimal("200")  # 500 - 300
    assert res.flags == []


def test_net_debt_per_capita_uses_population_attribute():
    res = solve(
        {
            "total_liabilities": Decimal("300"),
            "total_financial_assets": Decimal("100"),
            "attr:service_area_population": Decimal("1000"),
        }
    )
    assert res.solved["net_debt"].value == Decimal("200")
    assert res.solved["net_debt_per_capita"].value == Decimal("0.2")  # 200 / 1000


def test_population_is_never_solved_into():
    # net_debt known + per-capita known must NOT back-solve the population attribute.
    res = solve(
        {"net_debt": Decimal("200"), "net_debt_per_capita": Decimal("0.2")}
    )
    assert "attr:service_area_population" not in res.solved
    assert "attr:service_area_population" not in {
        c for c, v in res.values.items() if v.origin == "solved"
    }


# --- repo recompute: comparable_flag + population ---------------------------


def _period(repo):
    return repo.get_or_create_reporting_period(
        "annual_calendar", date(2024, 1, 1), date(2024, 12, 31), "2024"
    )


def _seed(repo, pid, code, value, scope="total"):
    repo.insert_metric_value(
        agency_id=repo.agency_id("ttc"),
        metric_id=repo.metric_id(code),
        reporting_period_id=pid,
        mode_id=None,
        service_scope=scope,
        value=Decimal(value),
        unit="CAD",
        quality="verified",
    )


def test_recompute_balance_sheet_flags_and_population():
    repo = InMemoryRepository()
    pid = _period(repo)
    repo._agency_population[repo.agency_id("ttc")] = Decimal("1000")
    _seed(repo, pid, "total_liabilities", "300")
    _seed(repo, pid, "total_financial_assets", "100")
    _seed(repo, pid, "total_non_financial_assets", "400")

    recompute_derived(repo, "ttc", pid)

    def cur(code):
        return repo.get_current_metric_value(
            repo.agency_id("ttc"), repo.metric_id(code), pid, None, "total"
        )

    net_debt = cur("net_debt")
    assert net_debt.value == Decimal("200")
    assert net_debt.comparable_flag is False  # raw dollar -> never ranked
    assert cur("debt_to_assets").value == Decimal("0.6")
    assert cur("debt_to_assets").comparable_flag is True  # scale-free ratio -> ranked
    ndpc = cur("net_debt_per_capita")
    assert ndpc.value == Decimal("0.2")  # 200 / 1000
    assert ndpc.comparable_flag is True

    # provenance: net_debt_per_capita cites the net_debt value row (population is an
    # attribute, reconstructed from the equation, not a metric_value input).
    deriv = repo.get_derivation(ndpc.id)
    assert deriv["equation_code"] == "net_debt_per_capita_def"
    assert deriv["input_value_ids"] == [net_debt.id]
