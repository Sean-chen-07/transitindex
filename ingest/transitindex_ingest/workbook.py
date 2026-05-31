"""Spreadsheet round-trip: export an editable .xlsx, import it back.

This is the manual-entry path for a NON-TECHNICAL editor (city staff). It
turns the database into a friendly Excel workbook they can fill by hand, then
reads that workbook back into the pipeline.

The workbook has four sheets:
  1. "How to use"     -- plain-language instructions.
  2. "Data Dictionary"-- what every column means, its unit, and (for derived
                         metrics) the plain-text formula.
  3. "Data"           -- the editable grid: one row per (agency, year). The 14
                         SOURCED columns are typed in by hand; the 6 DERIVED
                         columns hold live EXCEL formulas (grey, do-not-edit)
                         that mirror the pipeline's own derived math.
  4. "Gaps"           -- a per-row at-a-glance count of how many of the 14
                         sourced cells are filled vs missing.

export_workbook reads the current system-wide values out of the DB and seeds
the Data sheet with them (the DB is empty at MVP, so this usually fills
nothing -- expected). import_workbook reads the SOURCED columns only (never the
derived columns -- those are recomputed downstream) and pushes them through the
exact same orchestration as the StatCan importer: stage (tier 0, auto-approve
clean rows) -> promote -> recompute the 6 derived ratios -> refresh ranks.

The derived-column definitions are driven off the SAME `{numerator codes,
denominator code}` structure as jobs.derived_recompute._DERIVED, so the Excel
formulas and the server-side recompute can never drift apart: blank out when
any input is missing OR the denominator is zero (never divide by zero, never
fabricate a value).

openpyxl is imported LAZILY inside export/import so merely importing this
module never requires it. Everything else is pure stdlib.
"""

from __future__ import annotations

from .jobs.derived_recompute import _DERIVED
from .refdata import AGENCIES, METRICS

# --- Public metric ordering, names, and agency names -------------------------

# The 14 sourced and 6 derived metric codes, in refdata.METRICS display order.
SOURCED_METRICS: list[str] = [c for c, m in METRICS.items() if not m["is_derived"]]
DERIVED_METRICS: list[str] = [c for c, m in METRICS.items() if m["is_derived"]]

# Metric code -> human display name (the names a non-technical user reads).
DISPLAY_NAMES: dict[str, str] = {
    "annual_ridership": "Annual Ridership",
    "revenue_service_hours": "Revenue Service Hours",
    "vehicle_revenue_km": "Vehicle Revenue Kilometres",
    "on_time_performance": "On-Time Performance",
    "operating_revenue": "Operating Revenue",
    "operating_expenses": "Operating Expenses",
    "total_operating_subsidy": "Total Operating Subsidy",
    "labour_cost": "Labour Cost",
    "energy_fuel_cost": "Energy & Fuel Cost",
    "materials_services_cost": "Materials & Services Cost",
    "fleet_size": "Fleet Size",
    "fleet_average_age": "Fleet Average Age",
    "accessible_fleet_pct": "Accessible Fleet %",
    "capital_expenditure": "Capital Expenditure",
    "average_fare": "Average Fare",
    "trips_per_revenue_hour": "Trips per Revenue Hour",
    "farebox_recovery_ratio": "Farebox Recovery Ratio",
    "cost_per_rider": "Cost per Rider",
    "cost_per_hour": "Cost per Revenue Hour",
    "subsidy_per_rider": "Subsidy per Rider",
}

# Agency slug -> short name, in refdata.AGENCIES order (= Data-sheet row order).
AGENCY_NAMES: dict[str, str] = {
    "ttc": "TTC",
    "stm": "STM",
    "translink": "TransLink",
    "metrolinx": "Metrolinx",
    "oc-transpo": "OC Transpo",
    "calgary-transit": "Calgary Transit",
    "edmonton-ets": "ETS",
    "miway": "MiWay",
    "bc-transit": "BC Transit",
    "burlington-transit": "Burlington Transit",
}

