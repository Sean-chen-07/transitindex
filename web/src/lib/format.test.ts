import { describe, it, expect } from "vitest";
import {
  toOrdinal,
  rankLabel,
  srRankLabel,
  provinceName,
  formatMetricValue,
  formatYoy,
  MIN_DENOMINATOR,
} from "@/lib/format";

describe("toOrdinal", () => {
  it("formats common ordinals", () => {
    expect(toOrdinal(1)).toBe("1st");
    expect(toOrdinal(2)).toBe("2nd");
    expect(toOrdinal(3)).toBe("3rd");
    expect(toOrdinal(4)).toBe("4th");
    expect(toOrdinal(10)).toBe("10th");
    expect(toOrdinal(21)).toBe("21st");
    expect(toOrdinal(22)).toBe("22nd");
    expect(toOrdinal(23)).toBe("23rd");
  });
  it("handles the 11/12/13 exception", () => {
    expect(toOrdinal(11)).toBe("11th");
    expect(toOrdinal(12)).toBe("12th");
    expect(toOrdinal(13)).toBe("13th");
    expect(toOrdinal(111)).toBe("111th");
    expect(toOrdinal(112)).toBe("112th");
  });
});

describe("rankLabel — the defensive render gate", () => {
  it("shows the ordinal only when the rank is safe", () => {
    expect(rankLabel({ rank: 1, denominator: 10 })).toBe("1st");
    expect(rankLabel({ rank: 3, denominator: 10 })).toBe("3rd");
    expect(rankLabel({ rank: 5, denominator: 5 })).toBe("5th"); // exactly at min
  });

  it("suppresses below the minimum denominator (no '1st of 2')", () => {
    expect(rankLabel({ rank: 1, denominator: 2 })).toBe("not yet ranked");
    expect(rankLabel({ rank: 1, denominator: 4 })).toBe("not yet ranked");
    expect(MIN_DENOMINATOR).toBe(5);
  });

  it("suppresses every null / zero / out-of-range combination (no 'nullth')", () => {
    expect(rankLabel({ rank: null, denominator: 10 })).toBe("not yet ranked");
    expect(rankLabel({ rank: 3, denominator: null })).toBe("not yet ranked");
    expect(rankLabel({ rank: null, denominator: null })).toBe("not yet ranked");
    expect(rankLabel({ rank: 1, denominator: 0 })).toBe("not yet ranked");
    expect(rankLabel({ rank: 0, denominator: 10 })).toBe("not yet ranked");
    expect(rankLabel({ rank: 11, denominator: 10 })).toBe("not yet ranked"); // rank > denom
  });

  it("respects an explicit minDenominator override", () => {
    expect(rankLabel({ rank: 1, denominator: 2 }, 2)).toBe("1st");
  });
});

describe("srRankLabel", () => {
  it("reads the rank for screen readers", () => {
    expect(srRankLabel({ rank: 1, denominator: 10 })).toBe("ranked 1st of 10");
  });
  it("never reads a suppressed rank as a number", () => {
    expect(srRankLabel({ rank: 1, denominator: 2 })).toBe("not yet ranked");
    expect(srRankLabel({ rank: null, denominator: null })).toBe("not yet ranked");
  });
});

describe("formatMetricValue", () => {
  it("CAD: compact from 100k, plain dollars-and-cents below", () => {
    expect(formatMetricValue(1_420_000_000, "CAD", "CAD", { compact: true })).toBe("$1.42B");
    expect(formatMetricValue(9_800_000, "CAD", "CAD", { compact: true })).toBe("$9.8M");
    expect(formatMetricValue(4.6, "CAD", "CAD", { compact: true })).toBe("$4.60");
    expect(formatMetricValue(85_000, "CAD", "CAD", { compact: true })).toBe("$85,000");
  });
  it("CAD: non-compact stays a full number", () => {
    expect(formatMetricValue(1_420_000_000, "CAD", "CAD")).toBe("$1,420,000,000");
  });
  it("CAD: negative keeps the sign ahead of the symbol", () => {
    expect(formatMetricValue(-5_000_000, "CAD", "CAD", { compact: true })).toBe("-$5M");
  });
  it("%: max 1dp", () => {
    expect(formatMetricValue(81, "%", null)).toBe("81%");
    expect(formatMetricValue(58.34, "%", null)).toBe("58.3%");
  });
  it("count: compact number, no unit word", () => {
    expect(formatMetricValue(4_800, "count", null, { compact: true })).toBe("4,800");
    expect(formatMetricValue(521_000_000, "count", null, { compact: true })).toBe("521M");
  });
  it("hours / km carry their unit word", () => {
    expect(formatMetricValue(9_800_000, "hours", null, { compact: true })).toBe("9.8M hrs");
    expect(formatMetricValue(220_000_000, "km", null, { compact: true })).toBe("220M km");
  });
  it("years: fixed 1dp", () => {
    expect(formatMetricValue(7.4, "years", null)).toBe("7.4 yrs");
    expect(formatMetricValue(7, "years", null)).toBe("7.0 yrs");
  });
  it("CAD/hr and trips/hr", () => {
    expect(formatMetricValue(185, "CAD/hr", "CAD")).toBe("$185/hr");
    expect(formatMetricValue(52, "trips/hr", null)).toBe("52");
  });
  it("USD renders like CAD — the page names the currency, not the value", () => {
    expect(formatMetricValue(1_420_000_000, "USD", "USD", { compact: true })).toBe("$1.42B");
    expect(formatMetricValue(4.6, "USD", "USD", { compact: true })).toBe("$4.60");
    expect(formatMetricValue(185, "USD/hr", "USD")).toBe("$185/hr");
  });
  it("falls back to number + unit", () => {
    expect(formatMetricValue(12, "widgets", null)).toBe("12 widgets");
  });
});

describe("formatYoy", () => {
  it("absolute value, 1dp — the arrow carries the sign", () => {
    expect(formatYoy(4.2)).toBe("4.2%");
    expect(formatYoy(-1.3)).toBe("1.3%");
    expect(formatYoy(0)).toBe("0.0%");
  });
});

describe("provinceName", () => {
  it("expands codes to full names", () => {
    expect(provinceName("ON")).toBe("Ontario");
    expect(provinceName("BC")).toBe("British Columbia");
    expect(provinceName("QC")).toBe("Quebec");
    expect(provinceName("AB")).toBe("Alberta");
  });
  it("expands US state codes to full names", () => {
    expect(provinceName("NY")).toBe("New York");
    expect(provinceName("WA")).toBe("Washington");
    expect(provinceName("DC")).toBe("District of Columbia");
    expect(provinceName("PR")).toBe("Puerto Rico");
  });
  it("falls back gracefully", () => {
    expect(provinceName("XX")).toBe("XX");
    expect(provinceName(null)).toBe("Other");
    expect(provinceName(undefined)).toBe("Other");
  });
});
