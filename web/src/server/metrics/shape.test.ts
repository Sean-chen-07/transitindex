import { describe, it, expect } from "vitest";
import { toShape } from "@/server/metrics/shape";

describe("toShape — non-invertible free trend", () => {
  it("suppresses the chart below 2 points", () => {
    expect(toShape([])).toEqual([]);
    expect(toShape([42])).toEqual([]);
  });

  it("normalizes to 0..1 endpoints", () => {
    expect(toShape([10, 20])).toEqual([0, 1]);
    expect(toShape([10, 15, 20])).toEqual([0, 0.5, 1]);
  });

  it("renders a flat series as a flat mid-line (no divide-by-zero)", () => {
    expect(toShape([7, 7, 7])).toEqual([0.5, 0.5, 0.5]);
  });

  it("quantizes every point to a 0.1 bucket (no raw precision leaks)", () => {
    const shape = toShape([100, 133, 167, 200, 250, 410]);
    for (const p of shape) {
      expect(Number.isInteger(Math.round(p * 10))).toBe(true);
      expect(p).toBe(Math.round(p * 10) / 10);
    }
  });

  it("is non-invertible: series differing by <1% produce identical shape", () => {
    const a = toShape([100, 110, 120]);
    const b = toShape([100.5, 110.4, 119.8]); // all within ~1% of `a`
    expect(b).toEqual(a);
    // The raw scale (100 vs 100.5) is unrecoverable — only the bucketed shape ships.
    expect(a).toEqual([0, 0.5, 1]);
  });
});
