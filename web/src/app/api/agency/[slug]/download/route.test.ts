import { describe, it, expect, vi, beforeEach } from "vitest";

/**
 * The money gate (web/CLAUDE.md): viewing is free, but the per-agency CSV download is
 * gated on a live session + isPaid, checked server-side on every request. These tests
 * pin the four branches — unknown agency (404), anonymous (302 → sign-in), signed-in but
 * unpaid (403), and paid (200 + attachment) — so the boundary can't silently regress.
 */
const getAgencySummary = vi.fn();
const getSession = vi.fn();
const isPaid = vi.fn();
const getDetailMetrics = vi.fn();

vi.mock("@/server/data/agencies", () => ({
  getAgencySummary: (...a: unknown[]) => getAgencySummary(...a),
}));
vi.mock("@/server/entitlement", () => ({
  getSession: (...a: unknown[]) => getSession(...a),
  isPaid: (...a: unknown[]) => isPaid(...a),
}));
vi.mock("@/server/metrics/access", () => ({
  getDetailMetrics: (...a: unknown[]) => getDetailMetrics(...a),
}));
vi.mock("next/server", () => ({
  NextResponse: {
    redirect: (url: URL) =>
      new Response(null, { status: 307, headers: { location: url.toString() } }),
  },
}));

import { GET } from "./route";

function req() {
  return new Request("http://localhost:3000/api/agency/ttc/download");
}
const params = Promise.resolve({ slug: "ttc" });

beforeEach(() => {
  getAgencySummary.mockReset();
  getSession.mockReset();
  isPaid.mockReset();
  getDetailMetrics.mockReset();
});

describe("GET /api/agency/[slug]/download — the money gate", () => {
  it("404s an unknown agency", async () => {
    getAgencySummary.mockResolvedValue(null);
    const res = await GET(req(), { params });
    expect(res.status).toBe(404);
    expect(getSession).not.toHaveBeenCalled(); // never reach auth for a bad slug
  });

  it("redirects an anonymous caller to sign-in", async () => {
    getAgencySummary.mockResolvedValue({ id: 1, slug: "ttc" });
    getSession.mockResolvedValue(null);
    const res = await GET(req(), { params });
    expect(res.status).toBe(307);
    expect(res.headers.get("location")).toContain("/sign-in?callbackUrl=");
    expect(res.headers.get("location")).toContain("%2Fagency%2Fttc");
    expect(isPaid).not.toHaveBeenCalled();
  });

  it("403s a signed-in but unpaid caller", async () => {
    getAgencySummary.mockResolvedValue({ id: 1, slug: "ttc" });
    getSession.mockResolvedValue({ userId: 7 });
    isPaid.mockResolvedValue(false);
    const res = await GET(req(), { params });
    expect(res.status).toBe(403);
    expect(getDetailMetrics).not.toHaveBeenCalled(); // never build the file for a non-member
  });

  it("serves a CSV attachment to a paid member", async () => {
    getAgencySummary.mockResolvedValue({ id: 1, slug: "ttc" });
    getSession.mockResolvedValue({ userId: 7 });
    isPaid.mockResolvedValue(true);
    getDetailMetrics.mockResolvedValue([]); // empty → header-only CSV is fine here
    const res = await GET(req(), { params });
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toContain("text/csv");
    expect(res.headers.get("content-disposition")).toBe(
      'attachment; filename="ttc-financials.csv"',
    );
    expect(res.headers.get("cache-control")).toBe("no-store");
  });
});
