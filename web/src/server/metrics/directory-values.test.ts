import { describe, it, expect } from "vitest";
import { pickDirectoryValues, type DirectoryValueRow } from "./transform";

/**
 * Offline contract for the directory-card value picking (2026-08-05): latest annual
 * value per (agency, metric), 'total' scope preferred, rows arriving endDate-ascending.
 */

function row(overrides: Partial<DirectoryValueRow>): DirectoryValueRow {
  return {
    slug: "ttc",
    metricCode: "ridership",
    serviceScope: "total",
    unit: "count",
    value: 1,
    periodLabel: "2023",
    endDate: "2023-12-31",
    ...overrides,
  };
}

describe("pickDirectoryValues", () => {
  it("picks the LATEST annual value per (agency, metric)", () => {
    const out = pickDirectoryValues([
      row({ value: 100, periodLabel: "2022", endDate: "2022-12-31" }),
      row({ value: 200, periodLabel: "2023", endDate: "2023-12-31" }),
    ]);
    expect(out.ttc).toHaveLength(1);
    expect(out.ttc?.[0]).toMatchObject({
      metricCode: "ridership",
      value: 200,
      periodLabel: "2023",
      endDate: "2023-12-31",
    });
  });

  it("prefers 'total' scope over any other scope, even when the other is newer", () => {
    const out = pickDirectoryValues([
      row({ serviceScope: "total", value: 100, periodLabel: "2022", endDate: "2022-12-31" }),
      row({ serviceScope: "conventional", value: 999, periodLabel: "2023", endDate: "2023-12-31" }),
    ]);
    expect(out.ttc?.[0]?.value).toBe(100);
  });

  it("falls back to the lexically-first scope when 'total' is absent", () => {
    const out = pickDirectoryValues([
      row({ serviceScope: "conventional", value: 5 }),
      row({ serviceScope: "specialized", value: 7 }),
    ]);
    expect(out.ttc?.[0]?.value).toBe(5);
  });

  it("keeps agencies and metrics separate", () => {
    const out = pickDirectoryValues([
      row({ slug: "ttc", metricCode: "ridership", value: 1 }),
      row({ slug: "ttc", metricCode: "fleet_size", unit: "count", value: 2 }),
      row({ slug: "miway", metricCode: "ridership", value: 3 }),
    ]);
    expect(out.ttc).toHaveLength(2);
    expect(out.miway).toHaveLength(1);
  });

  it("returns an empty object for no rows", () => {
    expect(pickDirectoryValues([])).toEqual({});
  });

  it("carries unit and period metadata through to the card", () => {
    const out = pickDirectoryValues([
      row({ metricCode: "total_revenue_excluding_subsidy", unit: "CAD", value: 9_800_000 }),
    ]);
    expect(out.ttc?.[0]).toMatchObject({ unit: "CAD", periodLabel: "2023" });
  });
});
