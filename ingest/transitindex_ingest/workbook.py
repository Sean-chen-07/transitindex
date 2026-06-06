"""Spreadsheet round-trip: export an editable .xlsx, import it back.

This is the manual-entry path for a NON-TECHNICAL editor (city staff). It turns
the database into a friendly Excel workbook they can fill by hand, then reads
that workbook back into the pipeline.

The workbook is **period-aware**, six sheets (balance-sheet-and-frequency-plan.md §4):
  1. "How to use"          -- plain-language instructions, "Which tab?", the
                              Period token, and the colour legend.
  2. "Data Dictionary"     -- one row per metric (all 31), what each means, its
                              unit, formula, native frequency, and which sheet it
                              lives on.
  3. "Monthly"             -- fast-moving ridership + operating revenue, one row
                              per (agency, year, month). Resolved at a monthly
                              period; the server rolls them up to the year.
  4. "Annual Fundamentals" -- one row per (agency, Period). The 12 annual sourced
                              metrics are typed in (white); ridership/revenue ride
                              along as the grey annual ROLL-UP cell; the 6 derived
                              ratios are grey live Excel formulas.
  5. "Balance Sheet"       -- one row per (agency, Period). The 8 PSAB line items
                              are typed in (white); net_debt + two accounting
                              "check" columns are grey live formulas.
  6. "Gaps"                -- live =COUNT of filled cells per (agency, period)
                              across sheets 3-5, plus the newest month present.

Colours: white = type here · grey = calculated / do-not-touch · light-yellow =
optional / quarterly-only. Every grey cell is recomputed on the server, so import
reads ONLY the white cells (never a grey/derived/roll-up cell) and never fabricates
a blank. The server's bidirectional solver is the source of truth for every
derived and back-solved value; the Excel formulas are a live entry aid only.

One **Period text token** keys the annual sheets: `2024` (calendar), `FY2024-25`
(fiscal), or `2024-Q1` (TransLink quarterly). Export pre-fills the right token per
agency (from fiscal_year_end_month); import parses it back to a reporting period.

Display names + plain meanings come from the per-metric data dictionary
(`dictionary.load_dictionary()`), the single source of truth for both. openpyxl
AND PyYAML are imported LAZILY inside export/import, so merely importing this
module never requires either; everything else is pure stdlib.
"""

from __future__ import annotations

import re

from .equations import RatioEquation, defining_equation
from .refdata import METRICS, NON_RANKABLE_METRICS

# --- Metric groupings (routing), agency names --------------------------------

# The 11-metric balance-sheet family (PSAB). Kept for ROUTING -- which sheet a
# metric lives on -- no longer to EXCLUDE these metrics from the workbook.
BALANCE_SHEET_METRICS: frozenset[str] = frozenset({
    "total_financial_assets", "total_liabilities", "total_non_financial_assets",
    "total_assets", "tangible_capital_assets", "accumulated_surplus",
    "long_term_debt", "cash_and_investments",
    "net_debt", "debt_to_assets", "net_debt_per_capita",
})

# The two monthly-native feeds (StatCan 23-10-0307 publishes both): typed on the
# Monthly sheet, shown as the grey annual ROLL-UP cell on Annual Fundamentals.
MONTHLY_METRICS: list[str] = ["ridership", "operating_revenue"]

# Annual Fundamentals columns: the 14 non-balance-sheet sourced (in METRICS order,
# ridership/revenue included as grey roll-up), then the 6 derived (grey formulas).
ANNUAL_SOURCED_METRICS: list[str] = [
    c for c, m in METRICS.items() if not m["is_derived"] and c not in BALANCE_SHEET_METRICS
]
ANNUAL_DERIVED_METRICS: list[str] = [
    c for c, m in METRICS.items() if m["is_derived"] and c not in BALANCE_SHEET_METRICS
]
ANNUAL_COLUMNS: list[str] = ANNUAL_SOURCED_METRICS + ANNUAL_DERIVED_METRICS
# The 12 typed-in annual sourced metrics (everything sourced except the two that
# roll up from the Monthly sheet).
ANNUAL_WHITE_METRICS: list[str] = [c for c in ANNUAL_SOURCED_METRICS if c not in MONTHLY_METRICS]

# Balance Sheet: the 8 sourced line items (white). net_debt is shown as a grey
# formula; the two ranked ratios are computed server-side and never entered here.
BALANCE_SHEET_SOURCED: list[str] = [
    c for c, m in METRICS.items() if c in BALANCE_SHEET_METRICS and not m["is_derived"]
]
_NET_DEBT = "net_debt"
_WEBSITE_ONLY: frozenset[str] = frozenset({"debt_to_assets", "net_debt_per_capita"})

