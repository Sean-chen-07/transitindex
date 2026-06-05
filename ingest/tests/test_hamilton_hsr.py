"""Proves the Hamilton HSR adapter: timestamp conversion, ridership values, skip path."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from transitindex_ingest.adapters.hamilton_hsr import HAMILTON_HSR_URL, HamiltonHSRAdapter
from transitindex_ingest.contract import MetricValueRecord

FIXTURE = Path(__file__).parent / "fixtures" / "hamilton_hsr_sample.csv"


def _parse():
    adapter = HamiltonHSRAdapter()
    raw = FIXTURE.read_text(encoding="utf-8")
    return adapter, adapter.parse(raw)


def test_record_count():
    # 3 valid rows; 2 rows with missing/bad data land in skipped.
    _, records = _parse()
    assert len(records) == 3


def test_skipped_count():
    adapter, _ = _parse()
    assert len(adapter.skipped) == 2


def test_all_records_valid():
    _, records = _parse()
    assert all(isinstance(r, MetricValueRecord) for r in records)


def test_agency_slug():
    _, records = _parse()
    assert all(r.agency_slug == "hamilton-street-railway" for r in records)


def test_metric_code():
    _, records = _parse()
    assert all(r.metric_code == "monthly_ridership" for r in records)


def test_timestamp_to_period():
    # 1388552400000 ms = 2014-01-01 05:00 UTC (midnight EST) → Jan 2014 period.
    _, records = _parse()
    jan = _one(records, date(2014, 1, 1))
    assert jan.period_type == "monthly"
    assert jan.period_start == date(2014, 1, 1)
    assert jan.period_end == date(2014, 1, 31)
    assert jan.period_label == "Jan 2014"


def test_ridership_value():
    _, records = _parse()
    jan = _one(records, date(2014, 1, 1))
    assert jan.value == Decimal("1912337")
    assert jan.unit == "count"
    assert jan.currency is None


def test_source_provenance():
    _, records = _parse()
    r = records[0]
    assert r.source.document_type == "open_data_csv"
    assert r.source.extraction_method == "structured_import"
    assert r.source.license == "ogl_hamilton"
    assert r.source.source_url == HAMILTON_HSR_URL
    assert r.source.confidence == Decimal("1.0")


def test_quality_verified():
    _, records = _parse()
    assert all(r.quality == "verified" for r in records)


def test_service_scope_total():
    _, records = _parse()
    assert all(r.service_scope == "total" for r in records)


def test_skipped_reset_between_parses():
    adapter = HamiltonHSRAdapter()
    raw = FIXTURE.read_text(encoding="utf-8")
    adapter.parse(raw)
    adapter.parse(raw)
    assert len(adapter.skipped) == 2  # not 4 — reset each call


def _one(records, start: date) -> MetricValueRecord:
    matches = [r for r in records if r.period_start == start]
    assert len(matches) == 1, f"expected 1 record for {start}, got {len(matches)}"
    return matches[0]
