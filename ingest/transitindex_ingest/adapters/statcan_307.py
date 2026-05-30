"""Adapter for StatCan table 23-10-0307 (monthly urban transit).

23-10-0307 publishes monthly passenger trips and operating revenue (excluding
subsidies) per transit system. This adapter reads the table's CSV export and
yields one `MetricValueRecord` per (system, measure, month):

  * GEO / transit-system label -> agency slug via refdata.STATCAN_AGENCY_MAP.
    A label that is not in the map is SKIPPED (collected in `.skipped`) rather
    than crashing -- it usually means a system we do not track, or a renamed
    geography that needs the map updated.
  * the measure label -> metric_code (annual_ridership / operating_revenue).
    Measures we do not map (e.g. fare totals) are skipped silently; they are not
    failures, just rows we have no metric for.
  * SCALAR_FACTOR ('units'/'thousands'/'millions') scales VALUE.
  * REF_DATE (YYYY-MM) -> a monthly reporting period.

All rows are Tier-0 structured passthrough: service_scope='total',
quality='verified' (or 'preliminary' when STATUS flags a preliminary figure),
currency='CAD' for revenue and None for ridership.
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from ..contract import MetricValueRecord, SourceRef
from ..periods import monthly_period
from ..refdata import STATCAN_AGENCY_MAP

#: Canonical 23-10-0307 table URL (matches the seed/fixture provenance).
STATCAN_307_URL = "https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2310030701"

#: "Transit measures" member label -> our metric code. Only the two measures we
#: ingest are listed; any other measure row is ignored.
_MEASURE_TO_METRIC: dict[str, str] = {
    "Total passenger trips": "annual_ridership",
    "Total operating revenue (excluding subsidies)": "operating_revenue",
}

#: SCALAR_FACTOR label -> multiplier applied to VALUE.
_SCALAR_MULTIPLIER: dict[str, Decimal] = {
    "units": Decimal(1),
    "thousands": Decimal(1000),
    "millions": Decimal(1_000_000),
}


@dataclass
class StatCan23100307Adapter:
    """Parses 23-10-0307 CSV text into MetricValueRecords.

    `skipped` is populated by `parse()` with one entry per row dropped because
    its GEO label is not in STATCAN_AGENCY_MAP -- feed the list to the alert
    path so an unmapped/renamed system is noticed instead of silently lost.
    """

    skipped: list[dict] = field(default_factory=list)

    def parse(self, raw_csv_text: str) -> list[MetricValueRecord]:
        self.skipped = []
        records: list[MetricValueRecord] = []

        reader = csv.DictReader(io.StringIO(raw_csv_text))
        for row in reader:
            geo = (row.get("GEO") or "").strip()
            measure = (row.get("Transit measures") or "").strip()
            ref_date = (row.get("REF_DATE") or "").strip()

            slug = STATCAN_AGENCY_MAP.get(geo)
            if slug is None:
                self.skipped.append({"geo": geo, "ref_date": ref_date, "measure": measure})
                continue

            metric_code = _MEASURE_TO_METRIC.get(measure)
            if metric_code is None:
                continue  # a measure we do not ingest; not an error

            raw_value = (row.get("VALUE") or "").strip()
            if raw_value == "":
                continue  # suppressed/empty cell; nothing to record

            period = self._period(ref_date)
            value = Decimal(raw_value) * self._scalar(row.get("SCALAR_FACTOR"))
            currency = "CAD" if metric_code == "operating_revenue" else None
            quality = "preliminary" if _is_preliminary(row.get("STATUS")) else "verified"

            records.append(
                MetricValueRecord(
                    agency_slug=slug,
                    metric_code=metric_code,
                    period_type=period.period_type,
                    period_start=period.start,
                    period_end=period.end,
                    period_label=period.label,
                    service_scope="total",
                    value=value,
                    unit="count" if metric_code == "annual_ridership" else "CAD",
                    quality=quality,
                    currency=currency,
                    source=SourceRef(
                        document_type="statcan_table",
                        extraction_method="statcan_passthrough",
                        license="statcan_open",
                        source_url=STATCAN_307_URL,
                        confidence=Decimal("1.0"),
                    ),
                )
            )

        return records

    @staticmethod
    def _period(ref_date: str):
        year_str, month_str = ref_date.split("-")
        return monthly_period(int(year_str), int(month_str))

    @staticmethod
    def _scalar(scalar_factor: str | None) -> Decimal:
        key = (scalar_factor or "units").strip().lower()
        try:
            return _SCALAR_MULTIPLIER[key]
        except KeyError:
            raise ValueError(f"unknown SCALAR_FACTOR: {scalar_factor!r}")


def _is_preliminary(status: str | None) -> bool:
    """StatCan STATUS code 'p' (or 'E' estimate) marks a non-final figure."""
    return (status or "").strip().lower() in {"p", "e"}