# Plain-language gloss per metric for the Data Dictionary "Plain meaning" column.
_PLAIN_MEANING: dict[str, str] = {
    "annual_ridership": "Total boardings (unlinked passenger trips) for the year.",
    "revenue_service_hours": "Hours vehicles spent carrying passengers in service.",
    "vehicle_revenue_km": "Kilometres vehicles travelled while in passenger service.",
    "on_time_performance": "Share of trips that ran on time.",
    "operating_revenue": "Money earned from fares and other operations.",
    "operating_expenses": "Total cost of running the service for the year.",
    "total_operating_subsidy": "Government funding covering the operating shortfall.",
    "labour_cost": "Wages, salaries, and benefits for staff.",
    "energy_fuel_cost": "Cost of fuel and electricity to run vehicles.",
    "materials_services_cost": "Cost of parts, supplies, and outside services.",
    "fleet_size": "Number of vehicles in the fleet.",
    "fleet_average_age": "Average age of the vehicles in the fleet.",
    "accessible_fleet_pct": "Share of the fleet that is wheelchair-accessible.",
    "capital_expenditure": "Spending on long-term assets (vehicles, facilities).",
    "average_fare": "Revenue collected per rider.",
    "trips_per_revenue_hour": "Riders carried per hour of service.",
    "farebox_recovery_ratio": "Share of operating cost covered by fares.",
    "cost_per_rider": "Operating cost to carry one rider.",
    "cost_per_hour": "Operating cost per hour of service.",
    "subsidy_per_rider": "Public subsidy needed per rider.",
}

# Sheet names (single source of truth for both export and import).
_SHEET_HOWTO = "How to use"
_SHEET_DICT = "Data Dictionary"
_SHEET_DATA = "Data"
_SHEET_GAPS = "Gaps"


# --- Derived-formula plumbing (driven off _DERIVED so it can't drift) --------


def _plain_formula(code: str) -> str:
    """Human-readable formula for a derived metric, e.g. 'Operating Revenue /
    Annual Ridership' -- built from the same _DERIVED structure the math uses."""
    numer_codes, denom_code = _DERIVED[code]
    if len(numer_codes) == 1:
        numerator = DISPLAY_NAMES[numer_codes[0]]
    else:
        # subsidy_per_rider: numerator is (expenses - revenue).
        numerator = "(" + " - ".join(DISPLAY_NAMES[c] for c in numer_codes) + ")"
    return f"{numerator} / {DISPLAY_NAMES[denom_code]}"


def _excel_unit_format(code: str) -> str:
    """openpyxl number_format string chosen from the metric's unit/unit_type."""
    meta = METRICS[code]
    unit = meta["unit"]
    unit_type = meta["unit_type"]
    if unit_type == "currency":
        return '#,##0.00'  # dollars; no symbol so CAD/CAD-per-hour read cleanly
    if unit == "%":
        return '#,##0.0'  # stored as a percentage number (e.g. 92.5), not a fraction
    if unit_type in ("count",):
        return '#,##0'
    return '#,##0.00'  # hours, km, years, ratios


def _derived_excel_formula(code: str, row: int, col_of: dict[str, int]) -> str:
    """Build the live Excel formula for a derived cell in `row`.

    Mirrors compute_derived: blank ("") when any input cell is empty OR the
    denominator is zero, else numerator/denominator. Column letters are computed
    programmatically from `col_of` (metric code -> 1-based column index); never
    hardcoded. Refs use an absolute column ($G2 style) so they survive copy/fill.
    """
    from openpyxl.utils import get_column_letter

    numer_codes, denom_code = _DERIVED[code]
    den = f"${get_column_letter(col_of[denom_code])}{row}"

    if len(numer_codes) == 1:
        num = f"${get_column_letter(col_of[numer_codes[0]])}{row}"
        guard = f'OR({num}="",{den}="",{den}=0)'
        value = f"{num}/{den}"
    else:
        # subsidy_per_rider: numerator = (operating_expenses - operating_revenue).
        exp = f"${get_column_letter(col_of[numer_codes[0]])}{row}"
        rev = f"${get_column_letter(col_of[numer_codes[1]])}{row}"
        guard = f'OR({exp}="",{rev}="",{den}="",{den}=0)'
        value = f"({exp}-{rev})/{den}"

    return f'=IF({guard},"",{value})'


# --- DB read helper ----------------------------------------------------------


def _read_current_values(repo) -> dict[tuple[str, int], dict[str, object]]:
    """Pull current system-wide sourced values out of the DB.

    Returns {(agency_slug, year): {metric_code: value}} where `year` is the
    calendar year the reporting period BEGINS (period.start_date.year). Only
    system-wide rows (mode_id is None) are read; derived metrics are skipped
    (the workbook recomputes them via formulas). The DB is empty at MVP, so this
    usually returns nothing -- that is expected and fine.
    """
    metric_code = {m.id: m.code for m in repo.list_metrics()}
    out: dict[tuple[str, int], dict[str, object]] = {}
    for slug in AGENCY_NAMES:
        agency_id = repo.agency_id(slug)
        for period in repo.list_reporting_periods(agency_id):
            year = period.start_date.year
            for v in repo.list_current_values_for_agency_period(agency_id, period.id):
                if v.mode_id is not None:
                    continue
                code = metric_code.get(v.metric_id)
                if code is None or code not in SOURCED_METRICS:
                    continue
                out.setdefault((slug, year), {})[code] = v.value
    return out


