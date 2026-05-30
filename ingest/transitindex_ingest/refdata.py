"""Seed reference data, mirrored in Python.

These constants reflect the rows seeded in db/seeds/*. The in-memory repository
is built from them so slug/code lookups resolve identically to the live DB.
Keep in sync with the SQL seeds if those change.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping

# --- 10 modes (db/seeds/01_modes.sql), insertion order preserved -------------

MODES: tuple[str, ...] = (
    "bus",
    "subway",
    "light_rail",
    "commuter_rail",
    "streetcar",
    "brt",
    "trolleybus",
    "ferry",
    "paratransit",
    "on_demand",
)

# --- 10 agencies (db/seeds/02_agencies.sql + 03_agency_modes.sql) ------------
# slug -> subdivision (province), fiscal_year_end_month, primary_modes.

AGENCIES: Mapping[str, Mapping] = MappingProxyType(
    {
        "ttc": MappingProxyType(
            {"subdivision": "ON", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "subway", "streetcar", "paratransit")}
        ),
        "stm": MappingProxyType(
            {"subdivision": "QC", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "subway")}
        ),
        "translink": MappingProxyType(
            {"subdivision": "BC", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "subway", "commuter_rail", "ferry", "paratransit")}
        ),
        "metrolinx": MappingProxyType(
            {"subdivision": "ON", "fiscal_year_end_month": 3,
             "primary_modes": ("commuter_rail", "bus")}
        ),
        "oc-transpo": MappingProxyType(
            {"subdivision": "ON", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "light_rail")}
        ),
        "calgary-transit": MappingProxyType(
            {"subdivision": "AB", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "light_rail")}
        ),
        "edmonton-ets": MappingProxyType(
            {"subdivision": "AB", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "light_rail")}
        ),
        "miway": MappingProxyType(
            {"subdivision": "ON", "fiscal_year_end_month": 12,
             "primary_modes": ("bus",)}
        ),
        "bc-transit": MappingProxyType(
            {"subdivision": "BC", "fiscal_year_end_month": 3,
             "primary_modes": ("bus",)}
        ),
        "burlington-transit": MappingProxyType(
            {"subdivision": "ON", "fiscal_year_end_month": 12,
             "primary_modes": ("bus",)}
        ),
    }
)

# --- 20 metrics (db/seeds/04_metrics.sql) ------------------------------------
# code -> unit, unit_type, is_derived, formula (None unless derived),
# higher_is_better (None = neutral). Insertion order preserved.

METRICS: Mapping[str, Mapping] = MappingProxyType(
    {
        "annual_ridership": MappingProxyType(
            {"unit": "count", "unit_type": "count", "is_derived": False,
             "formula": None, "higher_is_better": True}
        ),
        "revenue_service_hours": MappingProxyType(
            {"unit": "hours", "unit_type": "time", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "vehicle_revenue_km": MappingProxyType(
            {"unit": "km", "unit_type": "distance", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "average_fare": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "operating_revenue / annual_ridership", "higher_is_better": None}
        ),
        "trips_per_revenue_hour": MappingProxyType(
            {"unit": "trips/hr", "unit_type": "ratio", "is_derived": True,
             "formula": "annual_ridership / revenue_service_hours", "higher_is_better": True}
        ),
        "on_time_performance": MappingProxyType(
            {"unit": "%", "unit_type": "ratio", "is_derived": False,
             "formula": None, "higher_is_better": True}
        ),
        "operating_revenue": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "operating_expenses": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "total_operating_subsidy": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "labour_cost": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "energy_fuel_cost": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "materials_services_cost": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "farebox_recovery_ratio": MappingProxyType(
            {"unit": "%", "unit_type": "ratio", "is_derived": True,
             "formula": "operating_revenue / operating_expenses", "higher_is_better": None}
        ),
        "cost_per_rider": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "operating_expenses / annual_ridership", "higher_is_better": False}
        ),
        "cost_per_hour": MappingProxyType(
            {"unit": "CAD/hr", "unit_type": "currency", "is_derived": True,
             "formula": "operating_expenses / revenue_service_hours", "higher_is_better": False}
        ),
        "subsidy_per_rider": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "(operating_expenses - operating_revenue) / annual_ridership",
             "higher_is_better": None}
        ),
        "fleet_size": MappingProxyType(
            {"unit": "count", "unit_type": "count", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "fleet_average_age": MappingProxyType(
            {"unit": "years", "unit_type": "time", "is_derived": False,
             "formula": None, "higher_is_better": False}
        ),
        "accessible_fleet_pct": MappingProxyType(
            {"unit": "%", "unit_type": "ratio", "is_derived": False,
             "formula": None, "higher_is_better": True}
        ),
        "capital_expenditure": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
    }
)

# --- 8 source feeds (db/seeds/05_source_feeds.sql) ---------------------------
# code -> tier, expected_cadence, enabled. Insertion order preserved.

SOURCE_FEEDS: Mapping[str, Mapping] = MappingProxyType(
    {
        "statcan_307": MappingProxyType(
            {"tier": 0, "expected_cadence": "monthly", "enabled": True}
        ),
        "edmonton_open_data": MappingProxyType(
            {"tier": 1, "expected_cadence": "monthly", "enabled": True}
        ),
        "calgary_open_data": MappingProxyType(
            {"tier": 1, "expected_cadence": "monthly", "enabled": True}
        ),
        "translink_quarterly": MappingProxyType(
            {"tier": 2, "expected_cadence": "quarterly", "enabled": False}
        ),
        "ttc_ceo_report": MappingProxyType(
            {"tier": 2, "expected_cadence": "monthly", "enabled": False}
        ),
        "oc_transpo_kpi": MappingProxyType(
            {"tier": 2, "expected_cadence": "monthly", "enabled": False}
        ),
        "metrolinx_ops": MappingProxyType(
            {"tier": 2, "expected_cadence": "quarterly", "enabled": False}
        ),
        "annual_report_pdfs": MappingProxyType(
            {"tier": 2, "expected_cadence": "annual", "enabled": False}
        ),
    }
)

# --- StatCan 23-10-0307 member-label -> agency slug --------------------------
# Covers ONLY the 7 agencies in the table (not oc-transpo, miway,
# burlington-transit). The keys below are PLACEHOLDER member labels: the EXACT
# StatCan geography labels MUST be verified against the live download before
# production use -- they often carry CMA/region suffixes that differ from these.
STATCAN_AGENCY_MAP: Mapping[str, str] = MappingProxyType(
    {
        "Toronto": "ttc",
        "Montréal": "stm",
        "Vancouver": "translink",
        "Calgary": "calgary-transit",
        "Edmonton": "edmonton-ets",
        "Toronto (GO Transit / GTHA)": "metrolinx",
        "Victoria": "bc-transit",
    }
)
