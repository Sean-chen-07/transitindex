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


def test_generate_markdown_is_deterministic():
    first = dictionary.generate_markdown()
    second = dictionary.generate_markdown()
    assert first == second
    assert "# TransitIndex — Data Dictionary" in first
    # every metric's display name appears
    for meta_code, meta in METRICS.items():
        assert f"`{meta_code}`" in first