# --- Export ------------------------------------------------------------------


def export_workbook(repo, path: str, years: list[int]) -> dict:
    """Build the four-sheet editable workbook and save it to `path`.

    One Data row per (agency in AGENCY_NAMES order) x (year in `years`). Sourced
    cells are pre-filled from the DB where present; derived cells carry live
    Excel formulas. Returns a summary dict with counts.
    """
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    db_values = _read_current_values(repo)

    wb = Workbook()
    _build_howto_sheet(wb)  # replaces the default sheet
    _build_dictionary_sheet(wb)
    filled_cells = _build_data_sheet(wb, years, db_values)
    _build_gaps_sheet(wb, years)

    wb.save(path)

    n_agencies = len(AGENCY_NAMES)
    return {
        "path": path,
        "rows": n_agencies * len(years),
        "agencies": n_agencies,
        "years": list(years),
        "filled_cells": filled_cells,
    }


def _build_howto_sheet(wb) -> None:
    """Sheet 1: plain-language instructions; reuses the default first sheet."""
    from openpyxl.styles import Alignment, Font

    ws = wb.active
    ws.title = _SHEET_HOWTO
    ws.sheet_view.showGridLines = False

    lines = [
        ("How to use this workbook", True),
        ("", False),
        ("This workbook collects transit performance numbers, one row per "
         "agency per year.", False),
        ("", False),
        ("1. Go to the \"Data\" tab.", False),
        ("2. Find the row for your agency and year.", False),
        ("3. Type real numbers into the WHITE columns, taken straight from your "
         "source (annual report, budget, etc.).", False),
        ("4. Leave a cell BLANK if you don't have that number yet -- never guess.",
         False),
        ("5. The GREY columns are calculated automatically (e.g. Cost per Rider). "
         "Do NOT type in them -- they will fill themselves in.", False),
        ("", False),
        ("About the Year column:", True),
        ("The Year is the calendar year the reporting year BEGINS. For most "
         "agencies that is just the calendar year. For Metrolinx and BC Transit "
         "(fiscal year ending in March), Year 2023 means their 2023-24 fiscal "
         "year.", False),
        ("", False),
        ("Want to know what a column means?", True),
        ("See the \"Data Dictionary\" tab for the plain meaning, unit, and "
         "formula of every column.", False),
        ("", False),
        ("Want to see what's still missing?", True),
        ("See the \"Gaps\" tab: it counts, for each row, how many of the 14 "
         "typed-in numbers are filled vs still missing.", False),
        ("", False),
        ("When you're done:", True),
        ("Save the file and run the import command to save your numbers back "
         "into the database. The grey calculated columns are recomputed on the "
         "server -- you don't need to worry about them.", False),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        cell = ws.cell(row=i, column=1, value=text)
        cell.font = Font(bold=bold, size=14 if (bold and i == 1) else 11)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 100


def _build_dictionary_sheet(wb) -> None:
    """Sheet 2: one row per metric -- meaning, unit, type, and formula."""
    from openpyxl.styles import Alignment, Font

    ws = wb.create_sheet(_SHEET_DICT)
    headers = ["Column", "Plain meaning", "Unit", "Type", "Formula"]
    for col, head in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=head)
        cell.font = Font(bold=True)

    row = 2
    # 14 sourced then 6 derived, matching the Data sheet column order.
    for code in SOURCED_METRICS + DERIVED_METRICS:
        is_derived = METRICS[code]["is_derived"]
        ws.cell(row=row, column=1, value=DISPLAY_NAMES[code])
        ws.cell(row=row, column=2, value=_PLAIN_MEANING[code])
        ws.cell(row=row, column=3, value=METRICS[code]["unit"])
        ws.cell(row=row, column=4, value="Calculated" if is_derived else "Sourced")
        ws.cell(row=row, column=5, value=_plain_formula(code) if is_derived else "")
        row += 1

    ws.freeze_panes = "A2"
    for col_letter, width in (("A", 28), ("B", 55), ("C", 10), ("D", 12), ("E", 38)):
        ws.column_dimensions[col_letter].width = width
    for r in range(2, row):
        ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")


