"""Generate the US agency seed + refdata mirror from NTD snapshot CSVs.

Run from the repo root AFTER `python ingest/scripts/fetch_ntd.py`:

    python ingest/scripts/generate_ntd_agencies.py

Inputs (from fetch_ntd.py, committed under db/seeds/ntd/):
  * db/seeds/ntd/ntd_monthly.csv — Full Reporter rows; supplies reporter
    selection (any non-empty UPT within the last 12 data months), the active
    mode set, and the state.
  * db/seeds/ntd/ntd_annual.csv  — supplies the display name for the latest
    report year (falls back to the monthly `agency` name).
  * db/seeds/ntd/ntd_agency_info.csv — supplies each reporter's fiscal-year end
    (`fy_end_date`), which becomes fiscal_year_end_month.

Outputs (BOTH committed):
  * db/seeds/08_agencies_us.sql            — core.agencies + core.agency_modes
  * ingest/transitindex_ingest/refdata_us.py — US_AGENCIES + NTD_AGENCY_MAP

Deterministic and slug-preserving: an ntd_id already present in the existing
refdata_us.NTD_AGENCY_MAP keeps its slug forever (slugs are public URLs);
new agencies get slugify(name)-<state>, with -<ntd_id> appended on collision.
fiscal_year_end_month comes from the Agency Information snapshot's fy_end_date;
a reporter missing from that snapshot falls back to 12 (calendar year).
Stdlib only.
"""

from __future__ import annotations

import csv
import re
import sys
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MONTHLY_CSV = REPO_ROOT / "db" / "seeds" / "ntd" / "ntd_monthly.csv"
ANNUAL_CSV = REPO_ROOT / "db" / "seeds" / "ntd" / "ntd_annual.csv"
AGENCY_INFO_CSV = REPO_ROOT / "db" / "seeds" / "ntd" / "ntd_agency_info.csv"
SEED_OUT = REPO_ROOT / "db" / "seeds" / "08_agencies_us.sql"
REFDATA_OUT = REPO_ROOT / "ingest" / "transitindex_ingest" / "refdata_us.py"

sys.path.insert(0, str(REPO_ROOT / "ingest"))
from transitindex_ingest.refdata import AGENCIES, MODES  # noqa: E402
from transitindex_ingest.refdata_us import NTD_AGENCY_MAP as EXISTING_MAP  # noqa: E402

# NTD mode code -> repo mode code (core.modes). Unknown codes are reported and
# dropped. MG (monorail / automated guideway people-movers) is classed as
# light_rail — a judgment call, documented here.
NTD_MODE_MAP: dict[str, str] = {
    "MB": "bus", "CB": "bus", "PB": "bus",
    "RB": "brt",
    "TB": "trolleybus",
    "HR": "subway",
    "LR": "light_rail", "MG": "light_rail",
    "SR": "streetcar", "CC": "streetcar", "IP": "streetcar",
    "CR": "commuter_rail", "YR": "commuter_rail", "AR": "commuter_rail",
    "FB": "ferry",
    "DR": "paratransit", "DT": "paratransit",
    "VP": "on_demand", "TN": "on_demand", "TX": "on_demand",
    # TR (aerial tramway) intentionally dropped — no repo mode fits.
}
DROPPED_MODES = {"TR"}

# Fallback fiscal-year end for a reporter absent from the Agency Information
# snapshot (a handful): calendar year. Reported as a count when it happens.
DEFAULT_FY_END_MONTH = 12

US_SUBDIVISIONS = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC", "PR", "VI", "GU", "AS", "MP",
}


def slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", text)


def sql_quote(text: str) -> str:
    return "'" + text.replace("'", "''") + "'"


def read_fy_end_months(path: Path) -> dict[str, int]:
    """ntd_id -> fiscal-year end month, from the Agency Information snapshot.

    `fy_end_date` is an ISO timestamp ("2024-06-30T00:00:00.000"); the month is
    what core.agencies.fiscal_year_end_month stores. A reporter listed more than
    once (several reporting modules) resolves to its latest fy_end_date, so the
    result is deterministic.
    """
    latest: dict[str, str] = {}
    with path.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            ntd_id = (row.get("ntd_id") or "").strip()
            raw = (row.get("fy_end_date") or "").strip()
            if len(raw) < 7 or not ntd_id:
                continue
            if raw > latest.get(ntd_id, ""):
                latest[ntd_id] = raw
    return {ntd_id: int(raw[5:7]) for ntd_id, raw in latest.items()}


