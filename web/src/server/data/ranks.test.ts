/**
 * Unit tests for reconcileRanks — the PRIMARY server-side N<5 guard.
 * This pure function is the only thing standing between the DB and "1st of 2"
 * (the Lane A rank job does not suppress small pools; db/migrations/005:34).
 * Tests run without a real DB by mocking the db pool and drizzle schema objects.
 */
import { vi, describe, it, expect } from "vitest";

// Must mock before the module is imported (vitest hoists vi.mock calls).
vi.mock("server-only", () => ({}));
vi.mock("@/server/db", () => ({ db: {} }));
vi.mock("@/db/schema", () => ({
  agencies: {},
  metricRanks: {},
  metrics: {},
  reportingPeriods: {},
}));

const { reconcileRanks } = await import("./ranks");

// --- fixtures ---

function makeRow(overrides: {
  metricId?: number;
  periodId?: number;
  rank?: number | null;
  denominator?: number | null;
  computedAt?: Date | null;
  metricCode?: string;
  metricDisplayName?: string;
  unitType?: string | null;
  higherIsBetter?: boolean | null;
  periodLabel?: string;
  periodEnd?: string;
}) {
  return {
    metricId: 1,
    periodId: 10,
    rank: 3,
    denominator: 10,
    computedAt: null,
    metricCode: "ridership",
    metricDisplayName: "Annual Ridership",
    unitType: "count",
    higherIsBetter: true,
    periodLabel: "FY2024",
    periodEnd: "2024-12-31",
    ...overrides,
  };
}

const META_1 = { id: 1, code: "ridership", displayName: "Annual Ridership", unitType: "count" as string | null, higherIsBetter: true as boolean | null };
const COHORT_10 = { periodId: 10, endDate: "2024-12-31", label: "FY2024" };

