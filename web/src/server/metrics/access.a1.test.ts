import { describe, it, expect } from "vitest";

/**
 * A1 (INVERTED 2026-06-09) — free viewing against a real Postgres test DB.
 *
 * Runs ONLY when TEST_DATABASE_URL is set (a throwaway DB with db/migrations applied,
 * so it exercises the real web_reader grant). The old contract (free views must strip
 * `value`) is retired: viewing is free by decision
 * (docs/design/detail-view-metrics.md §6), so getDetailMetrics takes NO session and
 * returns raw numbers to everyone. The money gate moved to
 * /api/agency/[slug]/download, which checks the live session + isPaid per request.
 */
const TEST_DB = process.env.TEST_DATABASE_URL;

describe.skipIf(!TEST_DB)("A1: free viewing (Postgres)", () => {
  it("getDetailMetrics needs no session and every entry carries a value + series", async () => {
    process.env.DATABASE_URL = TEST_DB;
    const { getDetailMetrics } = await import("@/server/metrics/access");

    const metrics = await getDetailMetrics("ttc"); // anonymous: no session parameter exists
    for (const m of metrics) {
      expect(typeof m.value).toBe("number");
      expect(Number.isFinite(m.value)).toBe(true);
      expect(Array.isArray(m.points)).toBe(true);
      expect(m.points.length).toBeGreaterThan(0);
    }
  }, 30_000); // network DB: allow for a cold Supabase pooler + TLS handshake
});
