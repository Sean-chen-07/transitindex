-- CHECK + FK enforcement (acceptance #4). All fixtures roll back at the end.
\set ON_ERROR_STOP on
BEGIN;

INSERT INTO core.agencies (slug, legal_name, subdivision) VALUES ('__test_con__', 'Test', 'ZZ');
-- reporting_periods is shared across agencies (migration 009): no agency_id, identity
-- is (period_type, start_date, end_date). A throwaway period date avoids real-data collision.
INSERT INTO core.reporting_periods (period_type, start_date, end_date, label)
  VALUES ('annual_calendar', DATE '1900-01-01', DATE '1900-12-31', '__test_con__');

DO $$
DECLARE a bigint; p bigint; m bigint;
BEGIN
  SELECT id INTO a FROM core.agencies          WHERE slug = '__test_con__';
  SELECT id INTO p FROM core.reporting_periods WHERE label = '__test_con__';
  SELECT id INTO m FROM core.metrics           WHERE code = 'ridership';

  -- bad service_scope -> rejected
  BEGIN
    INSERT INTO core.metric_values (agency_id, metric_id, reporting_period_id, service_scope, value, unit, quality)
    VALUES (a, m, p, 'bogus_scope', 1, 'count', 'verified');
    RAISE EXCEPTION 'TEST FAILED: bad service_scope accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;

  -- bad quality -> rejected
  BEGIN
    INSERT INTO core.metric_values (agency_id, metric_id, reporting_period_id, service_scope, value, unit, quality)
    VALUES (a, m, p, 'total', 1, 'count', 'bogus_quality');
    RAISE EXCEPTION 'TEST FAILED: bad quality accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;

  -- FK orphan (nonexistent agency) -> rejected
  BEGIN
    INSERT INTO core.metric_values (agency_id, metric_id, reporting_period_id, service_scope, value, unit, quality)
    VALUES (999999999, m, p, 'total', 1, 'count', 'verified');
    RAISE EXCEPTION 'TEST FAILED: FK orphan accepted';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;

  RAISE NOTICE 'PASS 01_constraints';
END $$;

ROLLBACK;
