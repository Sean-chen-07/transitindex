"use server";

import { z } from "zod";
import { db } from "@/server/db";
import { conversionEvents } from "@/db/schema";

// Accepts ONLY these fields; never reads or echoes a metric value (side-channel safe).
const schema = z.object({
  eventType: z.enum(["wall_hit", "gate_view", "checkout_start", "paid"]),
  agencyId: z.number().int().nullable().optional(),
  userId: z.number().int().nullable().optional(),
});

export async function logConversion(input: unknown): Promise<{ ok: boolean }> {
  const parsed = schema.safeParse(input);
  if (!parsed.success) return { ok: false };
  await db.insert(conversionEvents).values({
    eventType: parsed.data.eventType,
    agencyId: parsed.data.agencyId ?? null,
    userId: parsed.data.userId ?? null,
  });
  return { ok: true };
}
