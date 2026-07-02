-- migrate:up

-- Drop the weighted `fleet_capacity` metric (metric-set-build-plan.md Phase 6):
-- the arbitrary per-mode capacity weights are removed in favour of a non-ranked
-- 4-class fleet composition (Bus / Light rail / Heavy rail / Commuter rail) built
-- in the web layer from the existing per-mode `fleet_size`, so no new metric row
-- is needed for the composition itself. This reverts migration 015's
-- capacity_weight column and deletes fleet_capacity's data + catalog row.
--
-- Deletion order: metric_values / pending_values / metric_ranks (all FK
-- core.metrics(id), no cascade) before core.metrics itself.
-- core.metric_value_derivations / _inputs / metric_value_sources / _audit cascade
-- automatically off core.metric_values(id) ON DELETE CASCADE.

DELETE FROM core.metric_ranks
  WHERE metric_id = (SELECT id FROM core.metrics WHERE code = 'fleet_capacity');

DELETE FROM core.pending_values
  WHERE metric_id = (SELECT id FROM core.metrics WHERE code = 'fleet_capacity');

DELETE FROM core.metric_values
  WHERE metric_id = (SELECT id FROM core.metrics WHERE code = 'fleet_capacity');

DELETE FROM core.metrics WHERE code = 'fleet_capacity';

ALTER TABLE core.modes DROP COLUMN capacity_weight;

-- migrate:down

ALTER TABLE core.modes ADD COLUMN capacity_weight smallint;

UPDATE core.modes SET capacity_weight = CASE code
  WHEN 'bus'           THEN 1
  WHEN 'streetcar'     THEN 2
  WHEN 'light_rail'    THEN 3
  WHEN 'subway'        THEN 4
  WHEN 'commuter_rail' THEN 5
  WHEN 'brt'           THEN 1
  WHEN 'trolleybus'    THEN 1
END
WHERE code IN ('bus','streetcar','light_rail','subway','commuter_rail','brt','trolleybus');

INSERT INTO core.metrics (code, display_name, unit, unit_type, is_derived, formula, higher_is_better)
VALUES ('fleet_capacity', 'Fleet scale', 'count', 'count', false, NULL, NULL)
ON CONFLICT (code) DO NOTHING;
