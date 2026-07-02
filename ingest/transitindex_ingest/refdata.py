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

# Per-mode capacity weight for the aggregated `fleet_capacity` metric
# (Σ capacity_weight × fleet_size(mode)). Mirrors db/seeds/01_modes.sql +
# db/migrations/015_mode_capacity_weight.sql. Modes absent here (ferry,
# paratransit, on_demand) keep a NULL weight and are excluded from the aggregation.
MODE_CAPACITY_WEIGHT: Mapping[str, int] = MappingProxyType(
    {
        "bus": 1,
        "streetcar": 2,
        "light_rail": 3,
        "subway": 4,
        "commuter_rail": 5,
        "brt": 1,
        "trolleybus": 1,
    }
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
        # --- expansion agencies (data-collection targets beyond launch 10) ----
        "winnipeg-transit": MappingProxyType(
            {"subdivision": "MB", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "brt")}
        ),
        "hamilton-street-railway": MappingProxyType(
            {"subdivision": "ON", "fiscal_year_end_month": 12,
             "primary_modes": ("bus",)}
        ),
        "brampton-transit": MappingProxyType(
            {"subdivision": "ON", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "brt")}
        ),
        "grand-river-transit": MappingProxyType(
            {"subdivision": "ON", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "light_rail")}
        ),
        "stl-laval": MappingProxyType(
            {"subdivision": "QC", "fiscal_year_end_month": 12,
             "primary_modes": ("bus",)}
        ),
        "rtl-longueuil": MappingProxyType(
            {"subdivision": "QC", "fiscal_year_end_month": 12,
             "primary_modes": ("bus",)}
        ),
        "york-region-transit": MappingProxyType(
            {"subdivision": "ON", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "brt")}
        ),
        "halifax-transit": MappingProxyType(
            {"subdivision": "NS", "fiscal_year_end_month": 12,
             "primary_modes": ("bus", "ferry")}
        ),
        "durham-region-transit": MappingProxyType(
            {"subdivision": "ON", "fiscal_year_end_month": 12,
             "primary_modes": ("bus",)}
        ),
        "saskatoon-transit": MappingProxyType(
            {"subdivision": "SK", "fiscal_year_end_month": 12,
             "primary_modes": ("bus",)}
        ),
        "regina-transit": MappingProxyType(
            {"subdivision": "SK", "fiscal_year_end_month": 12,
             "primary_modes": ("bus",)}
        ),
    }
)

# --- 42 metrics (db/seeds/04_metrics.sql) ------------------------------------
# code -> unit, unit_type, is_derived, formula (None unless derived),
# higher_is_better (None = neutral). Insertion order preserved.
# Ridership is ONE metric; monthly vs annual is the reporting period's
# granularity (a dimension), not a separate metric code. The balance-sheet
# family (8 sourced + 3 derived) sits before the 10 financial-statement
# additions (metric-set-build-plan.md Phase 4): 5 sourced income-statement /
# revenue lines, plus 5 derived residuals (other_revenue, annual_surplus_deficit,
# and the three balance-sheet component residuals). All 10 are NON-rated.

METRICS: Mapping[str, Mapping] = MappingProxyType(
    {
        "ridership": MappingProxyType(
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
             "formula": "total_revenue_excluding_subsidy / ridership", "higher_is_better": None}
        ),
        "trips_per_revenue_hour": MappingProxyType(
            {"unit": "trips/hr", "unit_type": "ratio", "is_derived": True,
             "formula": "ridership / revenue_service_hours", "higher_is_better": True}
        ),
        "on_time_performance": MappingProxyType(
            {"unit": "%", "unit_type": "ratio", "is_derived": False,
             "formula": None, "higher_is_better": True}
        ),
        "total_revenue_excluding_subsidy": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "operating_expenses": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "subsidy": MappingProxyType(
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
             "formula": "total_revenue_excluding_subsidy / operating_expenses", "higher_is_better": None}
        ),
        "cost_per_rider": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "operating_expenses / ridership", "higher_is_better": False}
        ),
        "cost_per_hour": MappingProxyType(
            {"unit": "CAD/hr", "unit_type": "currency", "is_derived": True,
             "formula": "operating_expenses / revenue_service_hours", "higher_is_better": False}
        ),
        "subsidy_per_rider": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "subsidy / ridership",
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
        "fleet_capacity": MappingProxyType(
            {"unit": "count", "unit_type": "count", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "capital_expenditure": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        # --- balance-sheet family (PSAB statement of financial position) -------
        "total_financial_assets": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "total_liabilities": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "total_non_financial_assets": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "total_assets": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "tangible_capital_assets": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "accumulated_surplus": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "long_term_debt": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "cash_and_investments": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "net_debt": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "total_liabilities - total_financial_assets", "higher_is_better": False}
        ),
        "debt_to_assets": MappingProxyType(
            {"unit": "%", "unit_type": "ratio", "is_derived": True,
             "formula": "total_liabilities / total_assets", "higher_is_better": False}
        ),
        "net_debt_per_capita": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "net_debt / service_area_population", "higher_is_better": False}
        ),
        # --- financial-statement additions (metric-set-build-plan.md Phase 4) --
        # Sourced income-statement / revenue lines (non-rated, neutral):
        "amortization": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "other_operating_expenses": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "total_revenue": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "farebox_revenue": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        "total_expenses": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": False,
             "formula": None, "higher_is_better": None}
        ),
        # Derived residuals so the statements close (each defined by a SumEquation):
        "other_revenue": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "farebox_revenue + other_revenue", "higher_is_better": None}
        ),
        "annual_surplus_deficit": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "total_revenue - total_expenses", "higher_is_better": None}
        ),
        "other_financial_assets": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "cash_and_investments + other_financial_assets", "higher_is_better": None}
        ),
        "other_liabilities": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "long_term_debt + other_liabilities", "higher_is_better": None}
        ),
        "other_non_financial_assets": MappingProxyType(
            {"unit": "CAD", "unit_type": "currency", "is_derived": True,
             "formula": "tangible_capital_assets + other_non_financial_assets",
             "higher_is_better": None}
        ),
    }
)

