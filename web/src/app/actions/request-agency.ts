"use server";

import { z } from "zod";
import { db } from "@/server/db";
import { agencyRequests } from "@/db/schema";

// Accepts ONLY these fields; never reads or echoes a metric value (side-channel safe).
const schema = z.object({
  agencyId: z.number().int().nullable().optional(),
  requestedName: z.string().min(1).max(200).optional(),
  email: z.string().email().max(320).optional(),
});

export async function requestAgency(input: unknown): Promise<{ ok: boolean }> {
  const parsed = schema.safeParse(input);
  if (!parsed.success) return { ok: false };
  await db.insert(agencyRequests).values({
    agencyId: parsed.data.agencyId ?? null,
    requestedName: parsed.data.requestedName ?? null,
    email: parsed.data.email ?? null,
  });
  return { ok: true };
}
