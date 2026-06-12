"""Round-trip tests for the per-agency calendar-year time-series workbook.

Skipped unless BOTH openpyxl and PyYAML are installed (the workbook lazy-imports
openpyxl for the spreadsheet and PyYAML via the data dictionary).
"""

from __future__ import annotations

from decimal import Decimal

import pytest

openpyxl = pytest.importorskip("openpyxl")
pytest.importorskip("yaml")

from transitindex_ingest import workbook
from transitindex_ingest.dictionary import load_dictionary
from transitindex_ingest.periods import annual_period, monthly_period

NAMES = {c: s.display_name for c, s in load_dictionary().items()}


# --- helpers -----------------------------------------------------------------


def _load(path):
    return openpyxl.load_workbook(path, data_only=False)


def _year_block(ws, year: int) -> int:
    """1-based start column of `year`'s 18-col block on an agency tab.

    `year` is the START year; matches a bare-year header or a fiscal 'FY2024-25'
    label (parsed back to its start year), exactly as import does."""
    col = workbook._FIRST_YEAR_COL
    while col <= ws.max_column:
        raw = ws.cell(row=workbook._YEAR_HEADER_ROW, column=col).value
        if raw is not None and workbook._parse_year_header(raw) == year:
            return col
        col += workbook.YEAR_BLOCK_WIDTH
    raise AssertionError(f"year block {year} not found")


def _row_for(ws, label: str) -> int:
    """1-based row whose column-A label matches `label`."""
    for r in range(workbook._FIRST_DATA_ROW, ws.max_row + 1):
        if ws.cell(row=r, column=workbook._LABEL_COL).value == label:
            return r
    raise AssertionError(f"row {label!r} not found")


def _set_month(ws, *, metric_code: str, year: int, month: int, value) -> None:
    row = _row_for(ws, NAMES[metric_code])
    ystart = _year_block(ws, year)
    off = workbook._MONTH_OFFSETS[month - 1]
    ws.cell(row=row, column=ystart + off).value = value


def _fill_year_of_months(ws, *, metric_code: str, year: int, value) -> None:
    for m in range(1, 13):
        _set_month(ws, metric_code=metric_code, year=year, month=m, value=value)


def _set_year_cell(ws, *, label: str, year: int, value) -> None:
    """Set the Year-column cell of the row labelled `label` for `year`."""
    row = _row_for(ws, label)
    ystart = _year_block(ws, year)
    ws.cell(row=row, column=ystart + workbook._YEAR_OFFSET).value = value


def _year_cell(ws, *, label: str, year: int):
    row = _row_for(ws, label)
    ystart = _year_block(ws, year)
    return ws.cell(row=row, column=ystart + workbook._YEAR_OFFSET).value


def _current(repo, agency_slug, period, code, mode_code=None):
    """The current 'total' value for (agency, period, metric[, mode]), or None."""
    agency_id = repo.agency_id(agency_slug)
    pid = repo.get_or_create_reporting_period(
        period.period_type, period.start, period.end, period.label
    )
    mode_id = repo.mode_id(mode_code)
    return repo.get_current_metric_value(agency_id, repo.metric_id(code), pid, mode_id, "total")


# --- structure ---------------------------------------------------------------


def test_export_creates_one_tab_per_agency(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    summary = workbook.export_workbook(repo, out, [2023, 2024])

    assert summary["agencies"] == 21
    assert summary["fleet_modes"] == 5
    assert summary["metric_rows"] == len(workbook.METRIC_ROWS)

    wb = _load(out)
    # Two reference tabs, then one tab per agency in AGENCY_NAMES order.
    assert wb.sheetnames == (
        [workbook.SHEET_HOWTO, workbook.SHEET_DICT] + list(workbook.AGENCY_NAMES.values())
    )


def test_agency_tab_has_year_blocks_and_month_subheaders(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023, 2024])
    ws = _load(out)["TTC"]

    # Two year-block headers.
    assert ws.cell(row=workbook._YEAR_HEADER_ROW, column=_year_block(ws, 2023)).value == 2023
    assert ws.cell(row=workbook._YEAR_HEADER_ROW, column=_year_block(ws, 2024)).value == 2024

    # The 18 within-year sub-headers, in order.
    ystart = _year_block(ws, 2023)
    labels = [
        ws.cell(row=workbook._SUBHEADER_ROW, column=ystart + off).value
        for off in range(workbook.YEAR_BLOCK_WIDTH)
    ]
    assert labels == [
        "Jan", "Feb", "Mar", "Q1", "Apr", "May", "Jun", "Q2",
        "Jul", "Aug", "Sep", "Q3", "Oct", "Nov", "Dec", "Q4", "YTD", "Year",
    ]


