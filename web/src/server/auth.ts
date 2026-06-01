import "server-only";
import NextAuth from "next-auth";
import Google from "next-auth/providers/google";
import Resend from "next-auth/providers/resend";
import { DrizzleAdapter } from "@auth/drizzle-adapter";
import { uuid, text, timestamp } from "drizzle-orm/pg-core";
import { db } from "@/server/db";
import { app, accounts, sessions, verificationTokens } from "@/db/schema";

// Adapter view of app.users. The Auth.js DrizzleAdapter treats `.id` as the user primary
// key that accounts/sessions reference. For us that MUST be the uuid surrogate auth_id —
// NOT the bigint app.users.id that conversion_events/watchlists FK to. Same physical
// table; only the columns the adapter touches are projected here. (No .references() is
// needed; the real FKs live in db/migrations/008.)
const adapterUsers = app.table("users", {
  id: uuid("auth_id").primaryKey().notNull().defaultRandom(),
  name: text("name"),
  email: text("email").notNull(),
  emailVerified: timestamp("email_verified", { withTimezone: true, mode: "date" }),
  image: text("image"),
});

export const { handlers, auth, signIn, signOut } = NextAuth({
  // Database sessions: the session is a row in app.sessions (no JWT). This is what lets
  // entitlement read subscription_status LIVE per request — a cancelled subscriber loses
  // access on the next request, never at a stale token refresh.
  adapter: DrizzleAdapter(db, {
    usersTable: adapterUsers,
    accountsTable: accounts,
    sessionsTable: sessions,
    verificationTokensTable: verificationTokens,
  }),
  session: { strategy: "database" },
  // Honour the AUTH_URL / forwarded host (Supabase + non-Vercel hosting).
  trustHost: true,
  providers: [
    // Both read their secrets from env by convention: AUTH_GOOGLE_ID / AUTH_GOOGLE_SECRET
    // and AUTH_RESEND_KEY. Resend needs a verified "from" address.
    Google,
    Resend({ from: process.env.AUTH_EMAIL_FROM ?? "onboarding@resend.dev" }),
  ],
  pages: { signIn: "/sign-in" },
  callbacks: {
    // Expose the adapter user id (= app.users.auth_id, a uuid) on the session. The bigint
    // app.users.id is resolved from it in src/server/entitlement.ts (getSession).
    session({ session, user }) {
      if (session.user) session.user.id = user.id;
      return session;
    },
  },
});
