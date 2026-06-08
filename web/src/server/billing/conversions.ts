import "server-only";
import { and, eq } from "drizzle-orm";
import { db } from "@/server/db";
import { conversionEvents } from "@/db/schema";

/**
 * Record a 'paid' conversion-funnel event for a user, at most once.
 *
 * Stripe redelivers webhook events as normal operation (retries, manual replays,
 * at-least-once delivery), but a user converts to paid once. We insert only if there
 * isn't already a 'paid' row for them, so redeliveries don't inflate the funnel's paid
 * count — the app's only revenue-conversion signal. (No event-id dedupe table: the web
 * app is introspect-only and can't own a Lane-0 migration, so we dedupe on the funnel's
 * own natural key instead.)
 */
export async function recordPaidConversionOnce(userId: number): Promise<void> {
  const [already] = await db
    .select({ id: conversionEvents.id })
    .from(conversionEvents)
    .where(and(eq(conversionEvents.userId, userId), eq(conversionEvents.eventType, "paid")))
    .limit(1);
  if (!already) {
    await db.insert(conversionEvents).values({ eventType: "paid", userId });
  }
}