def _build_data_sheet(wb, years: list[int], db_values: dict) -> int:
    """Sheet 3: the editable grid. Returns the number of sourced cells filled.

    Header: Agency, Year, then 14 sourced display names, then 6 derived display
    names. One row per (agency, year). Sourced cells filled from `db_values`;
    derived cells get live Excel formulas referencing the same-row sourced cells.
    """
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet(_SHEET_DATA)
    grey = PatternFill(start_color="FFD9D9D9", end_color="FFD9D9D9", fill_type="solid")
    bold = Font(bold=True)

    ordered_metrics = SOURCED_METRICS + DERIVED_METRICS
    # Map each metric code to its 1-based column index (Agency=1, Year=2, then
    # metrics start at 3). Computed once, used for every formula.
    col_of: dict[str, int] = {
        code: 3 + idx for idx, code in enumerate(ordered_metrics)
    }

    # Header row.
    ws.cell(row=1, column=1, value="Agency").font = bold
    ws.cell(row=1, column=2, value="Year").font = bold
    for code in ordered_metrics:
        cell = ws.cell(row=1, column=col_of[code], value=DISPLAY_NAMES[code])
        cell.font = bold
        cell.alignment = Alignment(wrap_text=True, vertical="bottom")
        if METRICS[code]["is_derived"]:
            cell.fill = grey

    filled_cells = 0
    row = 2
    for slug, short_name in AGENCY_NAMES.items():
        for year in years:
            ws.cell(row=row, column=1, value=short_name)
            ws.cell(row=row, column=2, value=int(year))

            row_values = db_values.get((slug, year), {})
            for code in SOURCED_METRICS:
                cell = ws.cell(row=row, column=col_of[code])
                cell.number_format = _excel_unit_format(code)
                if code in row_values:
                    # value is Decimal; openpyxl needs a float/int for numerics.
                    cell.value = float(row_values[code])
                    filled_cells += 1

            for code in DERIVED_METRICS:
                cell = ws.cell(row=row, column=col_of[code])
                cell.value = _derived_excel_formula(code, row, col_of)
                cell.number_format = _excel_unit_format(code)
                cell.fill = grey
            row += 1

    # Styling: freeze header + first two columns, sensible widths.
    ws.freeze_panes = "C2"
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 8
    for code in ordered_metrics:
        ws.column_dimensions[get_column_letter(col_of[code])].width = 16

    return filled_cells


def _build_gaps_sheet(wb, years: list[int]) -> None:
    """Sheet 4: per-row count of filled vs missing sourced cells.

    The Filled/Missing columns are live Excel formulas over the Data sheet, so
    they update as the user types -- never stale.
    """
    from openpyxl.styles import Font
    from openpyxl.utils import get_column_letter

    ws = wb.create_sheet(_SHEET_GAPS)
    bold = Font(bold=True)
    for col, head in enumerate(
        ["Agency", "Year", "Filled (of 14)", "Missing metrics"], start=1
    ):
        ws.cell(row=1, column=col, value=head).font = bold

    # Sourced columns on the Data sheet occupy columns 3 .. 3+13 (14 columns).
    first_sourced = 3
    last_sourced = first_sourced + len(SOURCED_METRICS) - 1
    first_col = get_column_letter(first_sourced)
    last_col = get_column_letter(last_sourced)

    row = 2
    for short_name in AGENCY_NAMES.values():
        for year in years:
            data_row = row  # Data sheet and Gaps sheet share the same row layout
            ws.cell(row=row, column=1, value=short_name)
            ws.cell(row=row, column=2, value=int(year))
            data_range = f"'{_SHEET_DATA}'!{first_col}{data_row}:{last_col}{data_row}"
            ws.cell(row=row, column=3, value=f"=COUNT({data_range})")
            # The list of missing metric names is static (which metrics could be
            # filled), but the COUNT above tells the user how many are still
            # blank. We list ALL 14 sourced names so they know the full set.
            row += 1

    # A static reference list of the 14 sourced metrics for the user.
    ws.cell(row=row + 1, column=1, value="The 14 numbers to fill in:").font = bold
    for i, code in enumerate(SOURCED_METRICS, start=row + 2):
        ws.cell(row=i, column=1, value=DISPLAY_NAMES[code])

    ws.freeze_panes = "A2"
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 8
    ws.column_dimensions["C"].width = 14
    ws.column_dimensions["D"].width = 40


