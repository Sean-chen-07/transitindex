import type { MetricView, SeriesPoint } from "./types";

/**
 * Pure shaping of MetricView[] into the two-tab detail view-model
 * (docs/design/detail-view-metrics.md §§3–4). No DB, no "server-only": the outputs are
 * plain data, safe to serialize to a client component, and unit-tested offline.
 */

export interface SlotDef {
  code: string;
  label: string;
}

export interface StatementRowDef extends SlotDef {
  bold: boolean;
  indent: boolean;
}

/** Spec §3.1 — the six directory-card metrics, in order. */
export const HERO_SLOTS: SlotDef[] = [
  { code: "ridership", label: "Ridership" },
  { code: "total_revenue_excluding_subsidy", label: "Total revenue excluding subsidy" },
  { code: "on_time_performance", label: "On-time performance" },
  { code: "cost_per_rider", label: "Cost per rider" },
  { code: "subsidy_per_rider", label: "Subsidy per rider" },
  { code: "fleet_capacity", label: "Fleet scale" },
];

/** Spec §3.2 — current value only, no charts, no ranks. */
export const RATIO_ROWS: SlotDef[] = [
  { code: "farebox_recovery_ratio", label: "Farebox recovery" },
  { code: "cost_per_hour", label: "Cost per revenue hour" },
  { code: "trips_per_revenue_hour", label: "Trips per revenue hour" },
  { code: "average_fare", label: "Average fare" },
];

/** Spec §3.3 — current value only, no charts, no ranks. */
export const SERVICE_FLEET_ROWS: SlotDef[] = [
  { code: "revenue_service_hours", label: "Revenue service hours" },
  { code: "vehicle_revenue_km", label: "Vehicle revenue km" },
  { code: "fleet_size", label: "Fleet size" },
  { code: "fleet_average_age", label: "Fleet average age" },
  { code: "accessible_fleet_pct", label: "Accessible fleet %" },
];

/** Spec §4 Statement of Operations, in statement order. Bold = totals, indent = components. */
export const OPERATIONS_ROWS: StatementRowDef[] = [
  { code: "total_revenue_excluding_subsidy", label: "Total revenue excluding subsidy", bold: false, indent: false },
  { code: "labour_cost", label: "Labour", bold: false, indent: true },
  { code: "energy_fuel_cost", label: "Energy & fuel", bold: false, indent: true },
  { code: "materials_services_cost", label: "Materials & services", bold: false, indent: true },
  { code: "operating_expenses", label: "Total operating expenses", bold: true, indent: false },
  { code: "subsidy", label: "Subsidy (the gap)", bold: false, indent: false },
  { code: "capital_expenditure", label: "Capital spending", bold: false, indent: false },
];

/** Spec §4 Statement of Financial Position, in statement order. */
export const POSITION_ROWS: StatementRowDef[] = [
  { code: "cash_and_investments", label: "Cash & investments", bold: false, indent: false },
  { code: "total_financial_assets", label: "Total financial assets", bold: true, indent: true },
  { code: "long_term_debt", label: "Long-term debt", bold: false, indent: false },
  { code: "total_liabilities", label: "Total liabilities", bold: true, indent: true },
  { code: "net_debt", label: "Net debt", bold: false, indent: false },
  { code: "tangible_capital_assets", label: "Tangible capital assets", bold: false, indent: false },
  { code: "total_non_financial_assets", label: "Total non-financial assets", bold: true, indent: true },
  { code: "total_assets", label: "Total assets", bold: true, indent: true },
  { code: "accumulated_surplus", label: "Accumulated surplus", bold: false, indent: false },
  { code: "debt_to_assets", label: "Debt to assets", bold: false, indent: true },
  { code: "net_debt_per_capita", label: "Net debt per capita", bold: false, indent: true },
];

export interface YoyVM {
  pct: number;
  direction: "up" | "down" | "flat";
  vsLabel: string;
}

export interface HeroVM {
  code: string;
  label: string;
  unit: string;
  currency: string | null;
  value: number | null;
  asOfLabel: string;
  rank: number | null;
  denominator: number | null;
  yoy: YoyVM | null;
  monthly: SeriesPoint[];
  annual: SeriesPoint[];
}

export interface ValueRowVM {
  code: string;
  label: string;
  value: number | null;
  unit: string;
  currency: string | null;
  asOfLabel: string;
}

export interface StatementRowVM {
  code: string;
  label: string;
  bold: boolean;
  indent: boolean;
  unit: string;
  currency: string | null;
  /** Aligned to FinancialsVM.years; a missing year is null — NEVER 0. */
  cells: (number | null)[];
}

export interface FinancialsVM {
  years: { key: number; label: string }[];
  operations: StatementRowVM[];
  position: StatementRowVM[];
  hasFiscal: boolean;
}

