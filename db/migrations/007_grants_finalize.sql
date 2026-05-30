-- migrate:up

-- Now that every table exists, grant the least-privilege reader its access:
-- SELECT-only on core (the read-only contract), full DML on app (web writes here).
-- GRANT ... ON ALL TABLES only covers tables present at grant time, which is why
-- this runs last.
GRANT SELECT ON ALL TABLES IN SCHEMA core TO web_reader;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app TO web_reader;

-- migrate:down

REVOKE SELECT ON ALL TABLES IN SCHEMA core FROM web_reader;
REVOKE SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA app FROM web_reader;
