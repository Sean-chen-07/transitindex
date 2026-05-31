/**
 * READ/WRITE TYPES for the `app` schema — the web-written tables.
 *
 * Mirrored by hand from db/schema.sql (Lane 0). The web app may perform DML
 * (INSERT/UPDATE/DELETE) on app.* but NEVER DDL — db/migrations owns the schema.
 * `app.watchlists` is Phase 3 and intentionally omitted. The Auth.js adapter tables
 * (accounts/sessions/verification_token) + the app.users auth columns arrive in
 * Lane-0 migration 008 (steps 6-8); re-mirror them here after 008 lands.
 */
import { pgSchema, bigint, text, timestamp } from "drizzle-orm/pg-core";

export const app = pgSchema("app");

export const users = app.table("users", {
  id: bigint("id", { mode: "number" }).generatedAlwaysAsIdentity().primaryKey(),
  email: text("email").notNull(),
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
