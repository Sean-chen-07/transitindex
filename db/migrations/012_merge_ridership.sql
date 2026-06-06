-- migrate:up

-- Merge `monthly_ridership` + `annual_ridership` into ONE `ridership` metric:
-- period granularity (monthly / quarterly / annual) is the reporting period's
-- DIMENSION, not part of the metric code (backend-restructure-brief.md goal 2).
--
-- On a fresh DB this runs before seeds (core.metrics empty): it just ensures the
-- `ridership` row exists and the repoint/delete are no-ops. On an already-seeded
-- DB it repoints any existing children and drops the two old codes. Either way the
-- catalog ends at 20 metrics with `ridership` present (db/seeds/04_metrics.sql).

-- Ensure the merged metric exists (idempotent; mirrors 04_metrics.sql).
INSERT INTO core.metrics (code, display_name, unit, unit_type, is_derived, formula, higher_is_better)
VALUES ('ridership', 'Ridership', 'count', 'count', false, NULL, true)
ON CONFLICT (code) DO NOTHING;

DO $$
DECLARE
  rid  bigint;
  olds bigint[];
  dup  int;
BEGIN
  SELECT id INTO rid FROM core.metrics WHERE code = 'ridership';
  SELECT array_agg(id) INTO olds
    FROM core.metrics WHERE code IN ('annual_ridership', 'monthly_ridership');
  IF olds IS NULL THEN
    RETURN;  -- fresh DB: the old codes were never seeded; nothing to repoint
  END IF;

  -- Guard: no single CURRENT (agency, period, mode, scope) tuple may hold BOTH old
  -- codes -- after the merge they would collide on the one_current_value index.
  SELECT count(*) INTO dup FROM (
    SELECT 1 FROM core.metric_values
    WHERE is_current AND metric_id = ANY(olds)
    GROUP BY agency_id, reporting_period_id, mode_id, service_scope
    HAVING count(*) > 1
  ) c;
  IF dup > 0 THEN
    RAISE EXCEPTION 'ridership merge aborted: % current tuple(s) hold both old codes', dup;
  END IF;

  -- Guard: no single rank cohort (agency, period, comparison_set) may hold both.
  SELECT count(*) INTO dup FROM (
    SELECT 1 FROM core.metric_ranks
    WHERE metric_id = ANY(olds)
    GROUP BY agency_id, reporting_period_id, comparison_set
    HAVING count(*) > 1
  ) c;
  IF dup > 0 THEN
    RAISE EXCEPTION 'ridership merge aborted: % rank cohort(s) hold both old codes', dup;
  END IF;

  -- Repoint children. metric_values' value is unchanged, so the audit trigger
  -- (fires only on value change) correctly records nothing for a metric_id repoint.
  UPDATE core.metric_ranks   SET metric_id = rid WHERE metric_id = ANY(olds);
  UPDATE core.metric_values  SET metric_id = rid WHERE metric_id = ANY(olds);
  UPDATE core.pending_values SET metric_id = rid WHERE metric_id = ANY(olds);

  -- Drop the old codes. The metric_values.metric_id FK has no ON DELETE action,
  -- so this fails loudly if any child row was missed -- a deliberate safety net.
  DELETE FROM core.metrics WHERE id = ANY(olds);
END $$;

-- Sync the derived formula captions to the catalog (display only; the solver uses
-- equations.py). Explicit assignments also normalize subsidy_per_rider to the linked
-- form total_operating_subsidy / ridership. Idempotent.
UPDATE core.metrics SET formula = 'operating_revenue / ridership'            WHERE code = 'average_fare';
UPDATE core.metrics SET formula = 'ridership / revenue_service_hours'        WHERE code = 'trips_per_revenue_hour';
UPDATE core.metrics SET formula = 'operating_revenue / operating_expenses'   WHERE code = 'farebox_recovery_ratio';
UPDATE core.metrics SET formula = 'operating_expenses / ridership'           WHERE code = 'cost_per_rider';
UPDATE core.metrics SET formula = 'operating_expenses / revenue_service_hours' WHERE code = 'cost_per_hour';
UPDATE core.metrics SET formula = 'total_operating_subsidy / ridership'      WHERE code = 'subsidy_per_rider';

-- migrate:down

-- Re-split is lossy: a merged `ridership` row is reclassified by its reporting
-- period's granularity (monthly -> monthly_ridership, else annual_ridership). For
-- local round-trip testing only, never a production rollback after real data lands.
INSERT INTO core.metrics (code, display_name, unit, unit_type, is_derived, formula, higher_is_better) VALUES
  ('annual_ridership',  'Annual Ridership',  'count', 'count', false, NULL, true),
  ('monthly_ridership', 'Monthly Ridership', 'count', 'count', false, NULL, true)
ON CONFLICT (code) DO NOTHING;

DO $$
DECLARE rid bigint; ann bigint; mon bigint;
BEGIN
  SELECT id INTO rid FROM core.metrics WHERE code = 'ridership';
  SELECT id INTO ann FROM core.metrics WHERE code = 'annual_ridership';
  SELECT id INTO mon FROM core.metrics WHERE code = 'monthly_ridership';
  IF rid IS NULL THEN RETURN; END IF;

  UPDATE core.metric_values mv
    SET metric_id = CASE WHEN rp.period_type = 'monthly' THEN mon ELSE ann END
    FROM core.reporting_periods rp
    WHERE mv.reporting_period_id = rp.id AND mv.metric_id = rid;
  UPDATE core.metric_ranks mr
    SET metric_id = CASE WHEN rp.period_type = 'monthly' THEN mon ELSE ann END
    FROM core.reporting_periods rp
    WHERE mr.reporting_period_id = rp.id AND mr.metric_id = rid;
  UPDATE core.pending_values pv
    SET metric_id = CASE WHEN rp.period_type = 'monthly' THEN mon ELSE ann END
    FROM core.reporting_periods rp
    WHERE pv.reporting_period_id = rp.id AND pv.metric_id = rid;

  DELETE FROM core.metrics WHERE id = rid;
END $$;

UPDATE core.metrics SET formula = 'operating_revenue / annual_ridership'                       WHERE code = 'average_fare';
UPDATE core.metrics SET formula = 'annual_ridership / revenue_service_hours'                   WHERE code = 'trips_per_revenue_hour';
UPDATE core.metrics SET formula = 'operating_expenses / annual_ridership'                      WHERE code = 'cost_per_rider';
UPDATE core.metrics SET formula = '(operating_expenses - operating_revenue) / annual_ridership' WHERE code = 'subsidy_per_rider';