# --- Import ------------------------------------------------------------------


def import_workbook(repo, path: str) -> dict:
    """Read the Data sheet's SOURCED columns and push them through the pipeline.

    Mirrors cli.cmd_statcan exactly: build MetricValueRecords (sourced columns
    only -- never the 6 derived columns), stage them (tier 0, feed
    'manual_entry'), promote approved rows, recompute the derived ratios for
    each touched (agency, period), then refresh ranks for every metric in each
    touched period. Returns counts plus any sanity warnings.
    """
    from decimal import Decimal, InvalidOperation

    from openpyxl import load_workbook

    from .contract import MetricValueRecord, SourceRef
    from .jobs.derived_recompute import recompute_derived
    from .jobs.rank_refresh import refresh_ranks
    from .periods import annual_period
    from .promotion import promote_approved
    from .refdata import METRICS
    from .staging import stage_records

    # Reverse map short-name -> slug to resolve the Agency column.
    slug_of = {name: slug for slug, name in AGENCY_NAMES.items()}

    wb = load_workbook(path, data_only=False)
    if _SHEET_DATA not in wb.sheetnames:
        raise ValueError(f"workbook has no {_SHEET_DATA!r} sheet: {path}")
    ws = wb[_SHEET_DATA]

    # Column code <- header display name, for the SOURCED columns only.
    name_to_code = {DISPLAY_NAMES[c]: c for c in SOURCED_METRICS}

    header = [cell.value for cell in ws[1]]
    # Map each sourced metric code to its 0-based column index in this sheet.
    code_at_col: dict[int, str] = {}
    for idx, head in enumerate(header):
        if head in name_to_code:
            code_at_col[idx] = name_to_code[head]

    warnings: list[str] = []
    records: list[MetricValueRecord] = []
    source = SourceRef(
        document_type="manual_entry",
        extraction_method="manual",
        title="Manual entry (workbook import)",
    )

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        agency_name = row[0] if len(row) > 0 else None
        year_cell = row[1] if len(row) > 1 else None
        # Skip rows without an agency or a year.
        if agency_name is None or year_cell is None:
            continue
        slug = slug_of.get(str(agency_name).strip())
        if slug is None:
            warnings.append(f"unknown agency name: {agency_name!r}")
            continue
        try:
            year = int(year_cell)
        except (TypeError, ValueError):
            warnings.append(f"unreadable year {year_cell!r} for {agency_name}")
            continue

        period = annual_period(slug, year)
        for col_idx, code in code_at_col.items():
            if col_idx >= len(row):
                continue
            cell = row[col_idx]
            if cell is None or cell == "":
                continue  # blank: not entered, skip (never fabricate)
            try:
                # Pass through str so Decimal stays exact (1.1 not 1.0999...).
                value = Decimal(str(cell))
            except (InvalidOperation, ValueError):
                warnings.append(f"non-numeric {DISPLAY_NAMES[code]} for {agency_name} {year}: {cell!r}")
                continue

            meta = METRICS[code]
            records.append(
                MetricValueRecord(
                    agency_slug=slug,
                    metric_code=code,
                    period_type=period.period_type,
                    period_start=period.start,
                    period_end=period.end,
                    period_label=period.label,
                    service_scope="total",
                    value=str(value),
                    unit=meta["unit"],
                    quality="verified",
                    currency="CAD" if meta["unit_type"] == "currency" else None,
                    comparable_flag=True,
                    source=source,
                )
            )

    # --- Mirror cmd_statcan orchestration exactly ---------------------------
    pending_ids = stage_records(repo, records, tier=0, feed_code="manual_entry")
    promoted = promote_approved(repo)

    periods: set[int] = set()
    agency_periods: set[tuple[str, int]] = set()
    for r in records:
        aid = repo.agency_id(r.agency_slug)
        pid = repo.get_or_create_reporting_period(
            aid, r.period_type, r.period_start, r.period_end, r.period_label
        )
        periods.add(pid)
        agency_periods.add((r.agency_slug, pid))

    derived = 0
    for agency_slug, pid in sorted(agency_periods):
        res = recompute_derived(repo, agency_slug, pid)
        derived += len(res.ids)
        warnings.extend(res.warnings)

    for pid in periods:
        for code in METRICS:
            refresh_ranks(repo, code, pid, service_scope="total")

    return {
        "staged": len(pending_ids),
        "promoted": len(promoted),
        "derived": derived,
        "periods": len(periods),
        "warnings": warnings,
    }
