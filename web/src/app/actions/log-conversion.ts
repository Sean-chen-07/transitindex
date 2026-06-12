"use server";

import { z } from "zod";
import { db } from "@/server/db";
import { conversionEvents } from "@/db/schema";
import { getSession } from "@/server/entitlement";

// Accepts ONLY these fields; never reads or echoes a metric value (side-channel safe).
// userId is NOT accepted from the client — it is derived from the session below, so a
// forged payload can't attribute a conversion to another user.
//
// eventType is limited to the events a browser legitimately originates: 'gate_view' (the
// download dialog was opened) and 'wall_hit'. The revenue-signal events are emitted
// server-side ONLY, where they can't be forged: 'checkout_start' in billing/checkout.ts
// (a Stripe session was created) and 'paid' in the Stripe webhook (payment confirmed). A
// server action is a public HTTP endpoint, so accepting 'paid'/'checkout_start' here would
// let anyone inflate the funnel that decides pricing — they are rejected.
const schema = z.object({
  eventType: z.enum(["gate_view", "wall_hit"]),
  agencyId: z.number().int().nullable().optional(),
});

export async function logConversion(input: unknown): Promise<{ ok: boolean }> {
  const parsed = schema.safeParse(input);
  if (!parsed.success) return { ok: false };
  const session = await getSession();
  try {
    await db.insert(conversionEvents).values({
      eventType: parsed.data.eventType,
      agencyId: parsed.data.agencyId ?? null,
      userId: session?.userId ?? null,
    });
  } catch {
    // A stale/forged agencyId hits a foreign-key violation. Fail closed instead of
    // rejecting — the action's contract is { ok: boolean }, never a thrown rejection.
    return { ok: false };
  }
  return { ok: true };
}
