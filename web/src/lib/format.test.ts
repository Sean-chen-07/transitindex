import { describe, it, expect } from "vitest";
import { toOrdinal, rankLabel, srRankLabel, provinceName, MIN_DENOMINATOR } from "@/lib/format";

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

describe("provinceName", () => {
  it("expands codes to full names", () => {
    expect(provinceName("ON")).toBe("Ontario");
    expect(provinceName("BC")).toBe("British Columbia");
    expect(provinceName("QC")).toBe("Quebec");
    expect(provinceName("AB")).toBe("Alberta");
  });
  it("falls back gracefully", () => {
    expect(provinceName("XX")).toBe("XX");
    expect(provinceName(null)).toBe("Other");
    expect(provinceName(undefined)).toBe("Other");
  });
});
