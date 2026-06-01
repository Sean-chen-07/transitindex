-- web_reader least-privilege contract (acceptance #7). Read-only.
--
-- We assert the *grants* with has_table_privilege rather than doing SET ROLE +
-- attempting writes. The grant is exactly what produces the rejection (no RLS is
-- enabled on these tables), and has_table_privilege is portable across hosts and
-- does not depend on role-membership / SET ROLE quirks.
\set ON_ERROR_STOP on

DO $$
BEGIN
  -- core: SELECT yes, write no
  IF NOT has_table_privilege('web_reader','core.agencies','SELECT')
     THEN RAISE EXCEPTION 'web_reader is missing SELECT on core.agencies'; END IF;
  IF has_table_privilege('web_reader','core.agencies','INSERT')
     THEN RAISE EXCEPTION 'web_reader has INSERT on core.agencies (must not)'; END IF;
  IF has_table_privilege('web_reader','core.metric_values','UPDATE')
     THEN RAISE EXCEPTION 'web_reader has UPDATE on core.metric_values (must not)'; END IF;

  -- app: write yes
  IF NOT has_table_privilege('web_reader','app.conversion_events','INSERT')
     THEN RAISE EXCEPTION 'web_reader is missing INSERT on app.conversion_events'; END IF;
  IF NOT has_table_privilege('web_reader','app.conversion_events','SELECT')
     THEN RAISE EXCEPTION 'web_reader is missing SELECT on app.conversion_events'; END IF;

  -- 008 auth tables: web_reader needs full DML (the adapter reads + writes sessions,
  -- accounts, and verification tokens). 007's GRANT ON ALL TABLES does NOT cover them.
  IF NOT has_table_privilege('web_reader','app.sessions','SELECT')
     THEN RAISE EXCEPTION 'web_reader is missing SELECT on app.sessions'; END IF;
  IF NOT has_table_privilege('web_reader','app.sessions','INSERT')
     THEN RAISE EXCEPTION 'web_reader is missing INSERT on app.sessions'; END IF;
  IF NOT has_table_privilege('web_reader','app.sessions','DELETE')
     THEN RAISE EXCEPTION 'web_reader is missing DELETE on app.sessions'; END IF;
  IF NOT has_table_privilege('web_reader','app.accounts','INSERT')
     THEN RAISE EXCEPTION 'web_reader is missing INSERT on app.accounts'; END IF;
  IF NOT has_table_privilege('web_reader','app.verification_token','INSERT')
     THEN RAISE EXCEPTION 'web_reader is missing INSERT on app.verification_token'; END IF;
  IF NOT has_table_privilege('web_reader','app.verification_token','DELETE')
     THEN RAISE EXCEPTION 'web_reader is missing DELETE on app.verification_token'; END IF;

  -- 008 defense-in-depth REVOKE: web_reader must NOT be able to read these value-bearing
  -- tables (it has neither a free nor a paid use for them).
  IF has_table_privilege('web_reader','core.pending_values','SELECT')
     THEN RAISE EXCEPTION 'web_reader still has SELECT on core.pending_values (008 REVOKE missing)'; END IF;
  IF has_table_privilege('web_reader','core.metric_value_audit','SELECT')
     THEN RAISE EXCEPTION 'web_reader still has SELECT on core.metric_value_audit (008 REVOKE missing)'; END IF;

  -- Read-only / no-DDL contract: web_reader can enter both schemas (USAGE) but can never
  -- create objects in them, so an accidental drizzle-kit push or any CREATE/ALTER is
  -- refused by Postgres, not merely by the absence of a migrate script.
  IF has_schema_privilege('web_reader','app','CREATE')
     THEN RAISE EXCEPTION 'web_reader has CREATE on schema app (must not — web never does DDL)'; END IF;
  IF has_schema_privilege('web_reader','core','CREATE')
     THEN RAISE EXCEPTION 'web_reader has CREATE on schema core (must not — web never does DDL)'; END IF;

  RAISE NOTICE 'PASS 04_grants';
END $$;
