"""Offline round-trip tests for the .xlsx workbook (export + import).

Pure stdlib + pytest on the InMemoryRepository -- no live DB. The suite is
skipped wholesale when openpyxl is absent (the workbook module imports it
lazily, so the rest of the package still works without it).
"""

from __future__ import annotations

import pytest

openpyxl = pytest.importorskip("openpyxl")

from transitindex_ingest import workbook
from transitindex_ingest.periods import annual_period


def _data_header(path: str) -> list:
    """The Data sheet header row, as a list of cell values."""
    wb = openpyxl.load_workbook(path, data_only=False)
    ws = wb[workbook._SHEET_DATA]
    return [cell.value for cell in ws[1]]


def _current(repo, agency_slug: str, year: int, code: str):
    """The current 'total' system-wide value for (agency, year, metric), or None."""
    period = annual_period(agency_slug, year)
    agency_id = repo.agency_id(agency_slug)
    period_id = repo.get_or_create_reporting_period(
        agency_id, period.period_type, period.start, period.end, period.label
    )
    return repo.get_current_metric_value(
        agency_id, repo.metric_id(code), period_id, None, "total"
    )


# --- export -----------------------------------------------------------------


def test_export_creates_file_with_four_sheets_and_header(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    summary = workbook.export_workbook(repo, out, [2023, 2024])

    assert summary["path"] == out
    assert summary["agencies"] == 10
    assert summary["rows"] == 20  # 10 agencies x 2 years

    wb = openpyxl.load_workbook(out, data_only=False)
    assert wb.sheetnames == [
        workbook._SHEET_HOWTO,
        workbook._SHEET_DICT,
        workbook._SHEET_DATA,
        workbook._SHEET_GAPS,
    ]

    expected = (
        ["Agency", "Year"]
        + [workbook.DISPLAY_NAMES[c] for c in workbook.SOURCED_METRICS]
        + [workbook.DISPLAY_NAMES[c] for c in workbook.DERIVED_METRICS]
    )
    assert _data_header(out) == expected


def test_derived_columns_hold_formulas_not_numbers(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = openpyxl.load_workbook(out, data_only=False)
    ws = wb[workbook._SHEET_DATA]
    header = [cell.value for cell in ws[1]]

    # Locate the columns we care about (1-based).
    fare_col = header.index(workbook.DISPLAY_NAMES["average_fare"]) + 1
    rev_letter = openpyxl.utils.get_column_letter(
        header.index(workbook.DISPLAY_NAMES["operating_revenue"]) + 1
    )
    rid_letter = openpyxl.utils.get_column_letter(
        header.index(workbook.DISPLAY_NAMES["annual_ridership"]) + 1
    )

    # Every derived column in the first data row (row 2) is a formula.
    for code in workbook.DERIVED_METRICS:
        col = header.index(workbook.DISPLAY_NAMES[code]) + 1
        value = ws.cell(row=2, column=col).value
        assert isinstance(value, str) and value.startswith("=")

    # average_fare = operating_revenue / annual_ridership: the formula must
    # reference both source columns in the same row.
    fare_formula = ws.cell(row=2, column=fare_col).value
    assert f"{rev_letter}2" in fare_formula
    assert f"{rid_letter}2" in fare_formula


# --- round trip -------------------------------------------------------------


def test_round_trip_imports_sourced_and_recomputes_derived(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    # Reopen and type real numbers into a couple of rows.
    wb = openpyxl.load_workbook(out, data_only=False)
    ws = wb[workbook._SHEET_DATA]
    header = [cell.value for cell in ws[1]]
    agency_col = 1
    rev_col = header.index(workbook.DISPLAY_NAMES["operating_revenue"]) + 1
    rid_col = header.index(workbook.DISPLAY_NAMES["annual_ridership"]) + 1

    # Find the TTC and Metrolinx data rows (year is 2023 for all rows here).
    rows_by_agency = {}
    for r in range(2, ws.max_row + 1):
        name = ws.cell(row=r, column=agency_col).value
        if name is not None:
            rows_by_agency[name] = r

    ttc_row = rows_by_agency[workbook.AGENCY_NAMES["ttc"]]
    mx_row = rows_by_agency[workbook.AGENCY_NAMES["metrolinx"]]

    ws.cell(row=ttc_row, column=rev_col, value=2500)
    ws.cell(row=ttc_row, column=rid_col, value=1000)
    ws.cell(row=mx_row, column=rev_col, value=6000)
    ws.cell(row=mx_row, column=rid_col, value=2000)
    wb.save(out)

    summary = workbook.import_workbook(repo, out)
    assert summary["promoted"] == 4  # 2 metrics x 2 agencies

    # Sourced values landed.
    from decimal import Decimal

    assert _current(repo, "ttc", 2023, "operating_revenue").value == Decimal("2500")
    assert _current(repo, "ttc", 2023, "annual_ridership").value == Decimal("1000")

    # average_fare = operating_revenue / annual_ridership was recomputed & stored.
    ttc_fare = _current(repo, "ttc", 2023, "average_fare")
    assert ttc_fare is not None
    assert ttc_fare.value == Decimal("2.5")  # 2500 / 1000

    mx_fare = _current(repo, "metrolinx", 2023, "average_fare")
    assert mx_fare is not None
    assert mx_fare.value == Decimal("3")  # 6000 / 2000


def test_derived_columns_are_not_imported_as_sourced(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = openpyxl.load_workbook(out, data_only=False)
    ws = wb[workbook._SHEET_DATA]
    header = [cell.value for cell in ws[1]]
    rev_col = header.index(workbook.DISPLAY_NAMES["operating_revenue"]) + 1
    rid_col = header.index(workbook.DISPLAY_NAMES["annual_ridership"]) + 1
    fare_col = header.index(workbook.DISPLAY_NAMES["average_fare"]) + 1

    ttc_row = None
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == workbook.AGENCY_NAMES["ttc"]:
            ttc_row = r
            break

    # Type a bogus number straight into the Average Fare (derived) column.
    ws.cell(row=ttc_row, column=rev_col, value=2500)
    ws.cell(row=ttc_row, column=rid_col, value=1000)
    ws.cell(row=ttc_row, column=fare_col, value=999)  # should be ignored
    wb.save(out)

    workbook.import_workbook(repo, out)

    from decimal import Decimal

    # Only the recomputed value exists (2.5), never the bogus 999.
    fare = _current(repo, "ttc", 2023, "average_fare")
    assert fare is not None
    assert fare.value == Decimal("2.5")


def test_fiscal_mapping_metrolinx_imports_under_fiscal_period(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = openpyxl.load_workbook(out, data_only=False)
    ws = wb[workbook._SHEET_DATA]
    header = [cell.value for cell in ws[1]]
    rid_col = header.index(workbook.DISPLAY_NAMES["annual_ridership"]) + 1

    mx_row = None
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == workbook.AGENCY_NAMES["metrolinx"]:
            mx_row = r
            break
    ws.cell(row=mx_row, column=rid_col, value=5000)
    wb.save(out)

    workbook.import_workbook(repo, out)

    # Metrolinx (fiscal-year-end March) maps year 2023 to an annual_fiscal
    # period labelled FY2023-24.
    period = annual_period("metrolinx", 2023)
    assert period.period_type == "annual_fiscal"
    assert period.label == "FY2023-24"

    from decimal import Decimal

    value = _current(repo, "metrolinx", 2023, "annual_ridership")
    assert value is not None
    assert value.value == Decimal("5000")
