import { describe, it, expect } from "vitest";
import {
  HERO_SLOTS,
  RATIO_ROWS,
  SERVICE_FLEET_ROWS,
  OPERATIONS_ROWS,
  buildDetailModel,
} from "@/server/metrics/detail-model";
import type { MetricView, SeriesPoint } from "@/server/metrics/types";

function pt(periodType: string, periodLabel: string, endDate: string, value: number): SeriesPoint {
  return { periodType, periodLabel, endDate, value };
}

function metric(code: string, points: SeriesPoint[]): MetricView {
  const last = points[points.length - 1];
  return {
    metricCode: code,
    displayName: code,
    unit: "count",
    currency: null,
    value: last?.value ?? 0,
    asOfLabel: last?.periodLabel ?? "",
    rank: null,
    denominator: null,
    points,
  };
}

function heroFor(metrics: MetricView[], code: string) {
  const hero = buildDetailModel(metrics).heroes.find((h) => h.code === code);
  if (!hero) throw new Error(`no hero slot for ${code}`);
  return hero;
}

describe("yoy (like-for-like, neutral direction)", () => {
  it("up", () => {
    const hero = heroFor(
      [metric("ridership", [
        pt("annual_calendar", "2024", "2024-12-31", 100),
        pt("annual_calendar", "2025", "2025-12-31", 110),
      ])],
      "ridership",
    );
    expect(hero.yoy).toEqual({ pct: 10, direction: "up", vsLabel: "2024" });
  });

  it("down", () => {
    const hero = heroFor(
      [metric("ridership", [
        pt("annual_calendar", "2024", "2024-12-31", 100),
        pt("annual_calendar", "2025", "2025-12-31", 90),
      ])],
      "ridership",
    );
    expect(hero.yoy).toEqual({ pct: -10, direction: "down", vsLabel: "2024" });
  });

  it("flat when the pct rounds to 0.0", () => {
    const hero = heroFor(
      [metric("ridership", [
        pt("annual_calendar", "2024", "2024-12-31", 100000),
        pt("annual_calendar", "2025", "2025-12-31", 100001),
      ])],
      "ridership",
    );
    expect(hero.yoy).toEqual({ pct: 0, direction: "flat", vsLabel: "2024" });
  });

  it("null when there is no prior-year annual point", () => {
    const hero = heroFor(
      [metric("ridership", [
        pt("annual_calendar", "2023", "2023-12-31", 100), // gap: 2024 missing
        pt("annual_calendar", "2025", "2025-12-31", 110),
      ])],
      "ridership",
    );
    expect(hero.yoy).toBeNull();
  });

  it("null when the prior value is 0 (no fabricated percent)", () => {
    const hero = heroFor(
      [metric("ridership", [
        pt("annual_calendar", "2024", "2024-12-31", 0),
        pt("annual_calendar", "2025", "2025-12-31", 50),
      ])],
      "ridership",
    );
    expect(hero.yoy).toBeNull();
  });

  it("a monthly latest point never feeds yoy; displayed value stays annual", () => {
    const hero = heroFor(
      [metric("ridership", [
        pt("annual_calendar", "2024", "2024-12-31", 100),
        pt("annual_calendar", "2025", "2025-12-31", 110),
        pt("monthly", "Mar 2026", "2026-03-31", 12),
      ])],
      "ridership",
    );
    expect(hero.yoy).toEqual({ pct: 10, direction: "up", vsLabel: "2024" });
    expect(hero.value).toBe(110); // last ANNUAL point, not the later monthly one
    expect(hero.asOfLabel).toBe("2025");
    expect(hero.monthly).toHaveLength(1);
    expect(hero.annual).toHaveLength(2);
  });

  it("compares only the SAME annual periodType (fiscal never vs calendar)", () => {
    const hero = heroFor(
      [metric("ridership", [
        pt("annual_calendar", "2024", "2024-12-31", 100),
        pt("annual_fiscal", "FY2025", "2025-03-31", 110),
      ])],
      "ridership",
    );
    expect(hero.yoy).toBeNull();
  });
});

describe("financials grid", () => {
  it("a missing year stays null — never 0", () => {
    const model = buildDetailModel([
      metric("farebox_revenue", [
        pt("annual_calendar", "2023", "2023-12-31", 900),
        pt("annual_calendar", "2025", "2025-12-31", 1100),
      ]),
      metric("labour_cost", [pt("annual_calendar", "2024", "2024-12-31", 700)]),
    ]);
    expect(model.financials.years.map((y) => y.key)).toEqual([2023, 2024, 2025]);
    const revenue = model.financials.operations.find((r) => r.code === "farebox_revenue");
    const labour = model.financials.operations.find((r) => r.code === "labour_cost");
    expect(revenue?.cells).toEqual([900, null, 1100]);
    expect(labour?.cells).toEqual([null, 700, null]);
  });

  it("hasFiscal flags any contributing fiscal-year point", () => {
    const calendarOnly = buildDetailModel([
      metric("total_revenue", [pt("annual_calendar", "2024", "2024-12-31", 5)]),
    ]);
    expect(calendarOnly.financials.hasFiscal).toBe(false);

    const withFiscal = buildDetailModel([
      metric("total_revenue", [pt("annual_fiscal", "FY2024", "2024-03-31", 5)]),
    ]);
    expect(withFiscal.financials.hasFiscal).toBe(true);
  });

  it("an absent metric still renders its row, all cells null", () => {
    const model = buildDetailModel([
      metric("farebox_revenue", [pt("annual_calendar", "2024", "2024-12-31", 900)]),
    ]);
    expect(model.financials.operations).toHaveLength(OPERATIONS_ROWS.length);
    const amortization = model.financials.operations.find((r) => r.code === "amortization");
    expect(amortization?.cells).toEqual([null]);
    expect(model.ratios.find((r) => r.code === "average_fare")?.value).toBeNull();
  });
});

describe("placement (the spec's metric map)", () => {
  // Hard-coded from docs/design/detail-view-metrics.md §2 — 27 unique codes, no
  // repeats. The 2026-08-25 P&L redesign replaced the two-statement Financials tab
  // with a single P&L (revenue components → total revenue, expense components →
  // total expenses, surplus, capex memo); the balance-sheet rows left the page
  // (still collected, still in the CSV download).
  const SPEC_CODES = [
    "ridership",
    "total_revenue_excluding_subsidy",
    "on_time_performance",
    "cost_per_rider",
    "subsidy_per_rider",
    "farebox_recovery_ratio",
    "cost_per_hour",
    "trips_per_revenue_hour",
    "average_fare",
    "revenue_service_hours",
    "vehicle_revenue_km",
    "fleet_size",
    "fleet_average_age",
    "accessible_fleet_pct",
    "farebox_revenue",
    "other_revenue",
    "subsidy",
    "total_revenue",
    "labour_cost",
    "energy_fuel_cost",
    "materials_services_cost",
    "other_operating_expenses",
    "operating_expenses",
    "amortization",
    "total_expenses",
    "annual_surplus_deficit",
    "capital_expenditure",
  ];

  it("the union of all sections equals the 27 unique spec codes", () => {
    expect(SPEC_CODES).toHaveLength(27);
    expect(new Set(SPEC_CODES).size).toBe(27);
    const placed = [
      ...HERO_SLOTS,
      ...RATIO_ROWS,
      ...SERVICE_FLEET_ROWS,
      ...OPERATIONS_ROWS,
    ].map((d) => d.code);
    expect(placed).toHaveLength(27);
    expect(new Set(placed)).toEqual(new Set(SPEC_CODES));
  });
});
