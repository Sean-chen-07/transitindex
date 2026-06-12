-- migrate:up

-- Migration 017: reconcile primary_modes for durham-region-transit and
-- saskatoon-transit on environments where migration 010 already ran.
--
-- 010 inserted both agencies with primary_modes={bus} and runs before the
-- seeds, so ON CONFLICT (slug) DO NOTHING locked primary_modes={bus} even
-- though seed 06 (the researched census) adds their on_demand agency_modes
-- row -> primary_modes != agency_modes. 010/02/03 were corrected so fresh
-- rebuilds are consistent, but DO NOTHING never updates an existing row, so
-- already-applied databases need this explicit UPDATE.
--
-- Idempotent: the guard skips rows that already carry on_demand, so this is a
-- no-op on a fresh rebuild (where corrected 010 already inserted on_demand).

UPDATE core.agencies
SET primary_modes = array_append(primary_modes, 'on_demand')
WHERE slug IN ('durham-region-transit', 'saskatoon-transit')
  AND NOT ('on_demand' = ANY (primary_modes));

-- migrate:down

UPDATE core.agencies
SET primary_modes = array_remove(primary_modes, 'on_demand')
WHERE slug IN ('durham-region-transit', 'saskatoon-transit');