# Agency slug -> short name, in workbook row order (= reverse-lookup map on import).
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
    # expansion agencies
    "winnipeg-transit": "Winnipeg Transit",
    "hamilton-street-railway": "HSR",
    "brampton-transit": "Brampton Transit",
    "grand-river-transit": "GRT",
    "stl-laval": "STL",
    "rtl-longueuil": "RTL",
    "york-region-transit": "YRT",
    "halifax-transit": "Halifax Transit",
    "durham-region-transit": "DRT",
    "saskatoon-transit": "Saskatoon Transit",
    "regina-transit": "Regina Transit",
}

# Sheet names (single source of truth for both export and import).
SHEET_HOWTO = "How to use"
SHEET_DICT = "Data Dictionary"
SHEET_MONTHLY = "Monthly"
SHEET_ANNUAL = "Annual Fundamentals"
SHEET_BALANCE = "Balance Sheet"
SHEET_GAPS = "Gaps"

# Fills (ARGB). White = no fill.
_GREY = "FFD9D9D9"
_YELLOW = "FFFFF2CC"  # light yellow: optional / quarterly-only


def _native_frequency(code: str) -> str:
    return "Monthly" if code in MONTHLY_METRICS else "Annual"


def _sheet_for(code: str) -> str:
    """Which sheet a metric is ENTERED on (routes the user in the dictionary)."""
    if code in MONTHLY_METRICS:
        return SHEET_MONTHLY
    if code in BALANCE_SHEET_METRICS:
        if code in _WEBSITE_ONLY:
            return "— (calculated on the website)"
        return SHEET_BALANCE
    return SHEET_ANNUAL


# --- Formula plumbing (driven off the equation catalog so it can't drift) -----


def _operand_name(code: str, names: dict[str, str]) -> str:
    """Human label for a formula operand; humanizes `attr:` agency attributes."""
    if code.startswith("attr:"):
        return code[len("attr:"):].replace("_", " ").strip().capitalize()
    return names.get(code, code)


def _plain_formula(code: str, names: dict[str, str]) -> str:
    """Human-readable formula for a derived metric, e.g. 'Operating Revenue /
    Ridership' -- built from the equation catalog the solver uses."""
    eq = defining_equation(code)
    if isinstance(eq, RatioEquation):
        return f"{_operand_name(eq.numerator, names)} / {_operand_name(eq.denominator, names)}"
    parts: list[str] = []
    for i, (sign, term) in enumerate(eq.terms):
        op = " - " if sign < 0 else (" + " if i else "")
        parts.append(f"{op}{_operand_name(term, names)}")
    return "".join(parts).strip()


def _excel_unit_format(code: str) -> str:
    """openpyxl number_format string chosen from the metric's unit/unit_type."""
    meta = METRICS[code]
    unit, unit_type = meta["unit"], meta["unit_type"]
    if unit_type == "currency":
        return '#,##0.00'  # dollars; no symbol so CAD / CAD-per-hour read cleanly
    if unit == "%":
        return '#,##0.0'  # stored as a percentage number (e.g. 92.5), not a fraction
    if unit_type == "count":
        return '#,##0'
    return '#,##0.00'  # hours, km, years, ratios


def _cell(col: int, row: int) -> str:
    """Absolute-column cell ref ($G2 style) that survives copy/fill."""
    from openpyxl.utils import get_column_letter

    return f"${get_column_letter(col)}{row}"


def _derived_excel_formula(code: str, row: int, col_of: dict[str, int]) -> str:
    """Build the live Excel formula for a derived cell in `row`.

    Mirrors the equation catalog: blank ("") when any input cell is empty OR a
    ratio denominator is zero, else the ratio/sum. Column letters come from
    `col_of` (metric code -> 1-based column index); never hardcoded. An operand
    that isn't a column on this sheet (e.g. net_debt_per_capita's
    service_area_population, an agency attribute) can't be a live formula -> the
    cell stays blank and the server recompute is the source of truth for it.
    """
    eq = defining_equation(code)
    if isinstance(eq, RatioEquation):
        needed = [eq.numerator, eq.denominator]
    else:
        needed = [t for _s, t in eq.terms]
    if any(c not in col_of for c in needed):
        return ""

    def ref(c: str) -> str:
        return _cell(col_of[c], row)

    if isinstance(eq, RatioEquation):
        num, den = ref(eq.numerator), ref(eq.denominator)
        return f'=IF(OR({num}="",{den}="",{den}=0),"",{num}/{den})'

    # SumEquation (e.g. net_debt = total_liabilities - total_financial_assets).
    cells = [ref(t) for _s, t in eq.terms]
    guard = "OR(" + ",".join(f'{c}=""' for c in cells) + ")"
    parts: list[str] = []
    for i, (sign, term) in enumerate(eq.terms):
        op = "-" if sign < 0 else ("+" if i else "")
        parts.append(f"{op}{ref(term)}")
    return f'=IF({guard},"",{"".join(parts)})'


