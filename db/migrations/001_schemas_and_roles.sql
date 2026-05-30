-- migrate:up

-- Two schemas in one database. `core` = ingestion-written, web reads only.
-- `app` = web-written (users, funnel events). This split is what makes the
-- "web is a pure reader" invariant enforceable at the role level.
CREATE SCHEMA core;
CREATE SCHEMA app;

-- Least-privilege reader role for the web app. NOLOGIN (group role): it carries
-- privileges only, never a password — so no secret lands in a committed migration.
-- The real login credentials are provisioned out-of-band when Lane B ships.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'web_reader') THEN
    CREATE ROLE web_reader NOLOGIN;
  END IF;
END $$;

-- Baseline: let the reader enter both schemas. Table-level grants are applied in
-- migration 007, after every table exists (GRANT ... ON ALL TABLES only covers
-- tables that exist at grant time).
GRANT USAGE ON SCHEMA core TO web_reader;
GRANT USAGE ON SCHEMA app TO web_reader;

-- migrate:down

DROP SCHEMA IF EXISTS app CASCADE;
DROP SCHEMA IF EXISTS core CASCADE;
DO $$
BEGIN
  IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'web_reader') THEN
    EXECUTE 'DROP OWNED BY web_reader';
    EXECUTE 'DROP ROLE web_reader';
  END IF;
END $$;
