/**
 * READ/WRITE TYPES for the `app` schema — the web-written tables.
 *
 * Mirrored by hand from db/schema.sql (Lane 0). The web app may perform DML
 * (INSERT/UPDATE/DELETE) on app.* but NEVER DDL — db/migrations owns the schema.
 * `app.watchlists` is Phase 3 and intentionally omitted. The Auth.js adapter tables
 * (accounts/sessions/verification_token) + the app.users auth columns were added in
 * Lane-0 migration 008 and are mirrored below.
 */
import {
  pgSchema,
  bigint,
  text,
  timestamp,
  uuid,
  integer,
  primaryKey,
} from "drizzle-orm/pg-core";

export const app = pgSchema("app");

export const users = app.table("users", {
  id: bigint("id", { mode: "number" }).generatedAlwaysAsIdentity().primaryKey(),
  // uuid surrogate the Auth.js adapter keys on (008). The bigint id above stays the FK
  // target for conversion_events/watchlists; auth_id is what accounts/sessions reference.
  authId: uuid("auth_id").notNull().unique().defaultRandom(),
  email: text("email").notNull(),
  emailVerified: timestamp("email_verified", { withTimezone: true, mode: "date" }),
  name: text("name"),
  image: text("image"),
  authProvider: text("auth_provider"),
  subscriptionStatus: text("subscription_status"),
  subscriptionSource: text("subscription_source"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const conversionEvents = app.table("conversion_events", {
  id: bigint("id", { mode: "number" }).generatedAlwaysAsIdentity().primaryKey(),
  eventType: text("event_type").notNull(),
  agencyId: bigint("agency_id", { mode: "number" }),
  userId: bigint("user_id", { mode: "number" }),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

export const agencyRequests = app.table("agency_requests", {
  id: bigint("id", { mode: "number" }).generatedAlwaysAsIdentity().primaryKey(),
  agencyId: bigint("agency_id", { mode: "number" }),
  requestedName: text("requested_name"),
  email: text("email"),
  createdAt: timestamp("created_at", { withTimezone: true }).defaultNow().notNull(),
});

// --- Auth.js (NextAuth v5) DrizzleAdapter tables (migration 008) -----------------
// camelCase property keys are what @auth/drizzle-adapter expects; the strings are the
// real snake_case DB columns. user_id references app.users.auth_id (uuid), NOT the bigint
// app.users.id. No Drizzle .references() is declared (web introspects; it never migrates
// from these definitions) — the FKs live in db/migrations/008.

export const accounts = app.table(
  "accounts",
  {
    userId: uuid("user_id").notNull(),
    type: text("type").notNull(),
    provider: text("provider").notNull(),
    providerAccountId: text("provider_account_id").notNull(),
    refresh_token: text("refresh_token"),
    access_token: text("access_token"),
    expires_at: integer("expires_at"),
    token_type: text("token_type"),
    scope: text("scope"),
    id_token: text("id_token"),
    session_state: text("session_state"),
  },
  (t) => [primaryKey({ columns: [t.provider, t.providerAccountId] })],
);

export const sessions = app.table("sessions", {
  sessionToken: text("session_token").primaryKey(),
  userId: uuid("user_id").notNull(),
  expires: timestamp("expires", { withTimezone: true, mode: "date" }).notNull(),
});

export const verificationTokens = app.table(
  "verification_token",
  {
    identifier: text("identifier").notNull(),
    token: text("token").notNull(),
    expires: timestamp("expires", { withTimezone: true, mode: "date" }).notNull(),
  },
  (t) => [primaryKey({ columns: [t.identifier, t.token] })],
);
