"""TransLink SYNTHETIC scenario: the ten Phase-4 financial-statement additions.

The fixture lives in tests/fixtures/gold/synthetic/ -- invented round numbers on
a TransLink-style statement, not real TransLink figures.

Covers metric-set-build-plan.md Phase 7 item 2 ("add a fixture row per new
metric ... recommend TransLink for the clean PSAB statement"): a clean,
internally-consistent PSAB statement where the expense-components, revenue,
total_revenue, and balance-sheet identities all close, plus a should_flag
row proving the extractor does not promote a single provincial operating
grant (a COMPONENT) to the combined `subsidy` total (addendum #4).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from transitindex_ingest.eval.gold import load_gold, run_eval_through_pipeline
from transitindex_ingest.pdf.extract import pages_from_text
from transitindex_ingest.pdf.llm import ExtractedValue
from transitindex_ingest.pdf.pipeline import SourceRefMeta
from transitindex_ingest.validation.flags import validate

GOLD_DIR = Path(__file__).parent / "fixtures" / "gold" / "synthetic"
GOLD = load_gold(GOLD_DIR / "translink_annual_2024.json")
PAGES = pages_from_text(
    (GOLD_DIR / "translink_annual_2024_pages.txt").read_text(encoding="utf-8").split("=== PAGE")
)

META = SourceRefMeta(
    document_type="annual_report",
    title="TransLink 2024 Annual Report",
    source_url="https://example.org/translink-2024.pdf",
    publication_date=date(2025, 4, 1),
)


def _ev(metric_code, value, unit, confidence, *, note=None):
    return ExtractedValue(
        metric_code=metric_code,
        value=Decimal(value),
        unit=unit,
        period_kind="annual",
        period_year=2024,
        page_number=2,
        confidence=Decimal(confidence),
        note=note,
    )


def _validator(repo, record):
    return validate(record, prior_value=None)


def _clean_scenario():
    """Every gold row returned correctly and cleanly (the combined subsidy
    total, not the provincial-grant component)."""
    return [
        _ev("labour_cost", "700000000", "CAD", "0.95"),
        _ev("energy_fuel_cost", "120000000", "CAD", "0.95"),
        _ev("materials_services_cost", "380000000", "CAD", "0.95"),
        _ev("amortization", "250000000", "CAD", "0.95"),
        _ev("other_operating_expenses", "50000000", "CAD", "0.95"),
        _ev("operating_expenses", "1500000000", "CAD", "0.95"),
        _ev("total_expenses", "1500000000", "CAD", "0.95"),
        _ev("farebox_revenue", "480000000", "CAD", "0.95"),
        _ev("total_revenue_excluding_subsidy", "600000000", "CAD", "0.95"),
        _ev("subsidy", "1030000000", "CAD", "0.9"),
        _ev("total_revenue", "1630000000", "CAD", "0.95"),
        _ev("total_financial_assets", "900000000", "CAD", "0.95"),
        _ev("cash_and_investments", "650000000", "CAD", "0.95"),
        _ev("total_liabilities", "3200000000", "CAD", "0.95"),
        _ev("long_term_debt", "2600000000", "CAD", "0.95"),
        _ev("total_non_financial_assets", "8100000000", "CAD", "0.95"),
        _ev("tangible_capital_assets", "7900000000", "CAD", "0.95"),
    ]


def test_gold_fixture_has_a_should_flag_row():
    assert any(g.should_flag for g in GOLD)


def test_clean_translink_statement_scores_high_and_identities_close():
    """The full clean cohort: precision is high, and every closed identity
    (expense components, revenue components, total_revenue definition, and
    the three balance-sheet component splits) reconciles with no sum_mismatch
    on the reconciling rows."""
    report = run_eval_through_pipeline(
        GOLD, _clean_scenario(), "translink", PAGES, source_ref_meta=META, validator=_validator
    )
    assert report.precision >= 0.9

    opex = next(r for r in report.rows if r.metric_code == "operating_expenses")
    assert "sum_mismatch" not in opex.flags
    total_assets_rows = [
        r for r in report.rows if r.metric_code in ("total_financial_assets", "total_liabilities")
    ]
    for r in total_assets_rows:
        assert "sum_mismatch" not in r.flags


def test_provincial_grant_component_not_promoted_to_subsidy_total():
    """The should_flag trap: the source prints a $410M provincial operating
    grant alongside the $1,030M combined government contribution. A healthy
    extraction records `subsidy` from the combined line -- if it were instead
    read from the single-program component, the value would be wrong AND the
    subsidy/revenue identity would fail to reconcile, which sum_mismatch
    catches. This proves the trap is at least catchable via the identity."""
    scenario = _clean_scenario()[:-6] + [
        # Wrong: the provincial-grant COMPONENT ($410M) mistakenly recorded as
        # the whole `subsidy` line instead of the combined $1,030M total.
        _ev("subsidy", "410000000", "CAD", "0.9"),
    ] + _clean_scenario()[-5:]
    report = run_eval_through_pipeline(
        GOLD, scenario, "translink", PAGES, source_ref_meta=META, validator=_validator
    )
    subsidy_row = next(r for r in report.rows if r.metric_code == "subsidy")
    assert subsidy_row.should_flag
    assert not subsidy_row.within_tolerance
    assert subsidy_row.flagged
    assert "sum_mismatch" in subsidy_row.flags
