"""Proves the NTD adapters, the USD rank basis, and derived-value currency.

Offline + pure stdlib. refdata_us.py ships empty until the seed generator runs
(the NTD portal was unreachable from the build environment), so every test
injects a small synthetic agency map directly: two fake US agencies added to
refdata.ALL_AGENCIES (before the repo seeds itself) and passed to the adapters
as `agency_map`. Covers:

  * monthly: mode x TOS summation, miles->km, Full-Reporter filter, --since
    cutoff, unmapped-id skip path, units/flags/license;
  * annual: mode summation per report year, USD currency, fiscal-year periods;
  * rank refresh: currency cohorts rank on the USD basis (CAD x CAD_TO_USD),
    counts untouched;
  * derived recompute: a US agency's derived dollar values carry USD;
  * bulk load: end-to-end through the in-memory repo, idempotent re-run.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from transitindex_ingest.adapters.ntd_annual import NTD_ANNUAL_URL, NTDAnnualAdapter
from transitindex_ingest.adapters.ntd_monthly import (
    MILES_TO_KM,
    NTD_MONTHLY_URL,
    NTDMonthlyAdapter,
)
from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.jobs.derived_recompute import recompute_derived
from transitindex_ingest.jobs.rank_refresh import refresh_ranks
from transitindex_ingest.refdata import ALL_AGENCIES, CAD_TO_USD

MONTHLY_FIXTURE = Path(__file__).parent / "fixtures" / "ntd_monthly_sample.csv"
ANNUAL_FIXTURE = Path(__file__).parent / "fixtures" / "ntd_annual_sample.csv"

TEST_MAP = {"99901": "test-metro-wa", "99902": "test-city-tx"}


def _us_meta(state: str, ntd_id: str, fy_end: int = 12) -> dict:
    return {
        "subdivision": state,
        "fiscal_year_end_month": fy_end,
        "currency": "USD",
        "country": "US",
        "ntd_id": ntd_id,
        "primary_modes": ("bus",),
    }


@pytest.fixture
def us_agencies(monkeypatch):
    """Two synthetic US agencies visible in ALL_AGENCIES for this test only."""
    monkeypatch.setitem(ALL_AGENCIES, "test-metro-wa", _us_meta("WA", "99901"))
    monkeypatch.setitem(ALL_AGENCIES, "test-city-tx", _us_meta("TX", "99902"))


# --- monthly adapter ---------------------------------------------------------


def _parse_monthly(since="2019-01"):
    adapter = NTDMonthlyAdapter(agency_map=TEST_MAP)
    records = adapter.parse(MONTHLY_FIXTURE.read_text(encoding="utf-8"), since=since)
    return adapter, records


def _one(records, slug, code, start):
    match = [
        r
        for r in records
        if r.agency_slug == slug and r.metric_code == code and r.period_start == start
    ]
    assert len(match) == 1, f"expected 1 record, got {len(match)}"
    return match[0]


def test_monthly_sums_modes_and_tos(us_agencies):
    _, records = _parse_monthly()
    jan = _one(records, "test-metro-wa", "ridership", date(2024, 1, 1))
    # MB/DO 1000 + MB/PT 500 + LR/DO 250 -> one system-wide value.
    assert jan.value == Decimal("1750")
    assert jan.mode_code is None
    assert jan.service_scope == "total"


def test_monthly_record_count(us_agencies):
    # test-metro-wa: Jan (3 metrics) + Feb (3) ; test-city-tx: Jan 2024 (3) = 9.
    _, records = _parse_monthly()
    assert len(records) == 9


def test_monthly_miles_converted_to_km(us_agencies):
    _, records = _parse_monthly()
    vrkm = _one(records, "test-metro-wa", "vehicle_revenue_km", date(2024, 1, 1))
    # 100 + 50 + 25 miles across the three Jan rows.
    assert vrkm.value == Decimal("175") * MILES_TO_KM
    assert vrkm.unit == "km"


def test_monthly_empty_cell_never_a_zero(us_agencies):
    _, records = _parse_monthly()
    vrh = _one(records, "test-metro-wa", "revenue_service_hours", date(2024, 1, 1))
    # The LR row's empty vrh cell is skipped, not counted as 0.
    assert vrh.value == Decimal("15")


def test_monthly_since_cutoff_drops_old_months(us_agencies):
    _, records = _parse_monthly(since="2019-01")
    assert not [r for r in records if r.period_start.year < 2019]
    _, all_records = _parse_monthly(since="2018-01")
    dec18 = _one(all_records, "test-city-tx", "ridership", date(2018, 12, 1))
    assert dec18.value == Decimal("111")


def test_monthly_reduced_reporter_and_unmapped_skipped(us_agencies):
    adapter, records = _parse_monthly()
    slugs = {r.agency_slug for r in records}
    assert slugs == {"test-metro-wa", "test-city-tx"}
    assert [s["ntd_id"] for s in adapter.skipped] == ["99999"]  # 99903 is Reduced


def test_monthly_flags_units_license(us_agencies):
    _, records = _parse_monthly()
    ridership = _one(records, "test-metro-wa", "ridership", date(2024, 1, 1))
    assert ridership.comparable_flag is True  # rated hero metric
    assert ridership.unit == "count"
    assert ridership.currency is None
    assert ridership.quality == "verified"
    assert ridership.source.license == "us_public_domain"
    assert ridership.source.source_url == NTD_MONTHLY_URL
    vrkm = _one(records, "test-metro-wa", "vehicle_revenue_km", date(2024, 1, 1))
    assert vrkm.comparable_flag is False  # not rated


# --- annual adapter ----------------------------------------------------------


def _parse_annual():
    adapter = NTDAnnualAdapter(agency_map=TEST_MAP)
    return adapter, adapter.parse(ANNUAL_FIXTURE.read_text(encoding="utf-8"))


def test_annual_sums_modes_per_year(us_agencies):
    _, records = _parse_annual()
    farebox = [
        r
        for r in records
        if r.agency_slug == "test-metro-wa"
        and r.metric_code == "farebox_revenue"
        and r.period_label == "2023"
    ]
    assert len(farebox) == 1
    assert farebox[0].value == Decimal("1500000")  # MB 1.0M + LR 0.5M
    assert farebox[0].unit == "USD"
    assert farebox[0].currency == "USD"


def test_annual_calendar_period_from_report_year(us_agencies):
    _, records = _parse_annual()
    opex = [
        r
        for r in records
        if r.agency_slug == "test-metro-wa"
        and r.metric_code == "operating_expenses"
        and r.period_label == "2023"
    ]
    assert opex[0].period_type == "annual_calendar"
    assert opex[0].period_start == date(2023, 1, 1)
    assert opex[0].period_end == date(2023, 12, 31)
    assert opex[0].cost_basis == "operating"  # NTD opex excludes depreciation
    assert opex[0].source.license == "us_public_domain"
    assert opex[0].source.source_url == NTD_ANNUAL_URL


def test_annual_fiscal_year_agency_period(monkeypatch):
    # A June-fiscal-year agency: report_year names the END year.
    monkeypatch.setitem(ALL_AGENCIES, "test-fiscal-fl", _us_meta("FL", "99901", fy_end=6))
    adapter = NTDAnnualAdapter(agency_map={"99901": "test-fiscal-fl"})
    records = adapter.parse(ANNUAL_FIXTURE.read_text(encoding="utf-8"))
    r2023 = [r for r in records if "2022-23" in r.period_label and r.metric_code == "ridership"]
    assert len(r2023) == 1
    assert r2023[0].period_type == "annual_fiscal"
    assert r2023[0].period_start == date(2022, 7, 1)
    assert r2023[0].period_end == date(2023, 6, 30)


def test_annual_missing_cells_skipped_not_zero(us_agencies):
    _, records = _parse_annual()
    vrkm_2023 = [
        r
        for r in records
        if r.agency_slug == "test-metro-wa"
        and r.metric_code == "vehicle_revenue_km"
        and r.period_label == "2023"
    ]
    # LR 2023 row has an empty vehicle_revenue_miles cell -> only MB's 1M miles.
    assert vrkm_2023[0].value == Decimal("1000000") * MILES_TO_KM


def test_annual_unmapped_skipped(us_agencies):
    adapter, records = _parse_annual()
    assert {r.agency_slug for r in records} == {"test-metro-wa", "test-city-tx"}
    assert [s["ntd_id"] for s in adapter.skipped] == ["99999"]


# --- rank refresh: USD basis -------------------------------------------------


def _annual_2024(repo):
    return repo.get_or_create_reporting_period(
        "annual_calendar", date(2024, 1, 1), date(2024, 12, 31), "2024"
    )


def _put(repo, slug, code, pid, value, unit="count", currency=None):
    return repo.insert_metric_value(
        agency_id=repo.agency_id(slug),
        metric_id=repo.metric_id(code),
        reporting_period_id=pid,
        mode_id=None,
        service_scope="system_wide",
        value=Decimal(value),
        unit=unit,
        quality="verified",
        comparable_flag=True,
        currency=currency,
    )


def test_currency_rank_converts_cad_to_usd(us_agencies):
    repo = InMemoryRepository()
    pid = _annual_2024(repo)
    # cost_per_rider (lower is better): TTC 10 CAD -> 7 USD basis beats 8 USD.
    # Without the conversion TTC (10 > 8) would lose; with it TTC wins.
    _put(repo, "ttc", "cost_per_rider", pid, "10", unit="CAD", currency="CAD")
    _put(repo, "test-metro-wa", "cost_per_rider", pid, "8", unit="USD", currency="USD")
    assert Decimal("10") * CAD_TO_USD == Decimal("7.0")

    refresh_ranks(repo, "cost_per_rider", pid)

    rows = {r.agency_id: r for r in repo._ranks[(repo.metric_id("cost_per_rider"), pid, "all")]}
    assert rows[repo.agency_id("ttc")].rank == 1
    assert rows[repo.agency_id("test-metro-wa")].rank == 2
    assert all(r.denominator == 2 for r in rows.values())


def test_count_rank_never_converted(us_agencies):
    repo = InMemoryRepository()
    pid = _annual_2024(repo)
    _put(repo, "ttc", "ridership", pid, "100")
    _put(repo, "test-metro-wa", "ridership", pid, "90")

    refresh_ranks(repo, "ridership", pid)

    rows = {r.agency_id: r for r in repo._ranks[(repo.metric_id("ridership"), pid, "all")]}
    assert rows[repo.agency_id("ttc")].rank == 1  # 100 stays 100, no x0.7


def test_subdivision_ranks_group_us_states(us_agencies):
    repo = InMemoryRepository()
    pid = _annual_2024(repo)
    _put(repo, "ttc", "ridership", pid, "100")
    _put(repo, "test-metro-wa", "ridership", pid, "90")
    _put(repo, "test-city-tx", "ridership", pid, "80")

    refresh_ranks(repo, "ridership", pid)

    sub = {r.agency_id: r for r in repo._ranks[(repo.metric_id("ridership"), pid, "subdivision")]}
    # Each agency alone in its subdivision (ON / WA / TX) -> rank 1 of 1.
    for slug in ("ttc", "test-metro-wa", "test-city-tx"):
        assert sub[repo.agency_id(slug)].rank == 1
        assert sub[repo.agency_id(slug)].denominator == 1


# --- derived recompute: agency currency --------------------------------------


def test_derived_values_carry_agency_currency(us_agencies):
    repo = InMemoryRepository()
    pid = _annual_2024(repo)
    _put(repo, "test-metro-wa", "operating_expenses", pid, "8000000", unit="USD", currency="USD")
    _put(repo, "test-metro-wa", "ridership", pid, "1000000")

    result = recompute_derived(repo, "test-metro-wa", pid)

    derived = {repo._values[vid].metric_id: repo._values[vid] for vid in result.ids}
    cpr = derived[repo.metric_id("cost_per_rider")]
    assert cpr.value == Decimal("8")
    assert cpr.unit == "USD"
    assert cpr.currency == "USD"


def test_derived_values_stay_cad_for_canadian_agency(repo):
    pid = _annual_2024(repo)
    _put(repo, "ttc", "operating_expenses", pid, "9000000", unit="CAD", currency="CAD")
    _put(repo, "ttc", "ridership", pid, "1000000")

    result = recompute_derived(repo, "ttc", pid)

    derived = {repo._values[vid].metric_id: repo._values[vid] for vid in result.ids}
    cpr = derived[repo.metric_id("cost_per_rider")]
    assert cpr.unit == "CAD"
    assert cpr.currency == "CAD"


# --- bulk load end-to-end ----------------------------------------------------


@pytest.fixture
def ntd_map(monkeypatch, us_agencies):
    """Point both the adapters' and the loaders' NTD_AGENCY_MAP at TEST_MAP."""
    from transitindex_ingest import refdata_us
    from transitindex_ingest.adapters import ntd_annual, ntd_monthly

    for module in (refdata_us, ntd_monthly, ntd_annual):
        monkeypatch.setattr(module, "NTD_AGENCY_MAP", TEST_MAP)


def test_bulk_load_monthly_end_to_end(ntd_map):
    from transitindex_ingest.jobs.bulk_load import load_ntd_monthly

    repo = InMemoryRepository()
    result = load_ntd_monthly(repo, MONTHLY_FIXTURE)

    assert result.ok
    assert result.records_parsed == 9
    assert result.promoted_inserted == 9
    assert result.records_flagged == 0

    # Idempotent re-run: everything identical, nothing re-promoted.
    again = load_ntd_monthly(repo, MONTHLY_FIXTURE)
    assert again.ok
    assert again.promoted_inserted == 0
    assert again.promoted_skipped == 9


def test_bulk_load_annual_solves_derived_and_ranks(ntd_map):
    from transitindex_ingest.jobs.bulk_load import load_ntd_annual

    repo = InMemoryRepository()
    result = load_ntd_annual(repo, ANNUAL_FIXTURE)

    assert result.ok
    # 2 agencies x (2023: 5 metrics + 5 metrics) + 2024: 5 = 15 sourced records.
    assert result.records_parsed == 15

    # The derived pass produced a ranked cost_per_rider cohort for 2023
    # (both agencies have opex + ridership that year).
    pid_2023 = repo.get_or_create_reporting_period(
        "annual_calendar", date(2023, 1, 1), date(2023, 12, 31), "2023"
    )
    ranks = repo._ranks.get((repo.metric_id("cost_per_rider"), pid_2023, "all"), [])
    assert len(ranks) == 2