def _check_assets_formula(row: int, col_of: dict[str, int]) -> str:
    """Asset-split identity: total_assets == financial + non-financial (0.5% tol)."""
    tfa = _cell(col_of["total_financial_assets"], row)
    tnfa = _cell(col_of["total_non_financial_assets"], row)
    ta = _cell(col_of["total_assets"], row)
    # Guard total_assets too (beyond the spec's tfa/tnfa) so a missing total never
    # shows a #VALUE! error to a non-technical user -- blank when any input is missing.
    return (
        f'=IF(OR({tfa}="",{tnfa}="",{ta}=""),"",'
        f'IF(ABS(({tfa}+{tnfa})-{ta})<=ABS({ta})*0.005,"OK","MISMATCH"))'
    )


def _check_netdebt_formula(row: int, col_of: dict[str, int]) -> str:
    """Net-debt identity beside the printed cell: liabilities - financial assets."""
    liab = _cell(col_of["total_liabilities"], row)
    tfa = _cell(col_of["total_financial_assets"], row)
    return f'=IF(OR({liab}="",{tfa}=""),"",{liab}-{tfa})'


# --- Period token (one resolver) ---------------------------------------------

_RE_QUARTER = re.compile(r"^(\d{4})-Q([1-4])$")
_RE_FISCAL = re.compile(r"^FY(\d{4})-(\d{2})$")
_RE_YEAR = re.compile(r"^(\d{4})$")


def _parse_period_token(token: object, agency_slug: str):
    """Parse a Period text token into a reporting Period. Raises on a bad token.

    `2024-Q3` -> quarterly_period; `FY2024-25` / `2024` -> annual_period (the
    agency's fiscal_year_end_month decides calendar vs fiscal). Never guesses.
    """
    from .periods import annual_period, quarterly_period

    t = str(token).strip()
    m = _RE_QUARTER.match(t)
    if m:
        return quarterly_period(int(m.group(1)), int(m.group(2)))
    m = _RE_FISCAL.match(t)
    if m:
        start_year = int(m.group(1))
        expected = (start_year + 1) % 100
        if int(m.group(2)) != expected:
            raise ValueError(
                f"unreadable Period {t!r} for {agency_slug}: fiscal end-year "
                f"should be {expected:02d} (e.g. FY{start_year}-{expected:02d})"
            )
        return annual_period(agency_slug, start_year)
    m = _RE_YEAR.match(t)
    if m:
        return annual_period(agency_slug, int(m.group(1)))
    raise ValueError(
        f"unreadable Period {t!r} for {agency_slug}: expected '2024', "
        "'FY2024-25', or '2024-Q1'"
    )


# --- DB read helpers (pre-fill from current values) --------------------------


def _period_index(repo) -> dict:
    """Existing reporting periods keyed by (period_type, start, end) -> period.

    Lets export pre-fill from current values WITHOUT creating empty periods."""
    return {
        (p.period_type, p.start_date, p.end_date): p
        for p in repo.list_reporting_periods()
    }


def _read_total_values(repo, agency_id: int, period_id: int, codes) -> dict[str, object]:
    """Current system-wide ('total', mode_id None) values for `codes` at a period."""
    by_mid = {repo.metric_id(c): c for c in codes}
    out: dict[str, object] = {}
    for v in repo.list_current_values_for_agency_period(agency_id, period_id):
        if v.mode_id is not None or v.service_scope != "total":
            continue
        code = by_mid.get(v.metric_id)
        if code is not None:
            out[code] = v.value
    return out


# --- Export ------------------------------------------------------------------


