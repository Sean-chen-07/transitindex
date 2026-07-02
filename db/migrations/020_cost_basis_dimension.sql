-- migrate:up

-- cost_basis dimension (metric-set-build-plan.md Phase 3): the accounting basis
-- of an expense value. 'operating' EXCLUDES amortization (the CUTA/NTD operating
-- basis that the ranked ratios must use); 'psab_total' INCLUDES it (a PSAB
-- statement-of-operations total). This is a DIFFERENT axis from the extractor's
-- actual/budget/forecast/restated `basis` and from service_scope -- it exists so a
-- PSAB-basis expense is never silently ranked against a CUTA-basis one. Default
-- 'operating': the only basis any existing row was recorded on. Mirrors
-- contract.CostBasis / COST_BASES and web/src/db/schema/core.ts.

ALTER TABLE core.metric_values
  ADD COLUMN cost_basis text NOT NULL DEFAULT 'operating'
  CHECK (cost_basis IN ('operating','psab_total'));

ALTER TABLE core.pending_values
  ADD COLUMN cost_basis text NOT NULL DEFAULT 'operating'
  CHECK (cost_basis IN ('operating','psab_total'));

-- The NOT NULL DEFAULT backfills every existing row to 'operating' in place.

-- The ranked rider-share ratios take farebox_revenue as the numerator, not the
-- broad total_revenue_excluding_subsidy (metric-set-build-plan.md Phase 3,
-- Decision #4) -- else they inflate for capital-heavy agencies. Move the
-- numerators on existing DBs to match equations.py / the seeds.
UPDATE core.metrics SET formula = 'farebox_revenue / ridership'
  WHERE code = 'average_fare';
UPDATE core.metrics SET formula = 'farebox_revenue / operating_expenses'
  WHERE code = 'farebox_recovery_ratio';
UPDATE core.metric_equations SET display = 'average_fare = farebox_revenue / ridership'
  WHERE equation_code = 'average_fare_def';
UPDATE core.metric_equations SET display = 'farebox_recovery_ratio = farebox_revenue / operating_expenses'
  WHERE equation_code = 'farebox_recovery_def';

-- migrate:down

UPDATE core.metric_equations SET display = 'farebox_recovery_ratio = total_revenue_excluding_subsidy / operating_expenses'
  WHERE equation_code = 'farebox_recovery_def';
UPDATE core.metric_equations SET display = 'average_fare = total_revenue_excluding_subsidy / ridership'
  WHERE equation_code = 'average_fare_def';
UPDATE core.metrics SET formula = 'total_revenue_excluding_subsidy / operating_expenses'
  WHERE code = 'farebox_recovery_ratio';
UPDATE core.metrics SET formula = 'total_revenue_excluding_subsidy / ridership'
  WHERE code = 'average_fare';

ALTER TABLE core.pending_values DROP COLUMN cost_basis;
ALTER TABLE core.metric_values DROP COLUMN cost_basis;