# RANKING SOURCE OF TRUTH (2026-06-14 decision): only the five Highlights hero
# boxes are rated. Every other metric is shown without a rank. A value's
# comparable_flag is set to `code in RATED_METRICS`; rank_refresh additionally
# skips any metric not in this set. See docs/planning/metric-set-build-plan.md
# (Phase 1) and metric-standards-review.md ("Decisions taken").
RATED_METRICS: frozenset[str] = frozenset({
    "ridership", "total_revenue_excluding_subsidy", "on_time_performance",
    "cost_per_rider", "subsidy_per_rider",
})

# Balance-sheet dollar figures measure SIZE, not performance, so they are never
# ranked. SUPERSEDED by RATED_METRICS above for the comparable_flag decision
# (RATED_METRICS is the positive allow-list and the source of truth); kept for
# any code that still references the balance-sheet exclusion set.
NON_RANKABLE_METRICS: frozenset[str] = frozenset({
    "total_financial_assets", "total_liabilities", "total_non_financial_assets",
    "total_assets", "tangible_capital_assets", "accumulated_surplus",
    "long_term_debt", "cash_and_investments", "net_debt",
})

# --- 9 source feeds (db/seeds/05_source_feeds.sql) ---------------------------
# code -> tier, expected_cadence, enabled. Insertion order preserved.

SOURCE_FEEDS: Mapping[str, Mapping] = MappingProxyType(
    {
        "manual_entry": MappingProxyType(
            {"tier": 0, "expected_cadence": None, "enabled": True}
        ),
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
        "hamilton_open_data": MappingProxyType(
            {"tier": 1, "expected_cadence": "monthly", "enabled": True}
        ),
    }
)

# --- StatCan 23-10-0307 "Urban transit agency name" -> agency slug -----------
# Keys are the EXACT agency-name labels in the live 23-10-0307 CSV download.
# All 12 keys verified character-for-character against the live 23-10-0307 bulk CSV
# download (statcan_23100307.csv, verified 2026-06-04). The table also contains 6
# small systems we do not track (Codiac/Moncton, Leduc, Saint John, T3/PEI,
# Whitehorse, Yellowknife) — those are intentionally absent and the adapter
# collects them in `.skipped`. Note: OC Transpo, MiWay, Burlington, and Grand
# River Transit do NOT appear in this table (they need other sources).
STATCAN_AGENCY_MAP: Mapping[str, str] = MappingProxyType(
    {
        "Toronto transit commission (TTC)": "ttc",
        "Société de transport de Montréal (STM)": "stm",
        "South Coast British Columbia Transportation Authority (Translink)": "translink",
        "Calgary Transit": "calgary-transit",
        "Edmonton Transit Service (ETS)": "edmonton-ets",
        "Metrolinx, Greater Toronto and Hamilton Area (GTHA)": "metrolinx",
        "BC Transit (Victoria Regional Transit System)": "bc-transit",
        "Winnipeg Transit": "winnipeg-transit",
        "Halifax transit": "halifax-transit",
        "Réseau de transport de Longueuil": "rtl-longueuil",
        "Regina Transit": "regina-transit",
        "Société de transport de Laval": "stl-laval",
    }
)
