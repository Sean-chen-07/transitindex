"""Adapter for Hamilton Street Railway (HSR) monthly bus ridership.

Hamilton publishes pre-aggregated monthly ridership via an ArcGIS FeatureServer.
The endpoint returns CSV with three columns:

  OBJECTID        -- integer row id (ignored)
  YEAR_MONTH      -- Unix timestamp in milliseconds (UTC midnight on the 1st)
  MONTHLY_RIDERSHIP -- raw passenger count (not in thousands)

Live endpoint (returns CSV):
  https://services.arcgis.com/rYz782eMbySr2srL/arcgis/rest/services/
  HSR_Monthly_Bus_Ridership/FeatureServer/0/query?where=1%3D1&outFields=*&f=csv
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from ..contract import MetricValueRecord, SourceRef
from ..periods import monthly_period

HAMILTON_HSR_URL = (
    "https://services.arcgis.com/rYz782eMbySr2srL/arcgis/rest/services/"
    "HSR_Monthly_Bus_Ridership/FeatureServer/0/query?where=1%3D1&outFields=*&f=csv"
)

_AGENCY_SLUG = "hamilton-street-railway"
_FEED_CODE = "hamilton_open_data"


@dataclass
class HamiltonHSRAdapter:
    """Parses the Hamilton HSR ArcGIS CSV into MetricValueRecords.

    `skipped` is populated by `parse()` with one entry per row dropped due to
    a missing or unparseable value.
    """

    skipped: list[dict] = field(default_factory=list)

    def parse(self, raw_csv_text: str) -> list[MetricValueRecord]:
        self.skipped = []
        records: list[MetricValueRecord] = []

        reader = csv.DictReader(io.StringIO(raw_csv_text))
        for row in reader:
            ts_raw = (row.get("YEAR_MONTH") or "").strip()
            val_raw = (row.get("MONTHLY_RIDERSHIP") or "").strip()

            if not ts_raw or not val_raw:
                self.skipped.append({"row": dict(row), "reason": "empty field"})
                continue

            try:
                ts_ms = float(ts_raw)
                dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc)
                period = monthly_period(dt.year, dt.month)
            except (ValueError, OSError):
                self.skipped.append({"row": dict(row), "reason": "bad timestamp"})
                continue

            try:
                value = Decimal(val_raw)
            except Exception:
                self.skipped.append({"row": dict(row), "reason": "bad value"})
                continue

            records.append(
                MetricValueRecord(
                    agency_slug=_AGENCY_SLUG,
                    metric_code="monthly_ridership",
                    period_type=period.period_type,
                    period_start=period.start,
                    period_end=period.end,
                    period_label=period.label,
                    service_scope="total",
                    value=value,
                    unit="count",
                    quality="verified",
                    currency=None,
                    source=SourceRef(
                        document_type="open_data_csv",
                        extraction_method="structured_import",
                        license="ogl_hamilton",
                        source_url=HAMILTON_HSR_URL,
                        confidence=Decimal("1.0"),
                    ),
                )
            )

        return records