def test_quarter_year_and_derived_cells_are_formulas(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])
    ws = _load(out)["TTC"]
    ystart = _year_block(ws, 2023)

    rid_row = _row_for(ws, NAMES["ridership"])
    # Q1 and Year on a monthly metric are live SUM formulas.
    q1 = ws.cell(row=rid_row, column=ystart + workbook._QUARTER_OFFSETS[0]).value
    yr = ws.cell(row=rid_row, column=ystart + workbook._YEAR_OFFSET).value
    assert isinstance(q1, str) and q1.startswith("=") and "SUM(" in q1
    assert isinstance(yr, str) and yr.startswith("=") and "SUM(" in yr

    # average_fare's Year cell is a live ratio formula (numerator / denominator).
    af = _year_cell(ws, label=NAMES["average_fare"], year=2023)
    assert isinstance(af, str) and af.startswith("=") and "/" in af


def test_fleet_block_present_with_modes_and_scale(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])
    ws = _load(out)["TTC"]

    for _mode, label in workbook.FLEET_MODES:
        _row_for(ws, f"Fleet — {label}")  # raises if missing
    scale = _year_cell(ws, label="Fleet scale", year=2023)
    assert isinstance(scale, str) and scale.startswith("=")  # computed Fleet scale


def test_dictionary_lists_all_metrics(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])
    ws = _load(out)[workbook.SHEET_DICT]

    assert [c.value for c in ws[1]] == [
        "Column", "Plain meaning", "Unit", "Type", "Formula", "Native frequency",
    ]
    assert ws.max_row - 1 == 32  # all metrics, including fleet_capacity + balance sheet
    by_name = {ws.cell(row=r, column=1).value: r for r in range(2, ws.max_row + 1)}
    assert ws.cell(row=by_name[NAMES["ridership"]], column=6).value == "Monthly"
    assert ws.cell(row=by_name[NAMES["operating_expenses"]], column=6).value == "Annual"


# --- round trips -------------------------------------------------------------


def test_monthly_round_trip_rolls_up_and_derives_average_fare(repo, tmp_path):
    """12 months of ridership + revenue roll up to the year; average fare derives."""
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    ws = wb["TTC"]
    # Use agency-scale numbers: monthly revenue must clear the currency floor
    # (validation.flags._CURRENCY_FLOOR) or it is flagged and never auto-promoted.
    _fill_year_of_months(ws, metric_code="ridership", year=2023, value=10000)
    _fill_year_of_months(ws, metric_code="operating_revenue", year=2023, value=25000)
    wb.save(out)

    summary = workbook.import_workbook(repo, out)
    assert summary["promoted"] == 24  # 12 months x 2 metrics
    # 2 native annuals + the 4 calendar quarters each metric also rolls up (the
    # annual_calendar slot is already filled by the native roll-up, so it is skipped).
    assert summary["rolled"] == 10

    ap = annual_period("ttc", 2023)
    assert _current(repo, "ttc", ap, "ridership").value == Decimal("120000")
    assert _current(repo, "ttc", ap, "operating_revenue").value == Decimal("300000")
    assert _current(repo, "ttc", ap, "average_fare").value == Decimal("2.5")


