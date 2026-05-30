"""Shared pytest fixtures for the offline ingestion test suite.

Pure stdlib + pytest. `repo()` gives a fresh seeded InMemoryRepository;
`sample_record()` and `make_record()` build valid MetricValueRecords quickly.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from transitindex_ingest.contract import MetricValueRecord, SourceRef
from transitindex_ingest.db.memory import InMemoryRepository


@pytest.fixture
def repo() -> InMemoryRepository:
    """A fresh InMemoryRepository, seeded with all agencies/metrics/modes/feeds."""
    return InMemoryRepository()


@pytest.fixture
def make_record():
    """Factory: build a valid MetricValueRecord, overriding any field by kwarg."""

    def _make(**overrides) -> MetricValueRecord:
        defaults = dict(
            agency_slug="ttc",
            metric_code="annual_ridership",
            period_type="monthly",
            period_start=date(2026, 3, 1),
            period_end=date(2026, 3, 31),
            period_label="Mar 2026",
            service_scope="system_wide",
            value=Decimal("1234567"),
            unit="count",
            quality="preliminary",
            mode_code=None,
            currency=None,
            source=SourceRef(
                document_type="statcan_table",
                extraction_method="statcan_passthrough",
                source_url="https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2310030701",
                license="statcan_open",
                confidence=Decimal("1.0"),
            ),
        )
        defaults.update(overrides)
        return MetricValueRecord(**defaults)

    return _make


@pytest.fixture
def sample_record(make_record) -> MetricValueRecord:
    """A single valid MetricValueRecord (TTC annual_ridership, Mar 2026)."""
    return make_record()
