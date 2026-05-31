import "server-only";
import { cache } from "react";

/**
 * The paid-entitlement check the gate consumes. In the free-app build (steps 1-5)
 * there is no auth yet, so there is no session and nobody is paid — only the DEMO
 * agency reveals numbers. Steps 6-8 replace getSession() with Auth.js and make isPaid()
 * read app.users.subscription_status === 'active' LIVE per request (so a cancelled
 * subscriber loses access on the next request, never a stale JWT claim). `cache()`
 * dedupes the lookup to once per render.
 */
export interface Session {
  userId: number | null;
}

export const isPaid = cache(async (session: Session | null): Promise<boolean> => {
  if (!session?.userId) return false;
  // TODO(step 7): SELECT subscription_status FROM app.users WHERE id = session.userId
  //               return subscription_status === 'active';
  return false;
});

export async function getSession(): Promise<Session | null> {
  // TODO(step 7): wire Auth.js (database sessions). No auth in the free-app build.
  return null;
}