def export_workbook(repo, path: str, years: list[int]) -> dict:
    """Build the six-sheet editable workbook and save it to `path`.

    Pre-fills white cells from current DB values (and ridership/revenue from their
    annual roll-up) where present; the DB is empty at MVP so this usually fills
    nothing -- expected. Returns a summary dict with per-sheet row counts.
    """
    from openpyxl import Workbook

    from .dictionary import load_dictionary

    specs = load_dictionary()
    names = {c: s.display_name for c, s in specs.items()}
    meanings = {c: s.plain_meaning for c, s in specs.items()}
    index = _period_index(repo)

    wb = Workbook()
    _build_howto_sheet(wb)  # replaces the default sheet
    _build_dictionary_sheet(wb, names, meanings)
    filled = 0
    filled += _build_monthly_sheet(wb, years, names, repo, index)
    filled += _build_annual_sheet(wb, years, names, repo, index)
    filled += _build_balance_sheet(wb, years, names, repo, index)
    _build_gaps_sheet(wb, years, names)

    wb.save(path)

    n_agencies = len(AGENCY_NAMES)
    n_years = len(years)
    return {
        "path": path,
        "agencies": n_agencies,
        "years": list(years),
        "monthly_rows": n_agencies * n_years * 12,
        "annual_rows": n_agencies * n_years,
        "balance_rows": n_agencies * n_years,
        "filled_cells": filled,
    }


def _build_howto_sheet(wb) -> None:
    """Sheet 1: plain-language instructions; reuses the default first sheet."""
    from openpyxl.styles import Alignment, Font, PatternFill

    ws = wb.active
    ws.title = SHEET_HOWTO
    ws.sheet_view.showGridLines = False

    lines: list[tuple[str, bool]] = [
        ("How to use this workbook", True),
        ("", False),
        ("This workbook collects transit numbers. You type real figures into the "
         "WHITE cells, taken straight from your source (an annual report, a budget, "
         "an open-data file). Leave a cell BLANK if you don't have the number yet -- "
         "never guess. The website shows the last known number for you, so a blank "
         "here is fine.", False),
        ("", False),
        ("Which tab do I use?", True),
        ("- Monthly: month-by-month ridership and fare revenue. Type each month you "
         "have; the yearly total is worked out for you.", False),
        ("- Annual Fundamentals: the once-a-year operating numbers (service hours, "
         "costs, fleet, and so on), one row per agency per year.", False),
        ("- Balance Sheet: the agency's once-a-year financial position (assets, "
         "liabilities), from the audited financial statements.", False),
        ("- Data Dictionary: look up exactly what any column means and which tab to "
         "type it on.", False),
        ("- Gaps: see, at a glance, how many numbers are still missing.", False),
        ("", False),
        ("The colour code", True),
        ("- WHITE cells: type here.", False),
        ("- GREY cells: worked out automatically (totals, ratios, checks). Don't "
         "type in them -- anything you put there is ignored and recalculated.", False),
        ("- LIGHT-YELLOW cells: optional, only needed for the rare quarterly case. "
         "A blank one is perfectly normal.", False),
        ("", False),
        ("The Period column", True),
        ("On the Annual Fundamentals and Balance Sheet tabs, each row has a Period. "
         "It is filled in for you:", False),
        ("- 2024 means the calendar year 2024 (most agencies).", False),
        ("- FY2024-25 means a financial year ending in spring 2025 (Metrolinx and "
         "BC Transit, whose year ends in March).", False),
        ("- 2024-Q1 means the first quarter of 2024 -- only TransLink reports its "
         "balance sheet this often. You'd type this in yourself for that rare case.",
         False),
        ("", False),
        ("When you're done", True),
        ("Save the file and run the import command. Your numbers go into the "
         "database; the grey totals, ratios, and checks are recomputed on the "
         "server -- you don't need to worry about them.", False),
    ]
    for i, (text, bold) in enumerate(lines, start=1):
        cell = ws.cell(row=i, column=1, value=text)
        cell.font = Font(bold=bold, size=14 if (bold and i == 1) else 11)
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    # A light-yellow swatch beside the legend line so the colour is concrete.
    ws.cell(row=16, column=2, value="example").fill = PatternFill(
        start_color=_YELLOW, end_color=_YELLOW, fill_type="solid"
    )
    ws.column_dimensions["A"].width = 100
    ws.column_dimensions["B"].width = 12


def _build_dictionary_sheet(wb, names: dict[str, str], meanings: dict[str, str]) -> None:
    """Sheet 2: one row per metric (all 31) -- meaning, unit, type, formula, and
    the two routing columns (Native frequency, Sheet)."""
    from openpyxl.styles import Alignment, Font

    ws = wb.create_sheet(SHEET_DICT)
    headers = ["Column", "Plain meaning", "Unit", "Type", "Formula",
               "Native frequency", "Sheet"]
    for col, head in enumerate(headers, start=1):
        ws.cell(row=1, column=col, value=head).font = Font(bold=True)

    row = 2
    for code, meta in METRICS.items():
        is_derived = meta["is_derived"]
        ws.cell(row=row, column=1, value=names[code])
        ws.cell(row=row, column=2, value=meanings[code])
        ws.cell(row=row, column=3, value=meta["unit"])
        ws.cell(row=row, column=4, value="Calculated" if is_derived else "Sourced")
        ws.cell(row=row, column=5, value=_plain_formula(code, names) if is_derived else "")
        ws.cell(row=row, column=6, value=_native_frequency(code))
        ws.cell(row=row, column=7, value=_sheet_for(code))
        row += 1

    ws.freeze_panes = "A2"
    for col_letter, width in (
        ("A", 28), ("B", 55), ("C", 10), ("D", 12), ("E", 38), ("F", 16), ("G", 22)
    ):
        ws.column_dimensions[col_letter].width = width
    for r in range(2, row):
        ws.cell(row=r, column=2).alignment = Alignment(wrap_text=True, vertical="top")


