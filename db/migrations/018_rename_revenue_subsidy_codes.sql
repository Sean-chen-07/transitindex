-- migrate:up

-- Rename two live metric codes so each reads like the statement line it holds
-- (metric-set-build-plan.md, "Naming — codes match the statement line"):
--   operating_revenue        -> total_revenue_excluding_subsidy
--                               (= the StatCan 23-10-0307 "Total revenue,
--                                excluding subsidies" measure label)
--   total_operating_subsidy  -> subsidy
--
-- core.metric_values / core.pending_values reference metrics by FK id
-- (metric_id), so the id-referencing rows follow automatically -- only the code
-- text on core.metrics moves. core.metric_equations.defines FK is unaffected
-- (both renamed codes are sourced, never a `defines`); its `display` captions
-- are refreshed to mirror the executable catalog (equations.py / seed 07).
-- Idempotent: guarded so a fresh rebuild (seeds already ship the new codes) and
-- an already-renamed DB are both no-ops.

UPDATE core.metrics
SET code = 'total_revenue_excluding_subsidy', display_name = 'Total revenue excluding subsidy'
WHERE code = 'operating_revenue';

UPDATE core.metrics
SET code = 'subsidy', display_name = 'Subsidy'
WHERE code = 'total_operating_subsidy';

UPDATE core.metric_equations SET display = 'operating_expenses = total_revenue_excluding_subsidy + subsidy'
  WHERE equation_code = 'expense_revenue_subsidy';
UPDATE core.metric_equations SET display = 'average_fare = total_revenue_excluding_subsidy / ridership'
  WHERE equation_code = 'average_fare_def';
UPDATE core.metric_equations SET display = 'farebox_recovery_ratio = total_revenue_excluding_subsidy / operating_expenses'
  WHERE equation_code = 'farebox_recovery_def';
UPDATE core.metric_equations SET display = 'subsidy_per_rider = subsidy / ridership'
  WHERE equation_code = 'subsidy_per_rider_def';

-- migrate:down

UPDATE core.metrics
SET code = 'operating_revenue', display_name = 'Operating Revenue'
WHERE code = 'total_revenue_excluding_subsidy';

UPDATE core.metrics
SET code = 'total_operating_subsidy', display_name = 'Total Operating Subsidy'
WHERE code = 'subsidy';

UPDATE core.metric_equations SET display = 'operating_expenses = operating_revenue + total_operating_subsidy'
  WHERE equation_code = 'expense_revenue_subsidy';
UPDATE core.metric_equations SET display = 'average_fare = operating_revenue / ridership'
  WHERE equation_code = 'average_fare_def';
UPDATE core.metric_equations SET display = 'farebox_recovery_ratio = operating_revenue / operating_expenses'
  WHERE equation_code = 'farebox_recovery_def';
UPDATE core.metric_equations SET display = 'subsidy_per_rider = total_operating_subsidy / ridership'
  WHERE equation_code = 'subsidy_per_rider_def';
