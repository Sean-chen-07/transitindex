-- one_current_value invariant, including the NULL-mode case (acceptance #5).
-- This is the load-bearing NULLS NOT DISTINCT behaviour. Fixtures roll back.
\set ON_ERROR_STOP on
BEGIN;

INSERT INTO core.agencies (slug, legal_name, subdivision) VALUES ('__test_inv__', 'Test', 'ZZ');
-- reporting_periods is shared across agencies (migration 009): no agency_id, identity
-- is (period_type, start_date, end_date). A throwaway period date avoids real-data collision.
INSERT INTO core.reporting_periods (period_type, start_date, end_date, label)
  VALUES ('annual_calendar', DATE '1900-02-01', DATE '1900-12-31', '__test_inv__');

DO $$
DECLARE a bigint; p bigint; m bigint;
BEGIN
  SELECT id INTO a FROM core.agencies          WHERE slug = '__test_inv__';
  SELECT id INTO p FROM core.reporting_periods WHERE label = '__test_inv__';
  SELECT id INTO m FROM core.metrics           WHERE code = 'ridership';

  -- first current row with mode_id NULL: ok
  INSERT INTO core.metric_values (agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, unit, quality, is_current)
  VALUES (a, m, p, NULL, 'system_wide', 100, 'count', 'verified', true);

  -- second current row, identical tuple incl. mode_id NULL: must be rejected
  BEGIN
    INSERT INTO core.metric_values (agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, unit, quality, is_current)
    VALUES (a, m, p, NULL, 'system_wide', 200, 'count', 'verified', true);
    RAISE EXCEPTION 'TEST FAILED: 2nd current row with NULL mode accepted';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;

  -- a non-current duplicate is allowed (the index is partial: WHERE is_current)
  INSERT INTO core.metric_values (agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, unit, quality, is_current)
  VALUES (a, m, p, NULL, 'system_wide', 300, 'count', 'verified', false);

  RAISE NOTICE 'PASS 02_invariants';
END $$;

ROLLBACK;