def _build_monthly_sheet(wb, years, names, repo, index) -> int:
    """Sheet 3: month-by-month ridership + operating revenue (white). Returns the
    number of cells pre-filled from the DB."""
    from openpyxl.styles import Alignment, Font

    from .periods import monthly_period

    ws = wb.create_sheet(SHEET_MONTHLY)
    bold = Font(bold=True)
    headers = ["Agency", "Year", "Month"] + [names[c] for c in MONTHLY_METRICS]
    for col, head in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=head)
        cell.font = bold
        cell.alignment = Alignment(wrap_text=True, vertical="bottom")
    col_of = {code: 4 + i for i, code in enumerate(MONTHLY_METRICS)}  # 4, 5

    filled = 0
    row = 2
    for slug, short_name in AGENCY_NAMES.items():
        agency_id = repo.agency_id(slug)
        for year in years:
            for month in range(1, 13):
                mp = monthly_period(year, month)
                period = index.get((mp.period_type, mp.start, mp.end))
                values = (
                    _read_total_values(repo, agency_id, period.id, MONTHLY_METRICS)
                    if period is not None else {}
                )
                ws.cell(row=row, column=1, value=short_name)
                ws.cell(row=row, column=2, value=int(year))
                ws.cell(row=row, column=3, value=month)
                for code in MONTHLY_METRICS:
                    cell = ws.cell(row=row, column=col_of[code])
                    cell.number_format = _excel_unit_format(code)
                    if code in values:
                        cell.value = float(values[code])
                        filled += 1
                row += 1

    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:{_col(col_of[MONTHLY_METRICS[-1]])}{row - 1}"
    for letter, width in (("A", 20), ("B", 8), ("C", 8)):
        ws.column_dimensions[letter].width = width
    for code in MONTHLY_METRICS:
        ws.column_dimensions[_col(col_of[code])].width = 18
    return filled


def _build_annual_sheet(wb, years, names, repo, index) -> int:
    """Sheet 4: annual fundamentals -- 12 white sourced + grey roll-up
    ridership/revenue + 6 grey derived formulas. Returns pre-filled cell count."""
    from openpyxl.styles import Alignment, Font, PatternFill

    from .periods import annual_period

    ws = wb.create_sheet(SHEET_ANNUAL)
    grey = PatternFill(start_color=_GREY, end_color=_GREY, fill_type="solid")
    bold = Font(bold=True)
    col_of = {code: 3 + i for i, code in enumerate(ANNUAL_COLUMNS)}

    ws.cell(row=1, column=1, value="Agency").font = bold
    ws.cell(row=1, column=2, value="Period").font = bold
    for code in ANNUAL_COLUMNS:
        cell = ws.cell(row=1, column=col_of[code], value=names[code])
        cell.font = bold
        cell.alignment = Alignment(wrap_text=True, vertical="bottom")
        if METRICS[code]["is_derived"] or code in MONTHLY_METRICS:
            cell.fill = grey  # derived formulas + roll-up cells are do-not-touch

    filled = 0
    row = 2
    for slug, short_name in AGENCY_NAMES.items():
        agency_id = repo.agency_id(slug)
        for year in years:
            ap = annual_period(slug, year)
            period = index.get((ap.period_type, ap.start, ap.end))
            values = (
                _read_total_values(repo, agency_id, period.id, ANNUAL_SOURCED_METRICS)
                if period is not None else {}
            )
            ws.cell(row=row, column=1, value=short_name)
            ws.cell(row=row, column=2, value=ap.label)  # pre-filled Period token

            for code in ANNUAL_COLUMNS:
                cell = ws.cell(row=row, column=col_of[code])
                cell.number_format = _excel_unit_format(code)
                if METRICS[code]["is_derived"]:
                    cell.value = _derived_excel_formula(code, row, col_of)
                    cell.fill = grey
                elif code in MONTHLY_METRICS:
                    # Grey annual ROLL-UP cell: show the rolled value if present,
                    # never re-entered (the Monthly sheet is where it's typed).
                    cell.fill = grey
                    if code in values:
                        cell.value = float(values[code])
                        filled += 1
                else:
                    if code in values:  # 12 white sourced columns
                        cell.value = float(values[code])
                        filled += 1
            row += 1

    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{_col(col_of[ANNUAL_COLUMNS[-1]])}{row - 1}"
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 12
    for code in ANNUAL_COLUMNS:
        ws.column_dimensions[_col(col_of[code])].width = 16
    return filled