def main() -> int:
    if not MONTHLY_CSV.exists() or not ANNUAL_CSV.exists() or not AGENCY_INFO_CSV.exists():
        print(
            f"missing snapshot CSVs under {MONTHLY_CSV.parent} — run "
            "`python ingest/scripts/fetch_ntd.py` first",
            file=sys.stderr,
        )
        return 1

    # --- monthly: reporter selection + modes + state -------------------------
    months_seen: set[str] = set()
    rows = []
    with MONTHLY_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if (row.get("reporter_type") or "").strip() != "Full Reporter":
                continue
            month = (row.get("date") or "")[:7]
            if len(month) == 7:
                months_seen.add(month)
            rows.append(row)
    if not months_seen:
        print("no data months found in the monthly CSV", file=sys.stderr)
        return 1
    recent = set(sorted(months_seen)[-12:])

    active: dict[str, dict] = {}  # ntd_id -> {name, state, modes}
    unknown_modes: set[str] = set()
    for row in rows:
        month = (row.get("date") or "")[:7]
        if month not in recent:
            continue
        if (row.get("upt") or "").strip() == "":
            continue
        ntd_id = (row.get("ntd_id") or "").strip()
        if not ntd_id:
            continue
        entry = active.setdefault(
            ntd_id,
            {
                "name": (row.get("agency") or "").strip(),
                "state": (row.get("state") or "").strip().upper(),
                "modes": set(),
            },
        )
        ntd_mode = (row.get("mode") or "").strip().upper()
        mapped = NTD_MODE_MAP.get(ntd_mode)
        if mapped:
            entry["modes"].add(mapped)
        elif ntd_mode and ntd_mode not in DROPPED_MODES:
            unknown_modes.add(ntd_mode)

    if unknown_modes:
        print(f"WARNING: unmapped NTD mode codes dropped: {sorted(unknown_modes)}")

    # --- annual: preferred display names (latest report year wins) -----------
    annual_names: dict[str, tuple[int, str]] = {}
    with ANNUAL_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            ntd_id = (row.get("ntd_id") or "").strip()
            year_raw = (row.get("report_year") or "").strip()
            name = (row.get("agency") or "").strip()
            if not (ntd_id and year_raw.isdigit() and name):
                continue
            year = int(year_raw)
            if ntd_id not in annual_names or year > annual_names[ntd_id][0]:
                annual_names[ntd_id] = (year, name)

    # --- agency information: fiscal-year end month ---------------------------
    fy_end_months = read_fy_end_months(AGENCY_INFO_CSV)

    # --- assign slugs (preserve existing; disambiguate collisions) -----------
    canadian_slugs = set(AGENCIES)
    taken: set[str] = set(canadian_slugs) | set(EXISTING_MAP.values())
    assigned: dict[str, str] = dict(EXISTING_MAP)  # ntd_id -> slug (preserved)
    agencies: dict[str, dict] = {}

    skipped_states = []
    for ntd_id in sorted(active):
        meta = active[ntd_id]
        name = annual_names.get(ntd_id, (0, ""))[1] or meta["name"]
        state = meta["state"]
        if state not in US_SUBDIVISIONS:
            skipped_states.append((ntd_id, name, state))
            continue
        modes = tuple(m for m in MODES if m in meta["modes"])  # canonical order
        if not modes:
            modes = ("bus",)  # every Full Reporter runs something; degenerate fallback
        slug = assigned.get(ntd_id)
        if slug is None:
            slug = f"{slugify(name)}-{state.lower()}"
            if slug in taken:
                slug = f"{slug}-{ntd_id}"
            assigned[ntd_id] = slug
        taken.add(slug)
        agencies[slug] = {
            "ntd_id": ntd_id,
            "legal_name": name,
            "subdivision": state,
            "modes": modes,
            "fiscal_year_end_month": fy_end_months.get(ntd_id, DEFAULT_FY_END_MONTH),
        }
    missing_fy = [s for s in sorted(agencies) if agencies[s]["ntd_id"] not in fy_end_months]
    if missing_fy:
        print(
            f"WARNING: {len(missing_fy)} agency/agencies absent from the Agency Information "
            f"snapshot — fiscal_year_end_month defaulted to {DEFAULT_FY_END_MONTH}:"
        )
        for slug in missing_fy:
            print(f"  {agencies[slug]['ntd_id']} {slug}")
    if skipped_states:
        print(f"WARNING: {len(skipped_states)} reporter(s) with unrecognized state skipped:")
        for ntd_id, name, state in skipped_states:
            print(f"  {ntd_id} {name!r} state={state!r}")

    ordered = sorted(agencies)

    # --- emit db/seeds/08_agencies_us.sql ------------------------------------
    lines = [
        "-- Seed: US Full Reporter agencies from the FTA National Transit Database.",
        "-- GENERATED by ingest/scripts/generate_ntd_agencies.py — do not hand-edit.",
        "-- Selection: reporter_type='Full Reporter' with UPT reported in the last",
        "-- 12 data months of the committed monthly snapshot (db/seeds/ntd/).",
        "-- service_area_population left NULL (not fabricated); fiscal_year_end_month",
        "-- comes from the Agency Information snapshot's fy_end_date (12 if absent).",
        "-- Re-runnable (ON CONFLICT DO NOTHING / idempotent UPDATE).",
        "SET client_encoding = 'UTF8';",
        "",
        "INSERT INTO core.agencies (slug, legal_name, short_name, country, subdivision, fiscal_year_end_month, currency, primary_modes) VALUES",
    ]
    value_rows = []
    for slug in ordered:
        a = agencies[slug]
        modes_sql = ",".join(f"'{m}'" for m in a["modes"])
        value_rows.append(
            f"  ({sql_quote(slug)}, {sql_quote(a['legal_name'])}, NULL, 'US', "
            f"'{a['subdivision']}', {a['fiscal_year_end_month']}, 'USD', ARRAY[{modes_sql}])"
        )
    lines.append(",\n".join(value_rows))
    lines.append("ON CONFLICT (slug) DO NOTHING;")
    lines.append("")
    lines.append("UPDATE core.agencies AS a SET ntd_id = v.ntd_id")
    lines.append("FROM (VALUES")
    lines.append(
        ",\n".join(
            f"  ({sql_quote(slug)}, '{agencies[slug]['ntd_id']}')" for slug in ordered
        )
    )
    lines.append(") AS v(slug, ntd_id)")
    lines.append("WHERE a.slug = v.slug AND a.ntd_id IS DISTINCT FROM v.ntd_id;")
    lines.append("")
    lines.append("INSERT INTO core.agency_modes (agency_id, mode_id, status)")
    lines.append("SELECT a.id, m.id, 'active'")
    lines.append("FROM core.agencies a")
    lines.append("JOIN core.modes m ON true")
    lines.append("WHERE (a.slug, m.code) IN (VALUES")
    mode_rows = []
    for slug in ordered:
        for mode in agencies[slug]["modes"]:
            mode_rows.append(f"  ({sql_quote(slug)}, '{mode}')")
    lines.append(",\n".join(mode_rows))
    lines.append(")")
    lines.append("ON CONFLICT (agency_id, mode_id) DO NOTHING;")
    lines.append("")
    SEED_OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {SEED_OUT} ({len(ordered)} agencies)")

    # --- emit refdata_us.py ---------------------------------------------------
    py = [
        '"""US agency reference data — GENERATED, do not hand-edit.',
        "",
        "Produced by `python ingest/scripts/generate_ntd_agencies.py` from the",
        "committed NTD snapshots under db/seeds/ntd/. Mirrors",
        "db/seeds/08_agencies_us.sql exactly; re-running the generator preserves",
        "the existing slug of every ntd_id it has seen before (slugs are",
        "permanent URLs).",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from types import MappingProxyType",
        "from typing import Mapping",
        "",
        "# slug -> {subdivision (2-letter state), fiscal_year_end_month (NTD fy_end_date),",
        "#          country, ntd_id, primary_modes}. Same shape as refdata.AGENCIES",
        "#          plus country/currency/ntd_id.",
        "US_AGENCIES: Mapping[str, Mapping] = MappingProxyType(",
        "    {",
    ]
    for slug in ordered:
        a = agencies[slug]
        modes_py = ", ".join(f'"{m}"' for m in a["modes"])
        trailing = "," if len(a["modes"]) == 1 else ""
        py.append(f'        "{slug}": MappingProxyType(')
        py.append(
            f'            {{"subdivision": "{a["subdivision"]}", '
            f'"fiscal_year_end_month": {a["fiscal_year_end_month"]},'
        )
        py.append(
            f'             "currency": "USD", "country": "US", "ntd_id": "{a["ntd_id"]}",'
        )
        py.append(f'             "primary_modes": ({modes_py}{trailing})}}')
        py.append("        ),")
    py.append("    }")
    py.append(")")
    py.append("")
    py.append('# NTD ID (5-digit zero-padded string, e.g. "00001") -> agency slug.')
    py.append("NTD_AGENCY_MAP: Mapping[str, str] = MappingProxyType(")
    py.append("    {")
    for ntd_id in sorted(a["ntd_id"] for a in agencies.values()):
        slug = next(s for s in ordered if agencies[s]["ntd_id"] == ntd_id)
        py.append(f'        "{ntd_id}": "{slug}",')
    py.append("    }")
    py.append(")")
    py.append("")
    REFDATA_OUT.write_text("\n".join(py), encoding="utf-8")
    print(f"wrote {REFDATA_OUT} ({len(ordered)} agencies)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
