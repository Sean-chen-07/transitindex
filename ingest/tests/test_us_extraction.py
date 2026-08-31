"""Offline tests for the US-agency PDF extraction path (Phase 1: US unblock).

The extraction pipeline was Canada-only in three places: document->agency
resolution iterated the 21-entry `refdata.AGENCIES`, extracted currency values
were stamped "CAD" unconditionally, and the generated US refdata defaulted every
agency to a December fiscal year. These tests pin the fixed behaviour, and that
Canadian agencies are unchanged. No network, no API, no PDF.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from transitindex_ingest.pdf.extract import pages_from_text
from transitindex_ingest.pdf.llm import ExtractedValue, FakeLLMClient, _row_to_value
from transitindex_ingest.pdf.pipeline import SourceRefMeta, run_pdf
from transitindex_ingest.periods import annual_period_from_end_year
from transitindex_ingest.refdata import agency_currency
from transitindex_ingest.review.app import _slug_by_agency_id
from transitindex_ingest.scan import _slug_for_agency_id
from transitindex_ingest.validation import unit_mismatch, validate

# Two real generated US slugs: one calendar-year reporter, one with a June
# fiscal year end (the NTD majority).
US_CALENDAR = "alaska-railroad-corporation-ak"
US_FISCAL_JUNE = "access-services-ca"

PAGES = pages_from_text(["Annual Report — page 1", "Financial statements — page 2"])

META = SourceRefMeta(
    document_type="annual_report",
    title="ACFR",
    source_url="https://example.org/acfr.pdf",
    publication_date=date(2025, 1, 15),
)


def _expense_row(value: str = "88000000") -> dict:
    """One structured-output row as the extraction tool returns it."""
    return {
        "metric_code": "operating_expenses",
        "value": value,
        "period_kind": "annual",
        "period_year": 2024,
        "page_number": 2,
        "confidence": "0.9",
        "source_quote": f"Total operating expenses {value}",
    }


# --- agency/slug resolution over the combined list ---------------------------


def test_us_agency_slug_resolves_from_agency_id(repo):
    """A US document's agency_id maps back to its slug (was Canada-only)."""
    us_id = repo.agency_id(US_FISCAL_JUNE)
    assert _slug_for_agency_id(repo, us_id) == US_FISCAL_JUNE


def test_canadian_agency_slug_resolution_unchanged(repo):
    assert _slug_for_agency_id(repo, repo.agency_id("ttc")) == "ttc"


def test_review_app_slug_map_covers_us_and_canadian_agencies(repo):
    slug_by_id = _slug_by_agency_id(repo)
    assert slug_by_id[repo.agency_id(US_CALENDAR)] == US_CALENDAR
    assert slug_by_id[repo.agency_id("ttc")] == "ttc"


# --- per-agency currency -----------------------------------------------------


def test_agency_currency_is_usd_for_us_and_cad_for_canada():
    assert agency_currency(US_CALENDAR) == "USD"
    assert agency_currency("ttc") == "CAD"
    assert agency_currency("some-unknown-agency") == "CAD"


def test_extracted_value_carries_the_agency_currency():
    """The catalog unit is CAD-denominated; a US extraction redenominates it."""
    assert _row_to_value(_expense_row(), "USD").unit == "USD"
    assert _row_to_value(_expense_row(), "CAD").unit == "CAD"
    assert _row_to_value(_expense_row()).unit == "CAD"  # default unchanged


def test_us_staged_record_stores_usd(repo):
    value = ExtractedValue(
        metric_code="operating_expenses",
        value=Decimal("88000000"),
        unit="USD",
        period_kind="annual",
        period_year=2024,
        page_number=2,
        confidence=Decimal("0.9"),
    )
    (pending_id,) = run_pdf(
        repo,
        PAGES,
        US_CALENDAR,
        source_ref_meta=META,
        llm_client=FakeLLMClient([value]),
    )
    pending = repo.get_pending_value(pending_id)
    assert pending.unit == "USD"
    assert pending.currency == "USD"


def test_canadian_staged_record_still_stores_cad(repo):
    value = ExtractedValue(
        metric_code="operating_expenses",
        value=Decimal("2100000000"),
        unit="CAD",
        period_kind="annual",
        period_year=2024,
        page_number=2,
        confidence=Decimal("0.9"),
    )
    (pending_id,) = run_pdf(
        repo, PAGES, "ttc", source_ref_meta=META, llm_client=FakeLLMClient([value])
    )
    pending = repo.get_pending_value(pending_id)
    assert pending.unit == "CAD"
    assert pending.currency == "CAD"


# --- the flag that used to fire on every US financial value ------------------


def test_usd_value_on_a_us_agency_is_not_flagged(make_record):
    record = make_record(
        agency_slug=US_CALENDAR,
        metric_code="operating_expenses",
        value=Decimal("88000000"),
        unit="USD",
        currency="USD",
    )
    assert unit_mismatch(record) is None


def test_us_extraction_end_to_end_earns_no_unit_mismatch(repo):
    """Tool row -> ExtractedValue -> staged record -> validator, all in USD."""
    value = _row_to_value(_expense_row(), agency_currency(US_CALENDAR))
    (pending_id,) = run_pdf(
        repo,
        PAGES,
        US_CALENDAR,
        source_ref_meta=META,
        llm_client=FakeLLMClient([value]),
        validator=lambda _repo, record: validate(record),
    )
    assert "unit_mismatch" not in repo.get_pending_value(pending_id).flags


def test_cad_value_on_a_us_agency_is_still_flagged(make_record):
    record = make_record(
        agency_slug=US_CALENDAR,
        metric_code="operating_expenses",
        value=Decimal("88000000"),
        unit="CAD",
        currency="CAD",
    )
    assert unit_mismatch(record) == "unit_mismatch"


# --- US fiscal year ends (NTD fy_end_date, not a blanket December) -----------


def test_june_fiscal_year_maps_to_the_year_it_ends_in():
    """FY2024 for a June reporter runs Jul 2023 -> Jun 2024, not Jan-Dec 2024."""
    period = annual_period_from_end_year(US_FISCAL_JUNE, 2024)
    assert period.period_type == "annual_fiscal"
    assert period.start == date(2023, 7, 1)
    assert period.end == date(2024, 6, 30)
    assert period.label == "FY2023-24"


def test_calendar_us_agency_still_maps_to_the_calendar_year():
    period = annual_period_from_end_year(US_CALENDAR, 2024)
    assert period.period_type == "annual_calendar"
    assert period.start == date(2024, 1, 1)
    assert period.end == date(2024, 12, 31)


def test_us_pipeline_period_follows_the_agency_fiscal_year(repo):
    value = ExtractedValue(
        metric_code="ridership",
        value=Decimal("1200000"),
        unit="count",
        period_kind="annual",
        period_year=2024,
        page_number=1,
        confidence=Decimal("0.9"),
    )
    (pending_id,) = run_pdf(
        repo,
        PAGES,
        US_FISCAL_JUNE,
        source_ref_meta=META,
        llm_client=FakeLLMClient([value]),
    )
    period = next(
        p
        for p in repo.list_reporting_periods()
        if p.id == repo.get_pending_value(pending_id).reporting_period_id
    )
    assert (period.start_date, period.end_date) == (date(2023, 7, 1), date(2024, 6, 30))
