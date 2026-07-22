"""Adapter for the FTA NTD "Annual Data — Metrics" dataset (Socrata ekg5-frzt).

The NTD annual module publishes each US Full Reporter's audited service and
financial figures per agency x report_year x mode x type-of-service. This
adapter reads the dataset's ``/resource/ekg5-frzt.csv`` export (API field names
as headers -- what ``ingest/scripts/fetch_ntd.py`` downloads), sums rows across
mode x type-of-service, and yields one system-wide `MetricValueRecord` per
(agency, metric, report year):

  * ``fare_revenues_earned``    -> farebox_revenue           (USD)
  * ``total_operating_expenses``-> operating_expenses        (USD,
      cost_basis='operating' -- NTD opex excludes depreciation, exactly the
      repo's pinned CUTA/NTD operating basis)
  * ``unlinked_passenger_trips``-> ridership                 (count)
  * ``vehicle_revenue_miles``   -> vehicle_revenue_km        (x 1.609344)
  * ``vehicle_revenue_hours``   -> revenue_service_hours     (hours)

``report_year`` is the agency's own fiscal year, named by the year it ends in;
the period comes from `periods.annual_period_from_end_year` (honouring the
agency's fiscal_year_end_month). NTD has no balance sheet or full accrual
income statement, so the PSAB metric family stays Canada-only.

Derived ratios (average_fare, cost_per_rider, farebox_recovery_ratio, ...)
materialize downstream via the equation graph -- not emitted here.

All rows are Tier-0 structured federal passthrough: quality='verified',
license='us_public_domain' (US-government work, 17 U.S.C. §105).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping

from ..contract import MetricValueRecord, SourceRef
from ..periods import annual_period_from_end_year
from ..refdata import RATED_METRICS
from ..refdata_us import NTD_AGENCY_MAP
from .ntd_monthly import MILES_TO_KM  # single source for the conversion factor

#: Canonical dataset URL (identifies the shared source document).
NTD_ANNUAL_URL = (
    "https://data.transportation.gov/Public-Transit/"
    "2022-2024-NTD-Annual-Data-Metrics/ekg5-frzt"
)

#: CSV column -> (metric_code, unit, currency). Summed across mode x TOS.
_FIELD_TO_METRIC: dict[str, tuple[str, str, str | None]] = {
    "fare_revenues_earned": ("farebox_revenue", "USD", "USD"),
    "total_operating_expenses": ("operating_expenses", "USD", "USD"),
    "unlinked_passenger_trips": ("ridership", "count", None),
    "vehicle_revenue_miles": ("vehicle_revenue_km", "km", None),
    "vehicle_revenue_hours": ("revenue_service_hours", "hours", None),
}


@dataclass
class NTDAnnualAdapter:
    """Parses the ekg5-frzt CSV export into MetricValueRecords.

    `agency_map` defaults to the generated refdata_us.NTD_AGENCY_MAP; tests
    inject a small map directly. `skipped` is populated by `parse()` with one
    entry per unmapped ntd_id.
    """

    agency_map: Mapping[str, str] = field(default_factory=lambda: NTD_AGENCY_MAP)
    skipped: list[dict] = field(default_factory=list)

    def parse(self, raw_csv_text: str) -> list[MetricValueRecord]:
        self.skipped = []
        skipped_ids: set[str] = set()

        # (slug, report_year, metric_code) -> running sum across mode x TOS.
        sums: dict[tuple[str, int, str], Decimal] = {}

        reader = csv.DictReader(io.StringIO(raw_csv_text))
        for row in reader:
            ntd_id = (row.get("ntd_id") or "").strip()
            year_raw = (row.get("report_year") or "").strip()
            if not year_raw.isdigit():
                continue
            year = int(year_raw)

            slug = self.agency_map.get(ntd_id)
            if slug is None:
                if ntd_id not in skipped_ids:
                    skipped_ids.add(ntd_id)
                    self.skipped.append(
                        {"ntd_id": ntd_id, "agency": (row.get("agency") or "").strip()}
                    )
                continue

            for column, (metric_code, _unit, _currency) in _FIELD_TO_METRIC.items():
                raw = (row.get(column) or "").strip()
                if raw == "":
                    continue  # not reported for this mode; never a zero
                value = Decimal(raw)
                if metric_code == "vehicle_revenue_km":
                    value *= MILES_TO_KM
                key = (slug, year, metric_code)
                sums[key] = sums.get(key, Decimal(0)) + value

        unit_by_code = {
            code: (unit, currency) for code, unit, currency in _FIELD_TO_METRIC.values()
        }
        records: list[MetricValueRecord] = []
        for (slug, year, metric_code), value in sorted(sums.items()):
            unit, currency = unit_by_code[metric_code]
            period = annual_period_from_end_year(slug, year)
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
                    unit=unit,
                    quality="verified",
                    currency=currency,
                    comparable_flag=metric_code in RATED_METRICS,
                    source=SourceRef(
                        document_type="open_data_csv",
                        extraction_method="structured_import",
                        license="us_public_domain",
                        source_url=NTD_ANNUAL_URL,
                        confidence=Decimal("1.0"),
                    ),
                )
            )
        return records
