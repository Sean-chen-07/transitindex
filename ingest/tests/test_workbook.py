"""Round-trip tests for the period-aware six-sheet workbook.

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
from transitindex_ingest.periods import annual_period, monthly_period, quarterly_period

NAMES = {c: s.display_name for c, s in load_dictionary().items()}


# --- helpers -----------------------------------------------------------------


def _load(path):
    return openpyxl.load_workbook(path, data_only=False)


def _header(ws) -> list:
    return [c.value for c in ws[1]]


def _col_index(ws) -> dict:
    """Header name -> 1-based column index."""
    return {h: i + 1 for i, h in enumerate(_header(ws)) if h is not None}


def _fill_row(ws, *, agency: str, period, updates: dict) -> int:
    """Set `updates` (header name -> value) on the row matching (agency, period)."""
    idx = _col_index(ws)
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == agency and ws.cell(row=r, column=2).value == period:
            for head, value in updates.items():
                ws.cell(row=r, column=idx[head]).value = value
            return r
    raise AssertionError(f"row not found for {agency!r} / {period!r}")


def _set_period(ws, *, agency: str, old_period, new_period) -> None:
    """Overwrite the Period token on an (agency, old_period) row (e.g. -> quarterly)."""
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == agency and ws.cell(row=r, column=2).value == old_period:
            ws.cell(row=r, column=2).value = new_period
            return
    raise AssertionError(f"row not found for {agency!r} / {old_period!r}")


def _fill_monthly(ws, *, agency: str, year: int, ridership=None, revenue=None) -> None:
    """Set ridership / operating-revenue for every (agency, year) month row."""
    idx = _col_index(ws)
    for r in range(2, ws.max_row + 1):
        if ws.cell(row=r, column=1).value == agency and ws.cell(row=r, column=2).value == year:
            if ridership is not None:
                ws.cell(row=r, column=idx[NAMES["ridership"]]).value = ridership
            if revenue is not None:
                ws.cell(row=r, column=idx[NAMES["operating_revenue"]]).value = revenue


def _current(repo, agency_slug, period, code):
    """The current 'total' value for (agency, period, metric), or None."""
    agency_id = repo.agency_id(agency_slug)
    pid = repo.get_or_create_reporting_period(
        period.period_type, period.start, period.end, period.label
    )
    return repo.get_current_metric_value(agency_id, repo.metric_id(code), pid, None, "total")


# --- structure ---------------------------------------------------------------


def test_export_creates_six_sheets_with_headers(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    summary = workbook.export_workbook(repo, out, [2023, 2024])

    assert summary["agencies"] == 21
    assert summary["monthly_rows"] == 21 * 2 * 12
    assert summary["annual_rows"] == 21 * 2

    wb = _load(out)
    assert wb.sheetnames == [
        workbook.SHEET_HOWTO, workbook.SHEET_DICT, workbook.SHEET_MONTHLY,
        workbook.SHEET_ANNUAL, workbook.SHEET_BALANCE, workbook.SHEET_GAPS,
    ]
    assert _header(wb[workbook.SHEET_MONTHLY]) == [
        "Agency", "Year", "Month", NAMES["ridership"], NAMES["operating_revenue"],
    ]
    assert _header(wb[workbook.SHEET_ANNUAL]) == (
        ["Agency", "Period"] + [NAMES[c] for c in workbook.ANNUAL_COLUMNS]
    )
    assert _header(wb[workbook.SHEET_BALANCE]) == (
        ["Agency", "Period"]
        + [NAMES[c] for c in workbook.BALANCE_SHEET_SOURCED]
        + [NAMES["net_debt"], "Check: Assets", "Check: Net debt"]
    )


def test_dictionary_lists_all_31_metrics_with_routing(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])
    ws = _load(out)[workbook.SHEET_DICT]

    assert _header(ws) == [
        "Column", "Plain meaning", "Unit", "Type", "Formula",
        "Native frequency", "Sheet",
    ]
    assert ws.max_row - 1 == 31  # all metrics, including the 11 balance-sheet ones

    # Routing columns send the user to the right tab.
    by_name = {ws.cell(row=r, column=1).value: r for r in range(2, ws.max_row + 1)}
    rid = by_name[NAMES["ridership"]]
    assert ws.cell(row=rid, column=6).value == "Monthly"
    assert ws.cell(row=rid, column=7).value == workbook.SHEET_MONTHLY
    liab = by_name[NAMES["total_liabilities"]]
    assert ws.cell(row=liab, column=7).value == workbook.SHEET_BALANCE


def test_annual_derived_and_balance_checks_are_formulas(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])
    wb = _load(out)

    annual = wb[workbook.SHEET_ANNUAL]
    idx = _col_index(annual)
    # Every derived ratio cell is a live formula referencing this row.
    for code in workbook.ANNUAL_DERIVED_METRICS:
        val = annual.cell(row=2, column=idx[NAMES[code]]).value
        assert isinstance(val, str) and val.startswith("=")
    af = annual.cell(row=2, column=idx[NAMES["average_fare"]]).value
    assert "/" in af  # average fare references its numerator / denominator columns

    balance = wb[workbook.SHEET_BALANCE]
    bidx = _col_index(balance)
    assert str(balance.cell(row=2, column=bidx[NAMES["net_debt"]]).value).startswith("=")
    assert "MISMATCH" in balance.cell(row=2, column=bidx["Check: Assets"]).value
    assert str(balance.cell(row=2, column=bidx["Check: Net debt"]).value).startswith("=")


# --- round trips -------------------------------------------------------------


def test_monthly_round_trip_rolls_up_and_derives_average_fare(repo, tmp_path):
    """12 months of ridership + revenue roll up to the year; average fare derives."""
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    _fill_monthly(wb[workbook.SHEET_MONTHLY], agency="TTC", year=2023, ridership=100, revenue=250)
    wb.save(out)

    summary = workbook.import_workbook(repo, out)
    assert summary["promoted"] == 24  # 12 months x 2 metrics
    assert summary["rolled"] == 2  # annual ridership + annual revenue

    ap = annual_period("ttc", 2023)
    assert _current(repo, "ttc", ap, "ridership").value == Decimal("1200")
    assert _current(repo, "ttc", ap, "operating_revenue").value == Decimal("3000")
    assert _current(repo, "ttc", ap, "average_fare").value == Decimal("2.5")


def test_annual_fundamentals_white_cell_round_trip(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    _fill_row(
        wb[workbook.SHEET_ANNUAL],
        agency="TTC", period="2023",
        updates={NAMES["operating_expenses"]: 8000},
    )
    wb.save(out)

    workbook.import_workbook(repo, out)
    ap = annual_period("ttc", 2023)
    assert _current(repo, "ttc", ap, "operating_expenses").value == Decimal("8000")


def test_balance_sheet_dollars_not_comparable_and_net_debt_derived(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    _fill_row(
        wb[workbook.SHEET_BALANCE],
        agency="TTC", period="2023",
        updates={
            NAMES["total_liabilities"]: 500,
            NAMES["total_financial_assets"]: 200,
            NAMES["net_debt"]: 999,  # grey cell: must be ignored on import
        },
    )
    wb.save(out)

    workbook.import_workbook(repo, out)
    ap = annual_period("ttc", 2023)

    liab = _current(repo, "ttc", ap, "total_liabilities")
    assert liab.value == Decimal("500")
    assert liab.comparable_flag is False  # raw balance-sheet dollars are never ranked

    nd = _current(repo, "ttc", ap, "net_debt")
    assert nd.value == Decimal("300")  # server-derived 500-200, not the typed 999
    assert nd.comparable_flag is False


def test_fiscal_agency_imports_under_fiscal_period(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    ws = wb[workbook.SHEET_ANNUAL]
    # Metrolinx (March year-end) -> Period pre-filled as 'FY2023-24'.
    _fill_row(ws, agency="Metrolinx", period="FY2023-24",
              updates={NAMES["operating_expenses"]: 7000})
    wb.save(out)

    workbook.import_workbook(repo, out)
    ap = annual_period("metrolinx", 2023)
    assert ap.period_type == "annual_fiscal" and ap.label == "FY2023-24"
    assert _current(repo, "metrolinx", ap, "operating_expenses").value == Decimal("7000")


def test_quarterly_token_imports_under_quarterly_period(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2024])

    wb = _load(out)
    ws = wb[workbook.SHEET_BALANCE]
    # TransLink: a user types a quarterly token for its quarterly statement.
    _set_period(ws, agency="TransLink", old_period="2024", new_period="2024-Q1")
    _fill_row(ws, agency="TransLink", period="2024-Q1",
              updates={NAMES["total_assets"]: 900})
    wb.save(out)

    workbook.import_workbook(repo, out)
    qp = quarterly_period(2024, 1)
    landed = _current(repo, "translink", qp, "total_assets")
    assert landed is not None and landed.value == Decimal("900")


def test_grey_cells_are_not_imported(repo, tmp_path):
    """Typing into a grey roll-up / derived cell is ignored; the server recomputes."""
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    _fill_monthly(wb[workbook.SHEET_MONTHLY], agency="TTC", year=2023, ridership=100, revenue=250)
    # Bogus numbers typed into grey Annual cells (roll-up + derived).
    _fill_row(
        wb[workbook.SHEET_ANNUAL],
        agency="TTC", period="2023",
        updates={NAMES["ridership"]: 5, NAMES["average_fare"]: 999},
    )
    wb.save(out)

    workbook.import_workbook(repo, out)
    ap = annual_period("ttc", 2023)
    # Roll-up (1200), not the typed 5; derived (2.5), not the typed 999.
    assert _current(repo, "ttc", ap, "ridership").value == Decimal("1200")
    assert _current(repo, "ttc", ap, "average_fare").value == Decimal("2.5")


def test_malformed_period_token_warns_and_skips(repo, tmp_path):
    out = str(tmp_path / "wb.xlsx")
    workbook.export_workbook(repo, out, [2023])

    wb = _load(out)
    ws = wb[workbook.SHEET_ANNUAL]
    _set_period(ws, agency="TTC", old_period="2023", new_period="twenty-twenty-three")
    _fill_row(ws, agency="TTC", period="twenty-twenty-three",
              updates={NAMES["operating_expenses"]: 1234})
    wb.save(out)

    summary = workbook.import_workbook(repo, out)
    assert any("unreadable Period" in w for w in summary["warnings"])
    # The bad row contributed nothing.
    assert _current(repo, "ttc", annual_period("ttc", 2023), "operating_expenses") is None