export interface DetailViewModel {
  heroes: HeroVM[];
  ratios: ValueRowVM[];
  serviceFleet: ValueRowVM[];
  financials: FinancialsVM;
}

const ANNUAL_TYPES = new Set(["annual_calendar", "annual_fiscal"]);

function annualPoints(m: MetricView): SeriesPoint[] {
  return m.points.filter((p) => ANNUAL_TYPES.has(p.periodType));
}

function endYear(p: SeriesPoint): number {
  return Number(p.endDate.slice(0, 4));
}

/** Last annual point when any exists, else the last point of any type (honest as-of). */
function displayPoint(m: MetricView): SeriesPoint | null {
  const annual = annualPoints(m);
  return annual[annual.length - 1] ?? m.points[m.points.length - 1] ?? null;
}

/**
 * Like-for-like year-over-year: the last ANNUAL point vs the annual point of the SAME
 * periodType whose end-year is exactly one less (spec §3.1 — a monthly latest point
 * never feeds the arrow). Null when no such pair, or when the prior value is 0.
 */
function yoyOf(annual: SeriesPoint[]): YoyVM | null {
  const cur = annual[annual.length - 1];
  if (!cur) return null;
  const prev = annual.find(
    (p) => p.periodType === cur.periodType && endYear(p) === endYear(cur) - 1,
  );
  if (!prev || prev.value === 0) return null;
  const pct = Math.round(((cur.value - prev.value) / Math.abs(prev.value)) * 1000) / 10;
  const direction: YoyVM["direction"] = pct > 0 ? "up" : pct < 0 ? "down" : "flat";
  return { pct, direction, vsLabel: prev.periodLabel };
}

function toValueRow(def: SlotDef, m: MetricView | undefined): ValueRowVM {
  const shown = m ? displayPoint(m) : null;
  return {
    code: def.code,
    label: def.label,
    value: shown?.value ?? null,
    unit: m?.unit ?? "",
    currency: m?.currency ?? null,
    asOfLabel: shown?.periodLabel ?? "",
  };
}

function buildFinancials(byCode: Map<string, MetricView>): FinancialsVM {
  const statementRows = [...OPERATIONS_ROWS, ...POSITION_ROWS];

  // Sorted-ascending union of end-years over the annual points of all statement codes;
  // the label is the first periodLabel seen for that year.
  const labelByYear = new Map<number, string>();
  let hasFiscal = false;
  for (const def of statementRows) {
    const m = byCode.get(def.code);
    if (!m) continue;
    for (const p of annualPoints(m)) {
      const year = endYear(p);
      if (!labelByYear.has(year)) labelByYear.set(year, p.periodLabel);
      if (p.periodType === "annual_fiscal") hasFiscal = true;
    }
  }
  const years = [...labelByYear.entries()]
    .sort((a, b) => a[0] - b[0])
    .map(([key, label]) => ({ key, label }));

  const toRow = (def: StatementRowDef): StatementRowVM => {
    const m = byCode.get(def.code);
    const valueByYear = new Map<number, number>();
    if (m) for (const p of annualPoints(m)) valueByYear.set(endYear(p), p.value);
    return {
      code: def.code,
      label: def.label,
      bold: def.bold,
      indent: def.indent,
      unit: m?.unit ?? "",
      currency: m?.currency ?? null,
      cells: years.map((y) => valueByYear.get(y.key) ?? null),
    };
  };

  return {
    years,
    operations: OPERATIONS_ROWS.map(toRow),
    position: POSITION_ROWS.map(toRow),
    hasFiscal,
  };
}

export function buildDetailModel(metrics: MetricView[]): DetailViewModel {
  const byCode = new Map(metrics.map((m) => [m.metricCode, m]));

  const heroes: HeroVM[] = HERO_SLOTS.map((slot) => {
    const m = byCode.get(slot.code);
    if (!m) {
      return {
        code: slot.code,
        label: slot.label,
        unit: "",
        currency: null,
        value: null,
        asOfLabel: "",
        rank: null,
        denominator: null,
        yoy: null,
        monthly: [],
        annual: [],
      };
    }
    const annual = annualPoints(m);
    const shown = displayPoint(m);
    return {
      code: slot.code,
      label: m.displayName,
      unit: m.unit,
      currency: m.currency,
      value: shown?.value ?? null,
      asOfLabel: shown?.periodLabel ?? "",
      rank: m.rank,
      denominator: m.denominator,
      yoy: yoyOf(annual),
      monthly: m.points.filter((p) => p.periodType === "monthly"),
      annual,
    };
  });

  return {
    heroes,
    ratios: RATIO_ROWS.map((def) => toValueRow(def, byCode.get(def.code))),
    serviceFleet: SERVICE_FLEET_ROWS.map((def) => toValueRow(def, byCode.get(def.code))),
    financials: buildFinancials(byCode),
  };
}
