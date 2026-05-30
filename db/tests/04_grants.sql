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

  RAISE NOTICE 'PASS 04_grants';
END $$;
