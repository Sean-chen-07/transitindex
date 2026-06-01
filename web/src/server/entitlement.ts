import "server-only";
import { cache } from "react";
import { eq } from "drizzle-orm";
import { db } from "@/server/db";
import { users } from "@/db/schema";
// NOTE: @/server/auth (the NextAuth instance) is imported LAZILY inside getSession() below.
// Static-importing it here would pull the whole NextAuth stack into the graph of every
// module that only needs isPaid()/value-stripping — e.g. the metrics choke point and its
// Postgres tests. getSession() is the only function that actually needs auth().

/**
 * The paid-entitlement check the gate consumes. Auth.js issues DATABASE sessions: the
 * session row carries the uuid surrogate (app.users.auth_id). getSession() resolves it to
 * the bigint app.users.id the app keys on; isPaid() reads subscription_status LIVE per
 * request (so a cancelled subscriber loses access on the next request, never a stale JWT
 * claim — the Stripe webhook is the only writer of that column). `cache()` dedupes each
 * lookup to once per render.
 */
export interface Session {
  userId: number | null;
}

export const isPaid = cache(async (session: Session | null): Promise<boolean> => {
  if (!session?.userId) return false;
  const [row] = await db
    .select({ subscriptionStatus: users.subscriptionStatus })
    .from(users)
    .where(eq(users.id, session.userId))
    .limit(1);
  return row?.subscriptionStatus === "active";
});

export const getSession = cache(async (): Promise<Session | null> => {
  const { auth } = await import("@/server/auth");
  const session = await auth();
  // session.user.id is the adapter user id (= app.users.auth_id, a uuid).
  const authId = session?.user?.id;
  if (!authId) return null;
  const [row] = await db
    .select({ id: users.id })
    .from(users)
    .where(eq(users.authId, authId))
    .limit(1);
  return row ? { userId: row.id } : null;
});
