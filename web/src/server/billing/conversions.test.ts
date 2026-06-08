import { describe, it, expect, vi, beforeEach } from "vitest";

// Stub the db. `limit` resolves the existence-check select; `insertValues` is the insert.
const { limit, insertValues } = vi.hoisted(() => ({
  limit: vi.fn(),
  insertValues: vi.fn(),
}));
vi.mock("@/server/db", () => ({
  db: {
    select: () => ({ from: () => ({ where: () => ({ limit }) }) }),
    insert: () => ({ values: insertValues }),
  },
}));

import { recordPaidConversionOnce } from "@/server/billing/conversions";

beforeEach(() => {
  limit.mockReset();
  insertValues.mockReset();
  insertValues.mockResolvedValue(undefined);
});

describe("recordPaidConversionOnce", () => {
  it("inserts a 'paid' event when the user has none yet", async () => {
    limit.mockResolvedValue([]); // no existing 'paid' row
    await recordPaidConversionOnce(7);
    expect(insertValues).toHaveBeenCalledWith({ eventType: "paid", userId: 7 });
  });

  it("is idempotent: a Stripe redelivery does NOT insert a second 'paid' row", async () => {
    limit.mockResolvedValue([{ id: 1 }]); // already recorded
    await recordPaidConversionOnce(7);
    expect(insertValues).not.toHaveBeenCalled();
  });
});
