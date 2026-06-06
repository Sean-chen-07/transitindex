"""Proves the value contract: construction, enum validation, typing, round-trip.

This is the TODOS-P2 guarantee that MetricValueRecord/SourceRef are stable and
self-validating.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from transitindex_ingest.contract import MetricValueRecord, SourceRef


def test_record_constructs_and_types(sample_record):
    rec = sample_record
    assert isinstance(rec.value, Decimal)
    assert isinstance(rec.period_start, date)
    assert isinstance(rec.period_end, date)
    assert rec.mode_code is None
    assert rec.comparable_flag is True
    assert rec.flags == []


def test_value_coerced_to_decimal(make_record):
    # int and str inputs become Decimal; floats route through str safely.
    assert make_record(value=42).value == Decimal("42")
    assert make_record(value="3.50").value == Decimal("3.50")
    assert make_record(value=3.5).value == Decimal("3.5")


def test_bad_enum_values_rejected(make_record):
    with pytest.raises(ValueError):
        make_record(period_type="weekly")
    with pytest.raises(ValueError):
        make_record(service_scope="everything")
    with pytest.raises(ValueError):
        make_record(quality="guessed")


def test_bad_period_bounds_rejected(make_record):
    with pytest.raises(ValueError):
        make_record(period_start=date(2026, 4, 1), period_end=date(2026, 3, 31))


def test_bool_value_rejected(make_record):
    with pytest.raises(ValueError):
        make_record(value=True)


def test_record_is_frozen(sample_record):
    with pytest.raises(Exception):
        sample_record.value = Decimal("0")  # type: ignore[misc]


def test_flags_default_is_independent():
    a = MetricValueRecord(
        agency_slug="ttc",
        metric_code="ridership",
        period_type="monthly",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        period_label="Mar 2026",
        service_scope="system_wide",
        value=Decimal("1"),
        unit="count",
        quality="preliminary",
    )
    b = MetricValueRecord(
        agency_slug="stm",
        metric_code="ridership",
        period_type="monthly",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        period_label="Mar 2026",
        service_scope="system_wide",
        value=Decimal("2"),
        unit="count",
        quality="preliminary",
    )
    a.flags.append("yoy_spike")
    assert b.flags == []  # default_factory, not a shared mutable default


def test_to_dict_round_trips_serializable(sample_record):
    d = sample_record.to_dict()
    assert d["value"] == "1234567"  # Decimal -> str
    assert d["period_start"] == "2026-03-01"  # date -> ISO
    assert d["source"]["document_type"] == "statcan_table"
    assert d["source"]["confidence"] == "1.0"
    # JSON-serializable end to end
    import json

    assert json.loads(json.dumps(d))["metric_code"] == "ridership"


def test_sourceref_validation():
    with pytest.raises(ValueError):
        SourceRef(document_type="not_a_type", extraction_method="manual")
    with pytest.raises(ValueError):
        SourceRef(document_type="annual_report", extraction_method="telepathy")
    with pytest.raises(ValueError):
        SourceRef(
            document_type="annual_report",
            extraction_method="manual",
            confidence=Decimal("1.5"),
        )


def test_sourceref_to_dict(sample_record):
    d = sample_record.source.to_dict()
    assert d["extraction_method"] == "statcan_passthrough"
    assert d["license"] == "statcan_open"
