import { describe, it, expect, vi } from "vitest";

// freshness.ts statically imports @/server/db, which throws without DATABASE_URL. We only
// exercise the pure reducer (it never touches the db), so stub the module.
vi.mock("@/server/db", () => ({ db: {} }));

import { reduceLatestFreshness, type FeedRunRow } from "@/server/data/freshness";

const row = (over: Partial<FeedRunRow>): FeedRunRow => ({
  code: "statcan_307",
  displayName: "StatCan 23-10-0307",
  expectedCadence: "monthly",
  enabled: true,
  status: "ok",
  lastGoodAt: null,
  finishedAt: null,
  ...over,
});

describe("reduceLatestFreshness", () => {
  it("keeps the run with the max finishedAt even when its lastGoodAt is null", () => {
    // Regression: the old code compared a candidate's finishedAt against the kept run's
    // lastGoodAt. Since the ingester never sets lastGoodAt, the latest (failed) run would
    // be wrongly displaced by an OLDER successful one. The latest run must win.
    const latestFailed = row({
      status: "error",
      finishedAt: new Date("2026-03-01T00:00:00Z"),
      lastGoodAt: null,
    });
    const olderGood = row({
      status: "ok",
      finishedAt: new Date("2026-01-01T00:00:00Z"),
      lastGoodAt: new Date("2026-01-01T00:00:00Z"),
    });
    const [out] = reduceLatestFreshness([latestFailed, olderGood]);
    expect(out?.status).toBe("error");
    expect(out?.lastGoodAt).toBeNull();
  });

  it("ignores iteration order — the max finishedAt wins regardless of position", () => {
    const newer = row({ status: "ok", finishedAt: new Date("2026-05-01T00:00:00Z") });
    const older = row({ status: "stale", finishedAt: new Date("2026-02-01T00:00:00Z") });
    expect(reduceLatestFreshness([newer, older])[0]?.status).toBe("ok");
    expect(reduceLatestFreshness([older, newer])[0]?.status).toBe("ok");
  });

  it("tolerates a feed with no runs (all-null join row)", () => {
    const [out] = reduceLatestFreshness([
      row({ status: null, finishedAt: null, lastGoodAt: null }),
    ]);
    expect(out?.status).toBeNull();
    expect(out?.lastGoodAt).toBeNull();
  });

  it("skips disabled feeds", () => {
    expect(reduceLatestFreshness([row({ enabled: false })])).toEqual([]);
  });

  it("sorts the result by display name", () => {
    const out = reduceLatestFreshness([
      row({ code: "z", displayName: "Zebra Feed" }),
      row({ code: "a", displayName: "Alpha Feed" }),
    ]);
    expect(out.map((f) => f.displayName)).toEqual(["Alpha Feed", "Zebra Feed"]);
  });
});
