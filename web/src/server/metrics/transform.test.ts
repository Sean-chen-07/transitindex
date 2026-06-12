import { describe, it, expect } from "vitest";
import { toMetricView, type RawMetricSeries } from "@/server/metrics/transform";

const RAW: RawMetricSeries = {
  metricCode: "ridership",
  displayName: "Ridership",
  unit: "count",
  higherIsBetter: true,
  serviceScope: "total",
  currency: null,
  rank: 3,
  denominator: 7,
  hasComparablePeriod: true,
  points: [
    { periodId: 1, periodType: "monthly", periodLabel: "Jan 2026", endDate: "2026-01-31", value: 1000000 },
    { periodId: 2, periodType: "monthly", periodLabel: "Feb 2026", endDate: "2026-02-28", value: 1100000 },
    { periodId: 3, periodType: "monthly", periodLabel: "Mar 2026", endDate: "2026-03-31", value: 1234567 },
  ],
};

describe("toMetricView", () => {
  it("keeps the rank when clean", () => {
    const view = toMetricView(RAW);
    expect(view.rank).toBe(3);
    expect(view.denominator).toBe(7);
    expect(view.suppressedReason).toBeUndefined();
  });

  it("takes value and asOfLabel from the LAST point (chronological order)", () => {
    const view = toMetricView(RAW);
    expect(view.value).toBe(1234567);
    expect(view.asOfLabel).toBe("Mar 2026");
  });

  it("maps points to SeriesPoint and drops periodId", () => {
    const view = toMetricView(RAW);
    expect(view.points).toHaveLength(3);
    expect(view.points[0]).toEqual({
      periodType: "monthly",
      periodLabel: "Jan 2026",
      endDate: "2026-01-31",
      value: 1000000,
    });
  });
});

describe("rank safety: suppression", () => {
  it("nulls the rank and flags a period miss", () => {
    const view = toMetricView({ ...RAW, hasComparablePeriod: false });
    expect(view.suppressedReason).toBe("no_comparable_period");
    expect(view.rank).toBeNull();
    expect(view.denominator).toBeNull();
  });

  it("flags pending when the rank or denominator is missing", () => {
    const view = toMetricView({ ...RAW, rank: null });
    expect(view.suppressedReason).toBe("pending");
    expect(view.rank).toBeNull();
    expect(view.denominator).toBeNull();
  });

  it("suppresses below the minimum denominator", () => {
    const view = toMetricView({ ...RAW, rank: 1, denominator: 2 });
    expect(view.suppressedReason).toBe("below_min_denominator");
    expect(view.rank).toBeNull();
    expect(view.denominator).toBeNull();
  });
});