def _build_balance_sheet(wb, years, names, repo, index) -> int:
    """Sheet 5: balance sheet -- 8 white sourced lines + grey net_debt + two grey
    check columns. Returns pre-filled cell count."""
    from openpyxl.styles import Alignment, Font, PatternFill

    from .periods import annual_period

    ws = wb.create_sheet(SHEET_BALANCE)
    grey = PatternFill(start_color=_GREY, end_color=_GREY, fill_type="solid")
    bold = Font(bold=True)

    metric_cols = BALANCE_SHEET_SOURCED + [_NET_DEBT]
    col_of = {code: 3 + i for i, code in enumerate(metric_cols)}
    check_assets_col = 3 + len(metric_cols)
    check_netdebt_col = check_assets_col + 1
    last_col = check_netdebt_col

    ws.cell(row=1, column=1, value="Agency").font = bold
    ws.cell(row=1, column=2, value="Period").font = bold
    for code in metric_cols:
        cell = ws.cell(row=1, column=col_of[code], value=names[code])
        cell.font = bold
        cell.alignment = Alignment(wrap_text=True, vertical="bottom")
        if code == _NET_DEBT:
            cell.fill = grey
    for col, head in ((check_assets_col, "Check: Assets"), (check_netdebt_col, "Check: Net debt")):
        cell = ws.cell(row=1, column=col, value=head)
        cell.font = bold
        cell.alignment = Alignment(wrap_text=True, vertical="bottom")
        cell.fill = grey

    filled = 0
    row = 2
    for slug, short_name in AGENCY_NAMES.items():
        agency_id = repo.agency_id(slug)
        for year in years:
            ap = annual_period(slug, year)
            period = index.get((ap.period_type, ap.start, ap.end))
            values = (
                _read_total_values(repo, agency_id, period.id, BALANCE_SHEET_SOURCED)
                if period is not None else {}
            )
            ws.cell(row=row, column=1, value=short_name)
            ws.cell(row=row, column=2, value=ap.label)

            for code in BALANCE_SHEET_SOURCED:
                cell = ws.cell(row=row, column=col_of[code])
                cell.number_format = _excel_unit_format(code)
                if code in values:
                    cell.value = float(values[code])
                    filled += 1

            nd = ws.cell(row=row, column=col_of[_NET_DEBT])
            nd.value = _derived_excel_formula(_NET_DEBT, row, col_of)
            nd.number_format = _excel_unit_format(_NET_DEBT)
            nd.fill = grey

            ca = ws.cell(row=row, column=check_assets_col, value=_check_assets_formula(row, col_of))
            ca.fill = grey
            cn = ws.cell(row=row, column=check_netdebt_col, value=_check_netdebt_formula(row, col_of))
            cn.number_format = _excel_unit_format(_NET_DEBT)
            cn.fill = grey
            row += 1

    ws.freeze_panes = "C2"
    ws.auto_filter.ref = f"A1:{_col(last_col)}{row - 1}"
    ws.column_dimensions["A"].width = 20
    ws.column_dimensions["B"].width = 12
    for col in range(3, last_col + 1):
        ws.column_dimensions[_col(col)].width = 18
    return filled


