-- Audit trigger writes one row on a value-changing UPDATE (acceptance #6).
-- Fixtures roll back.
\set ON_ERROR_STOP on
BEGIN;

INSERT INTO core.agencies (slug, legal_name, subdivision) VALUES ('__test_trg__', 'Test', 'ZZ');
INSERT INTO core.reporting_periods (agency_id, period_type, start_date, end_date, label)
  SELECT id, 'annual_calendar', DATE '2024-01-01', DATE '2024-12-31', '2024'
  FROM core.agencies WHERE slug = '__test_trg__';

DO $$
DECLARE a bigint; p bigint; m bigint; v bigint; n int; ov numeric; nv numeric;
BEGIN
  SELECT id INTO a FROM core.agencies         WHERE slug = '__test_trg__';
  SELECT id INTO p FROM core.reporting_periods WHERE agency_id = a;
  SELECT id INTO m FROM core.metrics          WHERE code = 'annual_ridership';

  INSERT INTO core.metric_values (agency_id, metric_id, reporting_period_id, service_scope, value, unit, quality)
  VALUES (a, m, p, 'total', 1000, 'count', 'verified')
  RETURNING id INTO v;

  UPDATE core.metric_values SET value = 2000 WHERE id = v;

  SELECT count(*) INTO n
  FROM core.metric_value_audit WHERE metric_value_id = v AND change_type = 'update';
  IF n <> 1 THEN RAISE EXCEPTION 'TEST FAILED: expected 1 update-audit row, got %', n; END IF;

  SELECT old_value, new_value INTO ov, nv
  FROM core.metric_value_audit WHERE metric_value_id = v AND change_type = 'update';
  IF ov <> 1000 OR nv <> 2000 THEN RAISE EXCEPTION 'TEST FAILED: audit old/new wrong: %/%', ov, nv; END IF;

  RAISE NOTICE 'PASS 03_trigger';
END $$;

ROLLBACK;
