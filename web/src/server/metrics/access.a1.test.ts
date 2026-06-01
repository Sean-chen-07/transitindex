import { describe, it, expect } from "vitest";

/**
 * IRON A1 — end-to-end paywall integrity against a real Postgres test DB.
 *
 * Runs ONLY when TEST_DATABASE_URL is set (a throwaway DB with db/migrations applied,
 * so it exercises the real web_reader grant). Until the Postgres CI harness lands
 * (step 6 / Lane-0 P2), the RUNNABLE proof of the value-stripping logic is
 * transform.test.ts. This test verifies the reveal wiring + the no-`value` guarantee
 * against whatever data the test DB holds (correct even when empty).
 *
 * To seed a full red→green leak check, insert a known metric_value (e.g. 1234567) +
 * rank for a non-demo agency and assert getFreeMetrics never returns it.
 */
const TEST_DB = process.env.TEST_DATABASE_URL;

describe.skipIf(!TEST_DB)("A1: paywall integrity (Postgres)", () => {
  it("free metrics never carry a `value` key; demo reveals, non-demo anon does not", async () => {
    process.env.DATABASE_URL = TEST_DB;
    const { getFreeMetrics, getDetailMetrics } = await import("@/server/metrics/access");
    const { DEMO_AGENCY_SLUG } = await import("@/server/data/constants");

    const free = await getFreeMetrics(DEMO_AGENCY_SLUG);
    for (const m of free) expect("value" in m).toBe(false);

    const demo = await getDetailMetrics(DEMO_AGENCY_SLUG, null);
    expect(demo.reveal).toBe(true);

    const gated = await getDetailMetrics("stm", null); // a non-demo agency, anonymous
    expect(gated.reveal).toBe(false);
    for (const m of gated.metrics) expect("value" in m).toBe(false);
  }, 30_000); // network DB: allow for a cold Supabase pooler + TLS handshake
});
