"""Offline tests for the Tier 2 PDF -> pending pipeline.

Driven with FakeLLMClient + pre-extracted page text: no real PDF, no Anthropic
API, no creds. Asserts the core invariant (Tier 2 only ever stages 'pending',
never reaches metric_values), the low-confidence flagging, metric/period
mapping, French number parsing, and validator-flag merging. The real-I/O paths
(pdfplumber, anthropic) are guarded with pytest.importorskip so the suite stays
green without those deps.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from transitindex_ingest.pdf.extract import pages_from_text
from transitindex_ingest.pdf.llm import (
    EXTRACTION_SYSTEM_PROMPT,
    ExtractedValue,
    FakeLLMClient,
    LLMClient,
    parse_number,
)
from transitindex_ingest.pdf.pipeline import SourceRefMeta, run_pdf

PAGES = pages_from_text(
    ["TTC Annual Report 2024 — page 1", "Statistics — page 2", "Notes — page 3"]
)

META = SourceRefMeta(
    document_type="annual_report",
    title="TTC 2024 Annual Report",
    source_url="https://example.org/ttc-2024.pdf",
    publication_date=date(2025, 4, 1),
    archive_uri="s3://archive/ttc-2024.pdf",
)


def _run(repo, values, validator=None):
    return run_pdf(
        repo,
        PAGES,
        "ttc",
        source_ref_meta=META,
        llm_client=FakeLLMClient(values),
        validator=validator,
    )


# --- the core invariant: pending only, never metric_values ------------------


def test_values_land_as_pending_and_never_reach_metric_values(repo):
    values = [
        ExtractedValue(
            metric_code="ridership",
            value=Decimal("250000000"),
            unit="count",
            period_kind="annual",
            period_year=2024,
            page_number=2,
            confidence=Decimal("0.95"),
        ),
        ExtractedValue(
            metric_code="operating_expenses",
            value=Decimal("2100000000"),
            unit="CAD",
            period_kind="annual",
            period_year=2024,
            page_number=2,
            confidence=Decimal("0.9"),
        ),
    ]
    pending_ids = _run(repo, values)

    assert len(pending_ids) == 2
    pending = repo.list_pending_values()
    assert {p.id for p in pending} == set(pending_ids)
    assert all(p.review_status == "pending" for p in pending)

    # Invariant #1: nothing was promoted -- no metric_values, no audit entries.
    metric_id = repo.metric_id("ridership")
    period_id = repo.get_or_create_reporting_period(
        "annual_calendar", date(2024, 1, 1), date(2024, 12, 31), "2024"
    )
    assert repo.list_current_values_for_metric_period(metric_id, period_id) == []
    assert repo.iter_audit() == []


def test_extraction_method_and_provenance_recorded(repo):
    values = [
        ExtractedValue(
            metric_code="fleet_size",
            value=Decimal("2000"),
            unit="count",
            period_kind="annual",
            period_year=2024,
            page_number=3,
            confidence=Decimal("0.88"),
        )
    ]
    (pid,) = _run(repo, values)
    p = repo.get_pending_value(pid)
    assert p.extraction_method == "llm_assisted"
    assert p.page_number == 3
    assert p.confidence == Decimal("0.88")
    assert p.source_document_id is not None


# --- metric / period mapping ------------------------------------------------


def test_annual_calendar_period_mapping(repo):
    values = [
        ExtractedValue(
            metric_code="operating_revenue",
            value=Decimal("1300000000"),
            unit="CAD",
            period_kind="annual",
            period_year=2024,
            page_number=2,
            confidence=Decimal("0.9"),
        )
    ]
    (pid,) = _run(repo, values)
    p = repo.get_pending_value(pid)

    assert p.metric_id == repo.metric_id("operating_revenue")
    assert p.service_scope == "total"
    assert p.quality == "preliminary"
    assert p.currency == "CAD"
    # ttc fiscal_year_end_month == 12 -> annual_calendar, Jan1..Dec31, label '2024'
    period = repo.get_or_create_reporting_period(
        "annual_calendar", date(2024, 1, 1), date(2024, 12, 31), "2024"
    )
    assert p.reporting_period_id == period


def test_fiscal_year_period_mapping_for_metrolinx():
    from transitindex_ingest.db.memory import InMemoryRepository

    repo = InMemoryRepository()
    values = [
        ExtractedValue(
            metric_code="ridership",
            value=Decimal("70000000"),
            unit="count",
            period_kind="annual",
            period_year=2024,
            page_number=1,
            confidence=Decimal("0.9"),
        )
    ]
    (pid,) = run_pdf(
        repo,
        PAGES,
        "metrolinx",
        source_ref_meta=META,
        llm_client=FakeLLMClient(values),
    )
    p = repo.get_pending_value(pid)
    # metrolinx FYE month 3, and the extractor names a fiscal year by the year it
    # ENDS in: period_year=2024 is "fiscal year ending March 2024" = Apr 2023 ->
    # Mar 2024, label 'FY2023-24' (NOT FY2024-25 -- that off-by-one was the bug).
    period = repo.get_or_create_reporting_period(
        "annual_fiscal",
        date(2023, 4, 1),
        date(2024, 3, 31),
        "FY2023-24",
    )
    assert p.reporting_period_id == period


def test_monthly_period_mapping(repo):
    values = [
        ExtractedValue(
            metric_code="ridership",
            value=Decimal("21000000"),
            unit="count",
            period_kind="monthly",
            period_year=2026,
            period_month=3,
            page_number=2,
            confidence=Decimal("0.9"),
        )
    ]
    (pid,) = _run(repo, values)
    p = repo.get_pending_value(pid)
    period = repo.get_or_create_reporting_period(
        "monthly", date(2026, 3, 1), date(2026, 3, 31), "Mar 2026"
    )
    assert p.reporting_period_id == period


# --- low-confidence flagging ------------------------------------------------


def test_low_confidence_value_is_flagged_but_still_pending(repo):
    values = [
        ExtractedValue(
            metric_code="on_time_performance",
            value=Decimal("82.5"),
            unit="%",
            period_kind="annual",
            period_year=2024,
            page_number=2,
            confidence=Decimal("0.4"),  # below 0.7
        )
    ]
    (pid,) = _run(repo, values)
    p = repo.get_pending_value(pid)
    assert "low_confidence" in p.flags
    assert p.review_status == "pending"


def test_high_confidence_value_has_no_low_confidence_flag(repo):
    values = [
        ExtractedValue(
            metric_code="on_time_performance",
            value=Decimal("82.5"),
            unit="%",
            period_kind="annual",
            period_year=2024,
            page_number=2,
            confidence=Decimal("0.95"),
        )
    ]
    (pid,) = _run(repo, values)
    assert "low_confidence" not in repo.get_pending_value(pid).flags


# --- validator integration --------------------------------------------------


def test_validator_flags_are_merged(repo):
    def validator(repo, record):
        return ["yoy_spike"]

    values = [
        ExtractedValue(
            metric_code="ridership",
            value=Decimal("999999999"),
            unit="count",
            period_kind="annual",
            period_year=2024,
            page_number=2,
            confidence=Decimal("0.5"),  # low -> both flags expected
        )
    ]
    (pid,) = _run(repo, values, validator=validator)
    flags = repo.get_pending_value(pid).flags
    assert "yoy_spike" in flags
    assert "low_confidence" in flags


# --- French / Canadian number parsing ---------------------------------------


def test_parse_number_handles_french_thousands_and_decimal():
    assert parse_number("1 234 567") == Decimal("1234567")
    assert parse_number("12,5") == Decimal("12.5")
    assert parse_number("250000000") == Decimal("250000000")
    assert parse_number(Decimal("42")) == Decimal("42")


def test_french_formatted_value_parses_through_a_fake_client(repo):
    # A client that parses raw strings the way the real tool-output path does.
    class FrenchClient:
        def extract(self, system_prompt, document_text, agency_slug):
            return [
                ExtractedValue(
                    metric_code="ridership",
                    value=parse_number("1 234 567"),
                    unit="count",
                    period_kind="annual",
                    period_year=2024,
                    page_number=2,
                    confidence=Decimal("0.9"),
                )
            ]

    assert isinstance(FrenchClient(), LLMClient)
    (pid,) = run_pdf(
        repo, PAGES, "stm", source_ref_meta=META, llm_client=FrenchClient()
    )
    assert repo.get_pending_value(pid).value == Decimal("1234567")


# --- misc contract checks ---------------------------------------------------


def test_unknown_agency_fails_fast(repo):
    with pytest.raises(ValueError):
        run_pdf(
            repo,
            PAGES,
            "not-a-real-agency",
            source_ref_meta=META,
            llm_client=FakeLLMClient([]),
        )


def test_extraction_tool_enum_locked_to_sourced_metrics():
    """The tool's metric_code enum IS the non-derived METRICS set -- exactly.

    This locks the extractor to the published metric set: adding/removing a
    metric in refdata.METRICS updates the enum automatically, and any drift
    (a hand-edited enum, a derived code sneaking in) fails here.
    """
    from transitindex_ingest.pdf.llm import EXTRACTION_TOOL
    from transitindex_ingest.refdata import METRICS

    enum = EXTRACTION_TOOL["input_schema"]["properties"]["values"]["items"][
        "properties"
    ]["metric_code"]["enum"]
    assert enum == [code for code, m in METRICS.items() if not m["is_derived"]]


def test_notes_combine_note_label_and_quote_in_order():
    """The reviewer note joins note, printed_label, and source_quote with ' | '.

    Pins the assembled string so the audit-trail format (used by reviewers to
    locate a figure on the page) can't silently regress.
    """
    from transitindex_ingest.pdf.pipeline import _notes_for

    ev = ExtractedValue(
        metric_code="total_assets",
        value=Decimal("100"),
        unit="CAD",
        period_kind="annual",
        period_year=2024,
        page_number=12,
        confidence=Decimal("0.9"),
        note="restated",
        printed_label="Total assets",
        source_quote="Total assets 100,000",
    )
    assert _notes_for(ev) == (
        'restated | label: "Total assets" | quote: "Total assets 100,000"'
    )


def test_notes_are_none_when_nothing_to_record():
    from transitindex_ingest.pdf.pipeline import _notes_for

    ev = ExtractedValue(
        metric_code="ridership",
        value=Decimal("100"),
        unit="count",
        period_kind="annual",
        period_year=2024,
        page_number=1,
        confidence=Decimal("0.9"),
    )
    assert _notes_for(ev) is None


def test_notes_label_only_when_note_and_quote_absent():
    from transitindex_ingest.pdf.pipeline import _notes_for

    ev = ExtractedValue(
        metric_code="net_debt",
        value=Decimal("50"),
        unit="CAD",
        period_kind="annual",
        period_year=2024,
        page_number=8,
        confidence=Decimal("0.9"),
        printed_label="Net debt",
    )
    assert _notes_for(ev) == 'label: "Net debt"'


def test_system_prompt_lists_sourced_codes_and_demands_low_confidence():
    assert "ridership" in EXTRACTION_SYSTEM_PROMPT
    assert "operating_expenses" in EXTRACTION_SYSTEM_PROMPT
    # Derived metric must NOT be in the allowed set.
    assert "average_fare" not in EXTRACTION_SYSTEM_PROMPT
    assert "0.7" in EXTRACTION_SYSTEM_PROMPT  # explicit low-confidence instruction
    assert "record_metrics" in EXTRACTION_SYSTEM_PROMPT


def test_fake_client_satisfies_protocol():
    assert isinstance(FakeLLMClient([]), LLMClient)


# --- real-I/O paths: only run when their deps exist -------------------------


def test_extract_pages_requires_pdfplumber(tmp_path):
    pytest.importorskip("pdfplumber")
    from transitindex_ingest.pdf.extract import extract_pages

    # No real PDF on disk offline; just prove the symbol is importable when the
    # dep is present. Opening a non-PDF should raise, not silently pass.
    with pytest.raises(Exception):
        extract_pages(tmp_path / "missing.pdf")


def test_anthropic_client_constructs_when_sdk_present():
    pytest.importorskip("anthropic")
    from transitindex_ingest.pdf.llm import AnthropicLLMClient

    # Construction must not make a network call (only when a key is provided).
    client = AnthropicLLMClient(api_key="sk-test-not-real")
    assert isinstance(client, LLMClient)
