-- migrate:up

-- Mode capacity weight: a per-MODE rail-weighting used by the derived
-- `fleet_capacity` metric (Σ capacity_weight × fleet_size(mode)) so a metro car is
-- not equated with a bus. Nullable -- NULL modes (ferry, paratransit, on_demand) are
-- excluded from the capacity aggregation. Seeded in db/seeds/01_modes.sql; a fresh DB
-- gets the values from the seed, an existing DB picks up the column here.

ALTER TABLE core.modes ADD COLUMN capacity_weight smallint;

-- migrate:down

ALTER TABLE core.modes DROP COLUMN capacity_weight;
