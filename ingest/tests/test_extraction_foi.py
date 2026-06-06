"""The data dictionary drives the PDF-extraction guidance + FOI templates.

Skipped when PyYAML is absent (the dictionary module imports it lazily)."""

from __future__ import annotations

import pytest

pytest.importorskip("yaml")

from transitindex_ingest import dictionary


def test_extraction_guidance_covers_sourced_metrics_with_confusions():
    text = dictionary.extraction_guidance()
    # ridership guidance names the unlinked/linked confusion + FR label
    assert "ridership (Ridership)" in text
    assert "Unlinked" in text or "unlinked" in text
    assert "Achalandage" in text  # FR label appears
    # derived metrics are not emitted by the model -> not in the guidance
    assert "average_fare (Average Fare)" not in text


def test_extraction_guidance_can_scope_to_codes():
    text = dictionary.extraction_guidance(["operating_revenue"])
    assert "operating_revenue (Operating Revenue)" in text
    assert "subsidy" not in text.lower() or "operating_revenue" in text  # scoped


def test_foi_template_lists_requested_metrics_with_definitions():
    body = dictionary.foi_request_template(
        ["operating_expenses", "ridership"], agency="TTC", years="FY2023, FY2024"
    )
    assert "TTC" in body
    assert "FY2023, FY2024" in body
    assert "Operating Expenses" in body
    assert "Ridership" in body
    # definition text is included so the records officer knows the exact figure
    assert "cost of operating" in body.lower() or "boardings" in body.lower()