describe("reconcileRanks — primary N<5 guard", () => {
  it("returns [] when there are no cohort periods", () => {
    const result = reconcileRanks([], new Map(), new Map([[1, META_1]]));
    expect(result).toEqual([]);
  });

  it("returns [] when there are no rows and no meta", () => {
    const result = reconcileRanks([], new Map([[1, COHORT_10]]), new Map());
    expect(result).toEqual([]);
  });

  it("marks a valid rank as 'ranked'", () => {
    const rows = [makeRow({ rank: 3, denominator: 10 })];
    const latest = new Map([[1, COHORT_10]]);
    const meta = new Map([[1, META_1]]);
    const [r] = reconcileRanks(rows, latest, meta);
    expect(r?.status).toBe("ranked");
    expect(r?.rank).toBe(3);
    expect(r?.denominator).toBe(10);
  });

  it("suppresses when denominator < MIN_DENOMINATOR (5) → 'not_yet_ranked'", () => {
    const rows = [makeRow({ rank: 1, denominator: 4 })];
    const [r] = reconcileRanks(rows, new Map([[1, COHORT_10]]), new Map([[1, META_1]]));
    expect(r?.status).toBe("not_yet_ranked");
  });

  it("suppresses when rank is null → 'not_yet_ranked'", () => {
    const rows = [makeRow({ rank: null, denominator: 10 })];
    const [r] = reconcileRanks(rows, new Map([[1, COHORT_10]]), new Map([[1, META_1]]));
    expect(r?.status).toBe("not_yet_ranked");
  });

  it("suppresses when denominator is null → 'not_yet_ranked'", () => {
    const rows = [makeRow({ rank: 1, denominator: null })];
    const [r] = reconcileRanks(rows, new Map([[1, COHORT_10]]), new Map([[1, META_1]]));
    expect(r?.status).toBe("not_yet_ranked");
  });

  it("suppresses when rank < 1 → 'not_yet_ranked'", () => {
    const rows = [makeRow({ rank: 0, denominator: 10 })];
    const [r] = reconcileRanks(rows, new Map([[1, COHORT_10]]), new Map([[1, META_1]]));
    expect(r?.status).toBe("not_yet_ranked");
  });

  it("suppresses when rank > denominator → 'not_yet_ranked'", () => {
    const rows = [makeRow({ rank: 11, denominator: 10 })];
    const [r] = reconcileRanks(rows, new Map([[1, COHORT_10]]), new Map([[1, META_1]]));
    expect(r?.status).toBe("not_yet_ranked");
  });

  it("produces 'not_ranked_period_miss' when agency row is in a different period", () => {
    // Row is in period 9, but cohort's latest is period 10.
    const rows = [makeRow({ periodId: 9, rank: 3, denominator: 10 })];
    const [r] = reconcileRanks(rows, new Map([[1, COHORT_10]]), new Map([[1, META_1]]));
    expect(r?.status).toBe("not_ranked_period_miss");
    expect(r?.periodLabel).toBe("FY2024"); // cohort's label, not the row's
    expect(r?.rank).toBeNull();
    expect(r?.denominator).toBeNull();
  });

  it("produces 'not_ranked_period_miss' when agency has NO row for the metric at all", () => {
    const result = reconcileRanks([], new Map([[1, COHORT_10]]), new Map([[1, META_1]]));
    const [r] = result;
    expect(r?.status).toBe("not_ranked_period_miss");
    expect(r?.metricCode).toBe("ridership");
  });

  it("uses row's own fields when agency has a matching row (meta only needed for period-miss)", () => {
    // latestByMetric has metric 2, agency has a matching row. metaById is empty.
    // When `have` exists, the function uses have.metricCode etc. — meta is irrelevant.
    const rows = [makeRow({ metricId: 2, periodId: 20, metricCode: "fleet", metricDisplayName: "Fleet Size", rank: 2, denominator: 8 })];
    const latest = new Map([[2, { periodId: 20, endDate: "2024-12-31", label: "FY2024" }]]);
    const meta = new Map<number, typeof META_1>(); // empty — irrelevant for have-row case
    const [r] = reconcileRanks(rows, latest, meta);
    expect(r?.metricCode).toBe("fleet");
    expect(r?.status).toBe("ranked");
  });

  it("only uses the row that matches the cohort-latest period (ignores stale rows)", () => {
    // Agency has rows for both period 9 (rank=1) and period 10 (rank=3).
    // Only period 10 is latest; period 9 should be ignored.
    const rows = [
      makeRow({ periodId: 9, rank: 1, denominator: 10 }),
      makeRow({ periodId: 10, rank: 3, denominator: 10 }),
    ];
    const [r] = reconcileRanks(rows, new Map([[1, COHORT_10]]), new Map([[1, META_1]]));
    expect(r?.status).toBe("ranked");
    expect(r?.rank).toBe(3);
  });

  it("sorts results by metricDisplayName", () => {
    const COHORT_A = { periodId: 10, endDate: "2024-12-31", label: "FY2024" };
    const COHORT_B = { periodId: 10, endDate: "2024-12-31", label: "FY2024" };
    const latest = new Map([
      [1, COHORT_A],
      [2, COHORT_B],
    ]);
    const meta = new Map([
      [1, { id: 1, code: "z_metric", displayName: "Z Metric", unitType: null, higherIsBetter: null }],
      [2, { id: 2, code: "a_metric", displayName: "A Metric", unitType: null, higherIsBetter: null }],
    ]);
    const rows = [
      makeRow({ metricId: 1, periodId: 10, metricCode: "z_metric", metricDisplayName: "Z Metric" }),
      makeRow({ metricId: 2, periodId: 10, metricCode: "a_metric", metricDisplayName: "A Metric" }),
    ];
    const result = reconcileRanks(rows, latest, meta);
    expect(result[0]?.metricCode).toBe("a_metric");
    expect(result[1]?.metricCode).toBe("z_metric");
  });
});
