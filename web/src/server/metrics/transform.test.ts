import { describe, it, expect } from "vitest";
import { toFreeView, toPaidView, type RawMetricRow } from "@/server/metrics/transform";

const RAW: RawMetricRow = {
  metricCode: "monthly_ridership",
  displayName: "Monthly Ridership",
  unit: "count",
  higherIsBetter: true,
  serviceScope: "total",
  rank: 3,
  denominator: 7,
  value: 1234567, // distinctive — must never appear in a free payload
  currency: null,
  periodLabel: "Mar 2026",
  trend: [
    { periodLabel: "Jan 2026", value: 1000000 },
    { periodLabel: "Feb 2026", value: 1100000 },
    { periodLabel: "Mar 2026", value: 1234567 },
  ],
  provenance: [
    {
      sourceTitle: "StatCan 23-10-0307",
      sourceUrl: "https://example.org",
      pageNumber: null,
      tableReference: "23-10-0307",
      license: "statcan_open",
    },
  ],
  hasComparablePeriod: true,
};

describe("paywall: toFreeView never leaks a raw number (runnable A1)", () => {
  const free = toFreeView(RAW);
  const json = JSON.stringify(free);

  it("omits the value / trend / provenance keys entirely", () => {
    expect("value" in free).toBe(false);
    expect("trend" in free).toBe(false);
    expect("provenance" in free).toBe(false);
  });

  it("contains no raw number signature anywhere in the serialized payload", () => {
    expect(json).not.toContain("1234567");
    expect(json).not.toContain("1000000");
    expect(json).not.toContain("1100000");
  });

  it("still carries the free-safe facts", () => {
    expect(free.rank).toBe(3);
    expect(free.denominator).toBe(7);
    expect(free.direction).toBe("higher_is_better");
    expect(free.asOfLabel).toBe("Mar 2026");
    expect(free.attribution).toContain("Statistics Canada");
    expect(free.shape.length).toBe(3); // a shape, but quantized + non-invertible
    free.shape.forEach((p) => expect(p).toBe(Math.round(p * 10) / 10));
  });
});

describe("paywall: toPaidView includes the raw value", () => {
  it("carries value + trend + provenance", () => {
    const paid = toPaidView(RAW);
    expect(paid.value).toBe(1234567);
    expect(paid.trend).toHaveLength(3);
    expect(paid.provenance[0]?.license).toBe("statcan_open");
  });
});

describe("rank safety: suppression", () => {
  it("suppresses below the minimum denominator", () => {
    const free = toFreeView({ ...RAW, rank: 1, denominator: 2 });
    expect(free.rank).toBeNull();
    expect(free.suppressedReason).toBe("below_min_denominator");
  });
  it("flags a period miss", () => {
    const free = toFreeView({ ...RAW, hasComparablePeriod: false });
    expect(free.suppressedReason).toBe("no_comparable_period");
    expect(free.rank).toBeNull();
  });
});
