import type { PaidMetricView } from "@/server/metrics/types";

/**
 * Pure (no DB, no React) model for the per-metric calendar-year time-series grid.
 * It only reshapes the values ALREADY on PaidMetricView.trend — it never reads a raw
 * table, so it stays on the paid side of the choke point by construction (its only
 * input is a PaidMetricView, produced solely by access.ts on a revealed render).
 *
 * Trend labels follow ingest/periods.py exactly:
 *   monthly         "Mar 2026"
 *   quarterly       "2024-Q1"
 *   annual_calendar "2024"
 *   annual_fiscal   "FY2024-25"
 *   ytd             "2025 YTD (Jan–Aug)"  /  "FY2025-26 YTD (Apr–Aug)"
 * Anything unrecognized is dropped (never guessed into a cell).
 */

const MONTH_ABBR = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
] as const;

type TrendPoint = PaidMetricView["trend"][number];

/** One cell: a value plus whether it is a derived roll-up (Q / YTD / Year). */
export interface GridCell {
  value: number;
  periodLabel: string;
  derived: boolean;
}

export interface GridRow {
  /** Calendar year shown in the row header (fiscal years key on their START year). */
  year: number;
  /** 12 month cells (index 0 = Jan); null where a month is missing. */
  months: (GridCell | null)[];
  /** 4 quarterly subtotals (index 0 = Q1); null when absent. */
  quarters: (GridCell | null)[];
  /** Partial year-to-date roll-up, when present. */
  ytd: GridCell | null;
  /** Full-year figure (annual_calendar or annual_fiscal). */
  year_total: GridCell | null;
  /** True when the year's full figure is a fiscal (not calendar) year. */
  fiscal: boolean;
}

function ensureRow(rows: Map<number, GridRow>, year: number): GridRow {
  let row = rows.get(year);
  if (!row) {
    row = {
      year,
      months: Array(12).fill(null),
      quarters: Array(4).fill(null),
      ytd: null,
      year_total: null,
      fiscal: false,
    };
    rows.set(year, row);
  }
  return row;
}

/**
 * Build calendar-year rows (newest first) from one metric's trend. Month cells are raw
 * readings; quarter / YTD / year cells are flagged `derived` (roll-ups, visually distinct
 * + provenance-marked in the grid).
 */
export function buildGridRows(trend: TrendPoint[]): GridRow[] {
  const rows = new Map<number, GridRow>();

  for (const p of trend) {
    const label = p.periodLabel;
    const cell = (derived: boolean): GridCell => ({
      value: p.value,
      periodLabel: label,
      derived,
    });

    // monthly: "Mon YYYY"
    const m = /^([A-Z][a-z]{2}) (\d{4})$/.exec(label);
    if (m) {
      const idx = MONTH_ABBR.findIndex((abbr) => abbr === m[1]);
      if (idx >= 0) ensureRow(rows, Number(m[2])).months[idx] = cell(false);
      continue;
    }

    // quarterly: "YYYY-Q#"
    const q = /^(\d{4})-Q([1-4])$/.exec(label);
    if (q) {
      ensureRow(rows, Number(q[1])).quarters[Number(q[2]) - 1] = cell(true);
      continue;
    }

    // ytd: "<base> YTD (...)" — base is "YYYY" or "FYYYYY-YY"
    const y = /^(?:FY(\d{4})-\d{2}|(\d{4})) YTD /.exec(label);
    if (y) {
      ensureRow(rows, Number(y[1] ?? y[2])).ytd = cell(true);
      continue;
    }

    // annual_fiscal: "FYYYYY-YY"  (key on the START calendar year)
    const fy = /^FY(\d{4})-\d{2}$/.exec(label);
    if (fy) {
      const row = ensureRow(rows, Number(fy[1]));
      row.year_total = cell(true);
      row.fiscal = true;
      continue;
    }

    // annual_calendar: "YYYY"
    const ac = /^(\d{4})$/.exec(label);
    if (ac) {
      ensureRow(rows, Number(ac[1])).year_total = cell(true);
      continue;
    }
  }

  return [...rows.values()].sort((a, b) => b.year - a.year);
}