def _build_gaps_sheet(wb, years, names) -> None:
    """Sheet 6: live =COUNT of filled cells per (agency, period) across sheets 3-5,
    plus the newest month present per agency. All formulas, so never stale."""
    from openpyxl.styles import Font

    ws = wb.create_sheet(SHEET_GAPS)
    bold = Font(bold=True)
    n_years = len(years)
    rid_col = _col(4)  # ridership column on the Monthly sheet

    annual_white_cols = [_annual_col(c) for c in ANNUAL_WHITE_METRICS]
    first_bs = _col(3)
    last_bs = _col(2 + len(BALANCE_SHEET_SOURCED))

    row = 1
    ws.cell(row=row, column=1, value="What's still missing").font = bold
    row += 2

    # Newest month present per agency (live MAXIFS over the Monthly sheet).
    ws.cell(row=row, column=1, value="Newest year with monthly ridership").font = bold
    row += 1
    for col, head in ((1, "Agency"), (2, "Newest year")):
        ws.cell(row=row, column=col, value=head).font = bold
    row += 1
    for short_name in AGENCY_NAMES.values():
        ws.cell(row=row, column=1, value=short_name)
        maxifs = (
            f"MAXIFS('{SHEET_MONTHLY}'!B:B,'{SHEET_MONTHLY}'!A:A,A{row},"
            f"'{SHEET_MONTHLY}'!{rid_col}:{rid_col},\"<>\")"
        )
        ws.cell(row=row, column=2, value=f'=IF({maxifs}=0,"",{maxifs})')
        row += 1
    row += 1

    # Monthly coverage: months filled (of 12) per (agency, year).
    ws.cell(row=row, column=1, value="Monthly: months filled (of 12)").font = bold
    row += 1
    for col, head in ((1, "Agency"), (2, "Year"), (3, "Months filled")):
        ws.cell(row=row, column=col, value=head).font = bold
    row += 1
    for ai, short_name in enumerate(AGENCY_NAMES.values()):
        for yi, year in enumerate(years):
            start = 2 + (ai * n_years + yi) * 12
            ws.cell(row=row, column=1, value=short_name)
            ws.cell(row=row, column=2, value=int(year))
            rng = f"'{SHEET_MONTHLY}'!{rid_col}{start}:{rid_col}{start + 11}"
            ws.cell(row=row, column=3, value=f"=COUNT({rng})")
            row += 1
    row += 1

    # Annual Fundamentals: filled (of 12) per (agency, period).
    ws.cell(row=row, column=1, value=f"Annual Fundamentals: filled (of {len(ANNUAL_WHITE_METRICS)})").font = bold
    row += 1
    for col, head in ((1, "Agency"), (2, "Period"), (3, "Filled")):
        ws.cell(row=row, column=col, value=head).font = bold
    row += 1
    for ai, short_name in enumerate(AGENCY_NAMES.values()):
        for yi, year in enumerate(years):
            data_row = 2 + (ai * n_years + yi)
            ws.cell(row=row, column=1, value=short_name)
            ws.cell(row=row, column=2, value=f"='{SHEET_ANNUAL}'!B{data_row}")
            cells = ",".join(f"'{SHEET_ANNUAL}'!{c}{data_row}" for c in annual_white_cols)
            ws.cell(row=row, column=3, value=f"=COUNT({cells})")
            row += 1
    row += 1

    # Balance Sheet: filled (of 8) per (agency, period).
    ws.cell(row=row, column=1, value=f"Balance Sheet: filled (of {len(BALANCE_SHEET_SOURCED)})").font = bold
    row += 1
    for col, head in ((1, "Agency"), (2, "Period"), (3, "Filled")):
        ws.cell(row=row, column=col, value=head).font = bold
    row += 1
    for ai, short_name in enumerate(AGENCY_NAMES.values()):
        for yi, year in enumerate(years):
            data_row = 2 + (ai * n_years + yi)
            ws.cell(row=row, column=1, value=short_name)
            ws.cell(row=row, column=2, value=f"='{SHEET_BALANCE}'!B{data_row}")
            rng = f"'{SHEET_BALANCE}'!{first_bs}{data_row}:{last_bs}{data_row}"
            ws.cell(row=row, column=3, value=f"=COUNT({rng})")
            row += 1

    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = 14
    ws.column_dimensions["C"].width = 14


def _col(idx: int) -> str:
    from openpyxl.utils import get_column_letter

    return get_column_letter(idx)


def _annual_col(code: str) -> str:
    """Column letter of a metric on the Annual Fundamentals sheet."""
    return _col(3 + ANNUAL_COLUMNS.index(code))


# --- Import ------------------------------------------------------------------


