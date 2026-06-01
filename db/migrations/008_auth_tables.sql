-- migrate:up

-- Lane-0 migration for web authentication (Auth.js v5 / NextAuth database sessions).
-- The web app only INTROSPECTS these tables — it never defines or migrates them.
--
-- Identity reconciliation: app.users.id stays a bigint identity (it is the FK target
-- for app.conversion_events.user_id and app.watchlists.user_id). The Auth.js adapter
-- cannot key on a bigint, so we add a uuid surrogate, app.users.auth_id, and the three
-- adapter tables reference THAT. (gen_random_uuid() is a core function in Postgres 15+,
-- which Supabase runs; the apply runbook verifies it before running this.)

ALTER TABLE app.users
  ADD COLUMN auth_id        uuid UNIQUE NOT NULL DEFAULT gen_random_uuid(),
  ADD COLUMN name           text,
  ADD COLUMN image          text,
  ADD COLUMN email_verified timestamptz;

-- Auth.js DrizzleAdapter shapes (Postgres). Column names are snake_case here and mapped
-- to the adapter's camelCase property keys in web/src/db/schema/app.ts.
CREATE TABLE app.accounts (
  user_id             uuid NOT NULL REFERENCES app.users(auth_id) ON DELETE CASCADE,
  type                text NOT NULL,
  provider            text NOT NULL,
  provider_account_id text NOT NULL,
  refresh_token       text,
  access_token        text,
  expires_at          integer,
  token_type          text,
  scope               text,
  id_token            text,
  session_state       text,
  PRIMARY KEY (provider, provider_account_id)
);

CREATE TABLE app.sessions (
  session_token text PRIMARY KEY,
  user_id       uuid NOT NULL REFERENCES app.users(auth_id) ON DELETE CASCADE,
  expires       timestamptz NOT NULL
);

CREATE TABLE app.verification_token (
  identifier text NOT NULL,
  token      text NOT NULL,
  expires    timestamptz NOT NULL,
  PRIMARY KEY (identifier, token)
);

-- Migration 007 used GRANT ... ON ALL TABLES, which only covers tables that existed at
-- grant time, and there is no ALTER DEFAULT PRIVILEGES in this repo. So the new tables
-- get NO grant automatically — the web login would silently fail to read/write sessions.
-- These explicit grants are mandatory.
GRANT SELECT, INSERT, UPDATE, DELETE ON app.accounts           TO web_reader;
GRANT SELECT, INSERT, UPDATE, DELETE ON app.sessions           TO web_reader;
GRANT SELECT, INSERT, UPDATE, DELETE ON app.verification_token TO web_reader;

-- Defense-in-depth: the web app has no free OR paid use for these two value-bearing
-- tables, so close the grant trap for them at the DB layer (the paywall choke point
-- already never reads them, but this makes a leak impossible even by mistake).
REVOKE SELECT ON core.pending_values     FROM web_reader;
REVOKE SELECT ON core.metric_value_audit FROM web_reader;

-- migrate:down

-- Restore the grants the up-migration revoked.
GRANT SELECT ON core.pending_values     TO web_reader;
GRANT SELECT ON core.metric_value_audit TO web_reader;

-- Drop child tables before the column they reference. Safe pre-launch (zero real users).
DROP TABLE IF EXISTS app.verification_token;
DROP TABLE IF EXISTS app.sessions;
DROP TABLE IF EXISTS app.accounts;

ALTER TABLE app.users
  DROP COLUMN IF EXISTS email_verified,
  DROP COLUMN IF EXISTS image,
  DROP COLUMN IF EXISTS name,
  DROP COLUMN IF EXISTS auth_id;
