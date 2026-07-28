"""Adapter for the FTA NTD "Complete Monthly Ridership" dataset (Socrata 8bui-9xvu).

The National Transit Database publishes monthly unlinked passenger trips (UPT),
vehicle revenue miles (VRM) and vehicle revenue hours (VRH) for every US urban
Full Reporter, one row per agency x mode x type-of-service x month. This
adapter reads the dataset's ``/resource/8bui-9xvu.csv`` export (API field names
as headers -- what ``ingest/scripts/fetch_ntd.py`` downloads) and yields one
system-wide `MetricValueRecord` per (agency, metric, month):

  * ``ntd_id`` (5-digit zero-padded string) -> agency slug via
    refdata_us.NTD_AGENCY_MAP. An id not in the map is SKIPPED (collected in
    `.skipped`) -- a reporter we do not track, or a new one needing a
    generator re-run.
  * rows are SUMMED across mode x type-of-service into one system-wide value
    (mode_code=None, service_scope='total') -- the repo's grain for these
    metrics, matching the StatCan feed.
  * ``upt`` -> ridership (count); ``vrm`` -> vehicle_revenue_km (miles are
    converted at 1.609344 km/mile); ``vrh`` -> revenue_service_hours.
  * only ``reporter_type == 'Full Reporter'`` rows are ingested.
  * ``--since`` (a YYYY-MM string) drops months before the cutoff so the
    initial backfill stays bounded.

All rows are Tier-0 structured federal passthrough: quality='verified',
license='us_public_domain' (US-government work, 17 U.S.C. §105).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Mapping, Optional

from ..contract import MetricValueRecord, SourceRef
from ..periods import monthly_period
from ..refdata import RATED_METRICS
from ..refdata_us import NTD_AGENCY_MAP

#: Canonical dataset URL (identifies the shared source document).
NTD_MONTHLY_URL = (
    "https://data.transportation.gov/Public-Transit/"
    "Complete-Monthly-Ridership-with-adjustments-and-es/8bui-9xvu"
)

#: NTD reports distances in statute miles; the repo's metric is km.
MILES_TO_KM = Decimal("1.609344")

#: CSV column -> (metric_code, unit). Values are summed across mode x TOS.
_FIELD_TO_METRIC: dict[str, tuple[str, str]] = {
    "upt": ("ridership", "count"),
    "vrm": ("vehicle_revenue_km", "km"),
    "vrh": ("revenue_service_hours", "hours"),
}


@dataclass
class NTDMonthlyAdapter:
    """Parses the 8bui-9xvu CSV export into MetricValueRecords.

    `agency_map` defaults to the generated refdata_us.NTD_AGENCY_MAP; tests
    inject a small map directly. `skipped` is populated by `parse()` with one
    entry per (ntd_id, month) dropped because the id is unmapped.
    """

    agency_map: Mapping[str, str] = field(default_factory=lambda: NTD_AGENCY_MAP)
    skipped: list[dict] = field(default_factory=list)

    def parse(self, raw_csv_text: str, since: Optional[str] = None) -> list[MetricValueRecord]:
        self.skipped = []
        skipped_ids: set[str] = set()

        # (slug, year, month, metric_code) -> running sum across mode x TOS.
        sums: dict[tuple[str, int, int, str], Decimal] = {}
        units: dict[str, str] = {code: unit for code, unit in _FIELD_TO_METRIC.values()}

        reader = csv.DictReader(io.StringIO(raw_csv_text))
        for row in reader:
            reporter_type = (row.get("reporter_type") or "").strip()
            if reporter_type != "Full Reporter":
                continue

            ntd_id = (row.get("ntd_id") or "").strip()
            year_month = _year_month(row.get("date"))
            if year_month is None:
                continue
            year, month = year_month
            if since is not None and f"{year:04d}-{month:02d}" < since:
                continue

            slug = self.agency_map.get(ntd_id)
            if slug is None:
                if ntd_id not in skipped_ids:
                    skipped_ids.add(ntd_id)
                    self.skipped.append(
                        {"ntd_id": ntd_id, "agency": (row.get("agency") or "").strip()}
                    )
                continue

            for column, (metric_code, _unit) in _FIELD_TO_METRIC.items():
                raw = (row.get(column) or "").strip()
                if raw == "":
                    continue  # not reported for this mode/month; never a zero
                value = Decimal(raw)
                if metric_code == "vehicle_revenue_km":
                    value *= MILES_TO_KM
                key = (slug, year, month, metric_code)
                sums[key] = sums.get(key, Decimal(0)) + value

        records: list[MetricValueRecord] = []
        for (slug, year, month, metric_code), value in sorted(sums.items()):
            period = monthly_period(year, month)
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
                    unit=units[metric_code],
                    quality="verified",
                    currency=None,
                    comparable_flag=metric_code in RATED_METRICS,
                    source=SourceRef(
                        document_type="open_data_csv",
                        extraction_method="structured_import",
                        license="us_public_domain",
                        source_url=NTD_MONTHLY_URL,
                        confidence=Decimal("1.0"),
                    ),
                )
            )
        return records


def _year_month(raw: str | None) -> Optional[tuple[int, int]]:
    """Parse the dataset's ISO month stamp ('2024-01-01T00:00:00.000') -> (2024, 1)."""
    text = (raw or "").strip()
    if len(text) < 7:
        return None
    try:
        return int(text[0:4]), int(text[5:7])
    except ValueError:
        return None