def import_workbook(repo, path: str) -> dict:
    """Read the white cells of the three entry sheets and push them through the
    pipeline.

    Dispatches each sheet's rows to the right period builder and service scope,
    stages them (tier 0, feed 'manual_entry'), promotes, rolls monthly
    ridership/revenue up to the year, recomputes derived ratios for every touched
    (agency, period) -- including the annual periods the roll-up created -- then
    refreshes ranks. Grey cells (derived, roll-up, checks) are never read; blank
    cells are skipped (never fabricated). Returns counts plus any warnings.
    """
    from decimal import Decimal, InvalidOperation

    from openpyxl import load_workbook

    from .contract import MetricValueRecord, SourceRef
    from .dictionary import load_dictionary
    from .jobs.derived_recompute import recompute_derived
    from .jobs.rank_refresh import refresh_ranks
    from .jobs.rollup import rollup_metric
    from .periods import monthly_period
    from .promotion import promote_approved
    from .staging import stage_records

    names = {c: s.display_name for c, s in load_dictionary().items()}
    slug_of = {name: slug for slug, name in AGENCY_NAMES.items()}
    source = SourceRef(
        document_type="manual_entry",
        extraction_method="manual",
        title="Manual entry (workbook import)",
    )
    wb = load_workbook(path, data_only=False)
    warnings: list[str] = []
    records: list[MetricValueRecord] = []
    monthly_agency_years: set[tuple[str, int]] = set()

    def resolve_slug(agency_name) -> "str | None":
        if agency_name is None:
            return None
        slug = slug_of.get(str(agency_name).strip())
        if slug is None:
            warnings.append(f"unknown agency name: {agency_name!r}")
        return slug

    def as_decimal(cell, code, agency_name, period_label):
        try:
            return Decimal(str(cell))
        except (InvalidOperation, ValueError):
            warnings.append(
                f"non-numeric {names[code]} for {agency_name} {period_label}: {cell!r}"
            )
            return None

    def add_record(slug, code, period, value):
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
                # Balance-sheet dollars measure size, not performance -> never ranked.
                comparable_flag=code not in NON_RANKABLE_METRICS,
                source=source,
            )
        )

    def columns_for(ws, codes) -> dict[int, str]:
        name_to_code = {names[c]: c for c in codes}
        header = [c.value for c in ws[1]]
        return {i: name_to_code[h] for i, h in enumerate(header) if h in name_to_code}

    # --- Monthly sheet -> monthly_period(year, month) ------------------------
    if SHEET_MONTHLY in wb.sheetnames:
        ws = wb[SHEET_MONTHLY]
        cols = columns_for(ws, MONTHLY_METRICS)
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row:
                continue
            slug = resolve_slug(row[0] if len(row) > 0 else None)
            if slug is None or len(row) < 3:
                continue
            try:
                year, month = int(row[1]), int(row[2])
                period = monthly_period(year, month)
            except (TypeError, ValueError):
                warnings.append(f"unreadable Year/Month {row[1]!r}/{row[2]!r} for {row[0]}")
                continue
            for ci, code in cols.items():
                if ci >= len(row) or row[ci] is None or row[ci] == "":
                    continue
                value = as_decimal(row[ci], code, row[0], period.label)
                if value is not None:
                    add_record(slug, code, period, value)
            monthly_agency_years.add((slug, year))

    # --- Annual Fundamentals + Balance Sheet -> Period token -----------------
    for sheet_name, codes in (
        (SHEET_ANNUAL, ANNUAL_WHITE_METRICS),
        (SHEET_BALANCE, BALANCE_SHEET_SOURCED),
    ):
        if sheet_name not in wb.sheetnames:
            continue
        ws = wb[sheet_name]
        cols = columns_for(ws, codes)
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row:
                continue
            slug = resolve_slug(row[0] if len(row) > 0 else None)
            token = row[1] if len(row) > 1 else None
            if slug is None or token is None or token == "":
                continue
            try:
                period = _parse_period_token(token, slug)
            except ValueError as exc:
                warnings.append(str(exc))
                continue
            for ci, code in cols.items():
                if ci >= len(row) or row[ci] is None or row[ci] == "":
                    continue
                value = as_decimal(row[ci], code, row[0], period.label)
                if value is not None:
                    add_record(slug, code, period, value)

    # --- Orchestration: stage -> promote -> roll up -> recompute -> rank -----
    pending_ids = stage_records(repo, records, tier=0, feed_code="manual_entry")
    promoted = promote_approved(repo)

    periods: set[int] = set()
    agency_periods: set[tuple[str, int]] = set()
    for r in records:
        pid = repo.get_or_create_reporting_period(
            r.period_type, r.period_start, r.period_end, r.period_label
        )
        periods.add(pid)
        agency_periods.add((r.agency_slug, pid))

    # Roll monthly ridership + revenue up to the year BEFORE recompute, so annual
    # ratios (average_fare, ...) derive from the rolled-up annual inputs.
    rolled = 0
    for slug, year in sorted(monthly_agency_years):
        for code in MONTHLY_METRICS:
            written = rollup_metric(repo, slug, year, code)
            rolled += len(written.value_ids)
            for pid in written.period_ids:
                periods.add(pid)
                agency_periods.add((slug, pid))

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
        "rolled": rolled,
        "derived": derived,
        "periods": len(periods),
        "warnings": warnings,
    }
