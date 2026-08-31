"""Tests for the YAML data dictionary loader + generator.

Skipped wholesale when PyYAML is absent (the dictionary module imports it
lazily, so the rest of the package still works without it).
"""

from __future__ import annotations

import pytest

pytest.importorskip("yaml")

from transitindex_ingest import dictionary
from transitindex_ingest.equations import display_formula
from transitindex_ingest.refdata import METRICS


def test_dictionary_parity_with_refdata():
    specs = dictionary.load_dictionary()
    assert set(specs) == set(METRICS)  # one entry per metric, no extras


def test_specs_preserve_refdata_order():
    specs = dictionary.load_dictionary()
    assert list(specs) == list(METRICS)


def test_structural_fields_come_from_catalog_not_yaml():
    specs = dictionary.load_dictionary()
    for code, s in specs.items():
        assert s.unit == METRICS[code]["unit"]
        assert s.is_derived == METRICS[code]["is_derived"]
        assert s.formula == display_formula(code)  # None for sourced metrics


def test_required_fields_present_and_nonempty():
    specs = dictionary.load_dictionary()
    for code, s in specs.items():
        assert s.display_name and s.plain_meaning and s.definition and s.is_not
        assert s.source_tier in dictionary.SOURCE_TIERS


def test_derived_metrics_are_tier_derived():
    specs = dictionary.load_dictionary()
    for code, s in specs.items():
        if s.is_derived:
            assert s.source_tier == "derived"


def test_equations_participation_is_populated_for_linked_metrics():
    specs = dictionary.load_dictionary()
    # operating_expenses links into both income-statement identities + 3 ratios.
    assert "expense_components" in specs["operating_expenses"].equations
    assert "farebox_recovery_def" in specs["operating_expenses"].equations
    # a fleet metric participates in no equation
    assert specs["fleet_size"].equations == ()


def test_validate_dictionary_clean():
    raw = dictionary._load_yaml()
    assert dictionary.validate_dictionary(raw) == []


# --- statement assignment ----------------------------------------------------

INCOME_STATEMENT_METRICS = {
    "farebox_revenue",
    "other_revenue",
    "subsidy",
    "total_revenue",
    "total_revenue_excluding_subsidy",
    "labour_cost",
    "energy_fuel_cost",
    "materials_services_cost",
    "other_operating_expenses",
    "operating_expenses",
    "amortization",
    "total_expenses",
    "annual_surplus_deficit",
    "capital_expenditure",
}

BALANCE_SHEET_METRICS = {
    "cash_and_investments",
    "total_financial_assets",
    "other_financial_assets",
    "long_term_debt",
    "total_liabilities",
    "other_liabilities",
    "net_debt",
    "tangible_capital_assets",
    "total_non_financial_assets",
    "other_non_financial_assets",
    "total_assets",
    "accumulated_surplus",
}


def test_every_metric_has_a_valid_statement():
    specs = dictionary.load_dictionary()
    for code, s in specs.items():
        assert s.statement in dictionary.STATEMENTS, code


def test_financial_statement_metric_sets_are_exactly_as_specified():
    specs = dictionary.load_dictionary()
    by_statement = {
        st: {c for c, s in specs.items() if s.statement == st}
        for st in dictionary.STATEMENTS
    }
    assert by_statement["income_statement"] == INCOME_STATEMENT_METRICS
    assert by_statement["balance_sheet"] == BALANCE_SHEET_METRICS
    # everything else is a service metric; the three groups partition the catalog
    assert by_statement["service"] == (
        set(METRICS) - INCOME_STATEMENT_METRICS - BALANCE_SHEET_METRICS
    )


def test_metrics_for_statement_matches_specs_and_keeps_catalog_order():
    specs = dictionary.load_dictionary()
    for st in dictionary.STATEMENTS:
        codes = dictionary.metrics_for_statement(st)
        assert set(codes) == {c for c, s in specs.items() if s.statement == st}
        assert list(codes) == [c for c in METRICS if c in set(codes)]


def test_metrics_for_statement_rejects_unknown_statement():
    with pytest.raises(ValueError):
        dictionary.metrics_for_statement("cash_flow")


# --- statement-level vocabulary ----------------------------------------------


def test_statements_section_parses_with_names_and_cues():
    statements = dictionary.load_statements()
    assert set(statements) == set(dictionary.FINANCIAL_STATEMENTS)
    for code, st in statements.items():
        assert st.code == code
        assert st.display_name
        assert st.names_en and st.names_fr
        assert st.cues, code
        assert st.never_extract
        assert st.notes
        assert all(c == c.lower() for c in st.cues)  # router matches lowercased text


def test_statement_names_include_the_canonical_titles():
    statements = dictionary.load_statements()
    income = statements["income_statement"]
    balance = statements["balance_sheet"]
    assert "Statement of Operations" in income.names_en
    assert "Statement of Revenues, Expenses and Changes in Net Position" in income.names_en
    assert "État des résultats" in income.names_fr
    assert "Statement of Financial Position" in balance.names_en
    assert "Balance Sheet" in balance.names_en
    assert "Statement of Net Position" in balance.names_en
    assert "État de la situation financière" in balance.names_fr


# --- filtered extraction guidance --------------------------------------------


def test_extraction_guidance_unfiltered_is_unchanged_for_existing_callers():
    # existing callers pass nothing; the two spellings must be byte-identical
    assert dictionary.extraction_guidance() == dictionary.extraction_guidance(None, None)
    text = dictionary.extraction_guidance()
    assert "- ridership (" in text
    assert "- total_liabilities (" in text


def test_extraction_guidance_filtered_covers_only_that_statement():
    specs = dictionary.load_dictionary()
    for st in dictionary.FINANCIAL_STATEMENTS:
        text = dictionary.extraction_guidance(statement=st)
        for code, s in specs.items():
            if s.is_derived:
                continue  # never in the default canon
            marker = f"- {code} ("
            assert (marker in text) is (s.statement == st), (st, code)


def test_extraction_guidance_rejects_unknown_statement():
    with pytest.raises(ValueError):
        dictionary.extraction_guidance(statement="cash_flow")


def test_financial_lines_carry_us_and_french_label_variants():
    specs = dictionary.load_dictionary()
    assert "Depreciation" in specs["amortization"].labels_en
    assert "Net position" in specs["accumulated_surplus"].labels_en
    assert "Capital assets, net of accumulated depreciation" in (
        specs["tangible_capital_assets"].labels_en
    )
    assert "Personnel services" in specs["labour_cost"].labels_en
    assert "Operating assistance" in specs["subsidy"].labels_en
    assert "Passenger revenue" in specs["farebox_revenue"].labels_en
    assert "Total revenue excluding subsidies" in (
        specs["total_revenue_excluding_subsidy"].labels_en
    )
    assert "Dette nette" in specs["net_debt"].labels_fr
    assert "Immobilisations corporelles" in specs["tangible_capital_assets"].labels_fr
    # every financial line carries EN + FR variants and at least one trap
    for code, s in specs.items():
        if s.statement == "service":
            continue
        assert s.labels_en and s.labels_fr, code
        assert s.confusions, code


def test_generate_markdown_is_deterministic():
    first = dictionary.generate_markdown()
    second = dictionary.generate_markdown()
    assert first == second
    assert "# TransitIndex — Data Dictionary" in first
    # every metric's display name appears
    for meta_code, meta in METRICS.items():
        assert f"`{meta_code}`" in first