def test_partial_months_land_as_monthly_values(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    ws = wb["TTC"]
    _set_month(ws, metric_code="ridership", year=2023, month=1, value=42)
    wb.save(out)

    workbook.import_workbook(repo, out)
    jan = monthly_period(2023, 1)
    assert _current(repo, "ttc", jan, "ridership").value == Decimal("42")


def test_annual_white_cell_round_trip(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    # Agency-scale dollars: below the currency floor a value is flagged and not promoted.
    _set_year_cell(wb["TTC"], label=NAMES["operating_expenses"], year=2023, value=8000000)
    wb.save(out)

    workbook.import_workbook(repo, out)
    ap = annual_period("ttc", 2023)
    assert _current(repo, "ttc", ap, "operating_expenses").value == Decimal("8000000")


def test_balance_sheet_dollars_not_comparable_and_net_debt_derived(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    ws = wb["TTC"]
    # Agency-scale dollars: below the currency floor a value is flagged and not promoted.
    _set_year_cell(ws, label=NAMES["total_liabilities"], year=2023, value=500000000)
    _set_year_cell(ws, label=NAMES["total_financial_assets"], year=2023, value=200000000)
    wb.save(out)

    workbook.import_workbook(repo, out)
    ap = annual_period("ttc", 2023)

    liab = _current(repo, "ttc", ap, "total_liabilities")
    assert liab.value == Decimal("500000000")
    assert liab.comparable_flag is False  # raw balance-sheet dollars are never ranked

    nd = _current(repo, "ttc", ap, "net_debt")
    assert nd.value == Decimal("300000000")  # server-derived 500M-200M
    assert nd.comparable_flag is False


def test_fiscal_agency_imports_under_fiscal_period(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    # Metrolinx (March year-end): the 2023 column maps to its FY2023-24 period.
    # Agency-scale dollars: below the currency floor a value is flagged and not promoted.
    _set_year_cell(wb["Metrolinx"], label=NAMES["operating_expenses"], year=2023, value=7000000)
    wb.save(out)

    workbook.import_workbook(repo, out)
    ap = annual_period("metrolinx", 2023)
    assert ap.period_type == "annual_fiscal" and ap.label == "FY2023-24"
    assert _current(repo, "metrolinx", ap, "operating_expenses").value == Decimal("7000000")


def test_year_header_label_is_fiscal_for_fiscal_agency_and_plain_for_calendar(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])
    wb = _load(out)

    # Fiscal agency: the block header literally reads the fiscal label.
    mx = wb["Metrolinx"]
    mx_col = _year_block(mx, 2023)
    assert mx.cell(row=workbook._YEAR_HEADER_ROW, column=mx_col).value == "FY2023-24"

    # Calendar agency: still a bare integer.
    ttc = wb["TTC"]
    ttc_col = _year_block(ttc, 2023)
    assert ttc.cell(row=workbook._YEAR_HEADER_ROW, column=ttc_col).value == 2023


def test_per_mode_fleet_imports_with_mode_id_and_aggregates_capacity(repo, tmp_path):
    """Typed per-mode fleet rows land as fleet_size at the right mode_id; the server
    aggregates them into fleet_capacity (the grey Fleet-scale cell is not imported)."""
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    ws = wb["TTC"]
    _set_year_cell(ws, label="Fleet — Bus", year=2023, value=100)
    _set_year_cell(ws, label="Fleet — Subway", year=2023, value=10)
    # Bogus number typed into the grey Fleet-scale cell: must be ignored.
    _set_year_cell(ws, label="Fleet scale", year=2023, value=99999)
    wb.save(out)

    workbook.import_workbook(repo, out)
    ap = annual_period("ttc", 2023)

    assert _current(repo, "ttc", ap, "fleet_size", mode_code="bus").value == Decimal("100")
    assert _current(repo, "ttc", ap, "fleet_size", mode_code="subway").value == Decimal("10")
    # fleet_capacity = 1*100 (bus) + 4*10 (subway) = 140, derived server-side; the
    # typed 99999 is ignored because that cell is never imported.
    cap = _current(repo, "ttc", ap, "fleet_capacity")
    assert cap is not None and cap.value == Decimal("140")
    assert cap.mode_id is None  # a system-wide aggregate, not a per-mode row


def test_grey_computed_cells_are_not_imported(repo, tmp_path):
    """Typing into a grey Q/Year/derived cell is ignored; the server recomputes."""
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    ws = wb["TTC"]
    # Agency-scale numbers so monthly revenue clears the currency floor.
    _fill_year_of_months(ws, metric_code="ridership", year=2023, value=10000)
    _fill_year_of_months(ws, metric_code="operating_revenue", year=2023, value=25000)
    # Bogus number typed over the grey ridership Year roll-up cell + derived ratio.
    _set_year_cell(ws, label=NAMES["ridership"], year=2023, value=5)
    _set_year_cell(ws, label=NAMES["average_fare"], year=2023, value=999)
    wb.save(out)

    workbook.import_workbook(repo, out)
    ap = annual_period("ttc", 2023)
    # Roll-up (120000), not the typed 5; derived (2.5), not the typed 999.
    assert _current(repo, "ttc", ap, "ridership").value == Decimal("120000")
    assert _current(repo, "ttc", ap, "average_fare").value == Decimal("2.5")


def test_non_numeric_cell_warns_and_skips(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    _set_year_cell(wb["TTC"], label=NAMES["operating_expenses"], year=2023, value="not-a-number")
    wb.save(out)

    summary = workbook.import_workbook(repo, out)
    assert any("non-numeric" in w for w in summary["warnings"])
    assert _current(repo, "ttc", annual_period("ttc", 2023), "operating_expenses") is None
