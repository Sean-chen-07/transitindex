"""Offline tests for staging + promotion + feed-health recording.

Pure stdlib + pytest, on the InMemoryRepository fixture. We inject validators
explicitly (the project validator may not be on disk yet), so these tests pin
the tier auto-approval rules and the one_current_value invariant end to end.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from transitindex_ingest import promotion, staging
from transitindex_ingest.contract import SourceRef


def _no_flags(record):
    return []


def _always_flags(record):
    return ["yoy_spike"]


def _current(repo, record):
    """The single is_current metric value for `record`'s tuple, or None."""
    return repo.get_current_metric_value(
        repo.agency_id(record.agency_slug),
        repo.metric_id(record.metric_code),
        repo.get_or_create_reporting_period(
            repo.agency_id(record.agency_slug),
            record.period_type,
            record.period_start,
            record.period_end,
            record.period_label,
        ),
        repo.mode_id(record.mode_code),
        record.service_scope,
    )


def test_clean_tier0_auto_approves_and_promotes(repo, sample_record):
    pending_ids = staging.stage_records(
        repo, [sample_record], tier=0, feed_code="statcan_307", validator=_no_flags
    )
    assert len(pending_ids) == 1

    pending = repo.get_pending_value(pending_ids[0])
    assert pending.review_status == "approved"
    assert pending.flags == []
    # Approved but not yet in metric_values until promotion runs.
    assert _current(repo, sample_record) is None

    value_ids = promotion.promote_approved(repo)
    assert len(value_ids) == 1

    current = _current(repo, sample_record)
    assert current is not None
    assert current.value == sample_record.value
    assert current.is_current is True


def test_flagged_tier0_stays_pending_and_never_reaches_values(repo, sample_record):
    """Invariant #1: a flagged tier-0 record is held at 'pending'."""
    pending_ids = staging.stage_records(
        repo, [sample_record], tier=0, feed_code="statcan_307", validator=_always_flags
    )
    pending = repo.get_pending_value(pending_ids[0])
    assert pending.review_status == "pending"
    assert pending.flags == ["yoy_spike"]

    value_ids = promotion.promote_approved(repo)
    assert value_ids == []
    assert _current(repo, sample_record) is None


def test_tier2_never_auto_approves(repo, make_record):
    """Tier 2 (PDF) is always 'pending', even with zero flags."""
    record = make_record(
        source=SourceRef(
            document_type="annual_report",
            extraction_method="manual",
            source_url="https://example.org/ttc-annual-2025.pdf",
            license="public_document",
            page_number=12,
        )
    )
    pending_ids = staging.stage_records(
        repo, [record], tier=2, feed_code="annual_report_pdfs", validator=_no_flags
    )
    pending = repo.get_pending_value(pending_ids[0])
    assert pending.review_status == "pending"

    assert promotion.promote_approved(repo) == []
    assert _current(repo, record) is None


def test_second_promotion_supersedes_first(repo, make_record):
    """Two values for the same tuple: the second supersedes the first."""
    first = make_record(value=Decimal("1000000"))
    second = make_record(value=Decimal("2000000"))

    staging.stage_records(
        repo, [first], tier=0, feed_code="statcan_307", validator=_no_flags
    )
    [first_value_id] = promotion.promote_approved(repo)

    staging.stage_records(
        repo, [second], tier=0, feed_code="statcan_307", validator=_no_flags
    )
    [second_value_id] = promotion.promote_approved(repo)

    assert first_value_id != second_value_id

    current = _current(repo, second)
    assert current.id == second_value_id
    assert current.value == Decimal("2000000")
    assert current.is_current is True
    # Supersede chain: new current points back at the old row.
    assert current.restatement_of_id == first_value_id

    # Exactly one current row for the tuple; the old one is no longer current.
    cohort = repo.list_current_values_for_metric_period(
        current.metric_id, current.reporting_period_id
    )
    assert [v.id for v in cohort] == [second_value_id]


def test_feed_run_recorded(repo, sample_record):
    staging.stage_records(
        repo, [sample_record], tier=0, feed_code="statcan_307", validator=_no_flags
    )
    runs = repo._feed_runs
    assert len(runs) == 1
    assert runs[0]["status"] == "ok"
    assert runs[0]["rows_fetched"] == 1
    assert runs[0]["feed_id"] == repo.feed_id("statcan_307")
