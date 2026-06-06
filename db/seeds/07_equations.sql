-- Seed: the metric equation graph (8 equations), mirroring the executable catalog
-- in ingest/transitindex_ingest/equations.py. kind ∈ (sum, ratio); `defines` is the
-- derived metric an equation defines (NULL for the two operating-expense constraint
-- identities). `display` is the full 'lhs = rhs' caption. Re-runnable.
INSERT INTO core.metric_equations (equation_code, kind, defines, display) VALUES
  ('expense_revenue_subsidy',    'sum',   NULL,                     'operating_expenses = operating_revenue + total_operating_subsidy'),
  ('expense_components',         'sum',   NULL,                     'operating_expenses = labour_cost + energy_fuel_cost + materials_services_cost'),
  ('average_fare_def',           'ratio', 'average_fare',           'average_fare = operating_revenue / ridership'),
  ('cost_per_hour_def',          'ratio', 'cost_per_hour',          'cost_per_hour = operating_expenses / revenue_service_hours'),
  ('cost_per_rider_def',         'ratio', 'cost_per_rider',         'cost_per_rider = operating_expenses / ridership'),
  ('farebox_recovery_def',       'ratio', 'farebox_recovery_ratio', 'farebox_recovery_ratio = operating_revenue / operating_expenses'),
  ('subsidy_per_rider_def',      'ratio', 'subsidy_per_rider',      'subsidy_per_rider = total_operating_subsidy / ridership'),
  ('trips_per_revenue_hour_def', 'ratio', 'trips_per_revenue_hour', 'trips_per_revenue_hour = ridership / revenue_service_hours'),
  ('net_debt_def',               'sum',   'net_debt',               'net_debt = total_liabilities - total_financial_assets'),
  ('total_assets_identity',      'sum',   NULL,                     'total_assets = total_financial_assets + total_non_financial_assets'),
  ('accumulated_surplus_identity','sum',  NULL,                     'accumulated_surplus = total_assets - total_liabilities'),
  ('debt_to_assets_def',         'ratio', 'debt_to_assets',         'debt_to_assets = total_liabilities / total_assets'),
  ('net_debt_per_capita_def',    'ratio', 'net_debt_per_capita',    'net_debt_per_capita = net_debt / service_area_population')
ON CONFLICT (equation_code) DO NOTHING;
