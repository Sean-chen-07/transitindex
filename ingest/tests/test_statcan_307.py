"""Proves the StatCan 23-10-0307 adapter: mapping, scaling, periods, skip path.

Offline + pure stdlib (csv via the stdlib module). The fixture mirrors the real
table shape: 3 mapped systems x 2 measures x 2 months, plus one partially-mapped
system (Winnipeg Transit, ridership only — now in STATCAN_AGENCY_MAP). A row with
an agency name not in the map must land in `.skipped` and never reach the output.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from transitindex_ingest.adapters.base import Adapter, FileFetcher, Fetcher
from transitindex_ingest.adapters.statcan_307 import (
    STATCAN_307_URL,
    StatCan23100307Adapter,
)
from transitindex_ingest.contract import MetricValueRecord

FIXTURE = Path(__file__).parent / "fixtures" / "statcan_307_sample.csv"


def _parse():
    adapter = StatCan23100307Adapter()
    raw = FileFetcher().fetch(str(FIXTURE))
    return adapter, adapter.parse(raw)


def test_filefetcher_and_protocols():
    fetcher = FileFetcher()
    assert isinstance(fetcher, Fetcher)
    assert isinstance(StatCan23100307Adapter(), Adapter)


def test_count_includes_winnipeg():
    # 12 rows for TTC/STM/Calgary (3 systems x 2 measures x 2 months)
    # + 1 Winnipeg ridership row = 13 total; Winnipeg is now in the map.
    _, records = _parse()
    assert len(records) == 13


def test_all_records_valid():
    _, records = _parse()
    assert all(isinstance(r, MetricValueRecord) for r in records)


def test_slug_mapping():
    _, records = _parse()
    slugs = {r.agency_slug for r in records}
    assert slugs == {"ttc", "stm", "calgary-transit", "winnipeg-transit"}


def test_measure_to_metric_code():
    _, records = _parse()
    codes = {r.metric_code for r in records}
    assert codes == {"ridership", "operating_revenue"}


def test_scalar_factor_applied():
    # Toronto Jan revenue: VALUE 52000 with SCALAR_FACTOR 'thousands' -> x1000.
    _, records = _parse()
    rev = _one(records, "ttc", "operating_revenue", date(2026, 1, 1))
    assert rev.value == Decimal("52000") * Decimal(1000)
    assert rev.value == Decimal("52000000")
    # Ridership: VALUE 45000 with SCALAR_FACTOR 'thousands' -> x1000.
    trips = _one(records, "ttc", "ridership", date(2026, 1, 1))
    assert trips.value == Decimal("45000000")


def test_monthly_period_bounds_and_label():
    _, records = _parse()
    feb = _one(records, "stm", "ridership", date(2026, 2, 1))
    assert feb.period_type == "monthly"
    assert feb.period_start == date(2026, 2, 1)
    assert feb.period_end == date(2026, 2, 28)
    assert feb.period_label == "Feb 2026"


def test_scope_currency_and_source():
    _, records = _parse()
    rev = _one(records, "calgary-transit", "operating_revenue", date(2026, 1, 1))
    trips = _one(records, "calgary-transit", "ridership", date(2026, 1, 1))
    assert rev.service_scope == "total"
    assert rev.currency == "CAD"
    assert trips.currency is None
    assert rev.source.document_type == "statcan_table"
    assert rev.source.extraction_method == "statcan_passthrough"
    assert rev.source.license == "statcan_open"
    assert rev.source.source_url == STATCAN_307_URL
    assert rev.source.confidence == Decimal("1.0")


def test_status_marks_preliminary():
    _, records = _parse()
    # Toronto Feb rows carry STATUS 'p'; Jan rows are final.
    jan = _one(records, "ttc", "ridership", date(2026, 1, 1))
    feb = _one(records, "ttc", "ridership", date(2026, 2, 1))
    assert jan.quality == "verified"
    assert feb.quality == "preliminary"


def test_unmapped_system_skipped():
    # Winnipeg Transit is now in STATCAN_AGENCY_MAP so nothing should be skipped
    # from this fixture (all agency names are mapped or have empty values).
    adapter, records = _parse()
    assert len(adapter.skipped) == 0
    assert any(r.agency_slug == "winnipeg-transit" for r in records)


def test_skipped_reset_between_parses():
    # Skipped list must reset on each call, not accumulate.
    unmapped_row = (
        '"2026-01","Canada","","Unknown Agency","Urban transit systems",'
        '"Total passenger trips","Number","223","units","0","v1","1.1","5000","","","","1"\n'
    )
    header = FIXTURE.read_text(encoding="utf-8").splitlines()[0] + "\n"
    adapter = StatCan23100307Adapter()
    adapter.parse(header + unmapped_row)
    adapter.parse(header + unmapped_row)
    assert len(adapter.skipped) == 1  # not 2 — reset each call


def _one(records, slug, code, start) -> MetricValueRecord:
    matches = [
        r
        for r in records
        if r.agency_slug == slug and r.metric_code == code and r.period_start == start
    ]
    assert len(matches) == 1, f"expected exactly one {slug}/{code}/{start}, got {len(matches)}"
    return matches[0]
