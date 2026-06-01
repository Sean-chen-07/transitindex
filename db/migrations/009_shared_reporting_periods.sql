-- migrate:up

-- Make a reporting period SHARED across agencies instead of per-agency, so agencies
-- can be ranked against each other within a comparable period.
--
-- Original contradiction (schema-design.md §3.5 vs §3.6/§3.11): reporting_periods was
-- built per-agency (UNIQUE (agency_id, period_type, start_date)), but ranking — the core
-- product feature — needs ONE shared period row per calendar period so all agencies' values
-- land in a single cohort. As built, "Mar 2026" was 5 rows (one per agency), so every rank
-- cohort had size 1 → every agency ranked "1 of 1" and the web suppressed them all.
--
-- New identity: (period_type, start_date, end_date). end_date is in the key (not just
-- start_date) so agencies with the same start but different fiscal year-ends stay in
-- distinct periods (the legitimate §3.5 concern). metric_values keeps its OWN agency_id, so
-- the one_current_value index (agency_id, metric_id, reporting_period_id, mode_id,
-- service_scope) still uniquely identifies each agency's current value after the collapse.

-- (a) Pick a surviving period id per (period_type, start_date, end_date): the lowest id.
CREATE TEMP TABLE period_remap ON COMMIT DROP AS
SELECT rp.id AS old_id,
       MIN(rp.id) OVER (PARTITION BY rp.period_type, rp.start_date, rp.end_date) AS new_id
FROM core.reporting_periods rp;

-- (b) Repoint every child row from a duplicate period to its surviving sibling.
UPDATE core.metric_values mv
  SET reporting_period_id = r.new_id
  FROM period_remap r
  WHERE mv.reporting_period_id = r.old_id AND r.old_id <> r.new_id;

UPDATE core.metric_ranks mr
  SET reporting_period_id = r.new_id
  FROM period_remap r
  WHERE mr.reporting_period_id = r.old_id AND r.old_id <> r.new_id;

UPDATE core.pending_values pv
  SET reporting_period_id = r.new_id
  FROM period_remap r
  WHERE pv.reporting_period_id = r.old_id AND r.old_id <> r.new_id;

-- (c) Delete the now-orphaned duplicate period rows.
DELETE FROM core.reporting_periods rp
  USING period_remap r
  WHERE rp.id = r.old_id AND r.old_id <> r.new_id;

-- (d) Drop the per-agency identity + the agency_id column/FK.
ALTER TABLE core.reporting_periods
  DROP CONSTRAINT reporting_periods_agency_id_period_type_start_date_key;
ALTER TABLE core.reporting_periods
  DROP CONSTRAINT reporting_periods_agency_id_fkey;
ALTER TABLE core.reporting_periods
  DROP COLUMN agency_id;

-- (e) New shared identity.
ALTER TABLE core.reporting_periods
  ADD CONSTRAINT reporting_periods_period_type_start_date_end_date_key
  UNIQUE (period_type, start_date, end_date);

-- migrate:down

-- Lossy: a period's original per-agency ownership cannot be reconstructed once periods are
-- shared, so the restored agency_id is left NULL. This down path is for local round-trip
-- testing only, never a production rollback after real multi-agency data has been pooled.
ALTER TABLE core.reporting_periods
  DROP CONSTRAINT reporting_periods_period_type_start_date_end_date_key;
ALTER TABLE core.reporting_periods
  ADD COLUMN agency_id bigint REFERENCES core.agencies(id) ON DELETE CASCADE;
-- (No UNIQUE (agency_id, period_type, start_date) is re-added: with agency_id NULL it could
--  not be satisfied for existing rows. The up-migration does not depend on it existing.)
