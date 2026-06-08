import { describe, it, expect, vi, beforeEach } from "vitest";

// Stub the db (would throw without DATABASE_URL) and the session resolver. `vi.hoisted`
// makes the spies available inside the hoisted vi.mock factories.
const { insertValues, getSession } = vi.hoisted(() => ({
  insertValues: vi.fn(),
  getSession: vi.fn(),
}));
vi.mock("@/server/db", () => ({ db: { insert: () => ({ values: insertValues }) } }));
vi.mock("@/server/entitlement", () => ({ getSession }));

import { logConversion } from "@/app/actions/log-conversion";

beforeEach(() => {
  insertValues.mockReset();
  insertValues.mockResolvedValue(undefined);
  getSession.mockReset();
  getSession.mockResolvedValue({ userId: 7 });
});

describe("logConversion", () => {
  it("rejects invalid input without touching the db", async () => {
    expect(await logConversion({ eventType: "nope" })).toEqual({ ok: false });
    expect(insertValues).not.toHaveBeenCalled();
  });

  it("derives userId from the session and ignores any client-supplied userId", async () => {
    const out = await logConversion({ eventType: "gate_view", agencyId: 3, userId: 999 });
    expect(out).toEqual({ ok: true });
    expect(insertValues).toHaveBeenCalledWith({
      eventType: "gate_view",
      agencyId: 3,
      userId: 7, // from the session, NOT the forged 999
    });
  });

  it("uses userId null when logged out", async () => {
    getSession.mockResolvedValue(null);
    await logConversion({ eventType: "wall_hit" });
    expect(insertValues).toHaveBeenCalledWith({
      eventType: "wall_hit",
      agencyId: null,
      userId: null,
    });
  });

  it("returns { ok: false } (never rejects) when the insert throws on a bad FK", async () => {
    insertValues.mockRejectedValue(new Error("insert or update violates foreign key"));
    await expect(
      logConversion({ eventType: "gate_view", agencyId: 123456 }),
    ).resolves.toEqual({ ok: false });
  });
});
