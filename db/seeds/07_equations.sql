-- Seed: the metric equation graph, mirroring the executable catalog in
-- ingest/transitindex_ingest/equations.py. kind ∈ (sum, ratio); `defines` is the
-- derived metric an equation defines (NULL for the pure constraint identities).
-- `display` is the full 'lhs = rhs' caption. Re-runnable.
INSERT INTO core.metric_equations (equation_code, kind, defines, display) VALUES
  ('expense_revenue_subsidy',    'sum',   NULL,                     'operating_expenses = total_revenue_excluding_subsidy + subsidy'),
  ('expense_components',         'sum',   NULL,                     'operating_expenses = labour_cost + energy_fuel_cost + materials_services_cost + amortization + other_operating_expenses'),
  ('earned_revenue_components',  'sum',   'other_revenue',          'total_revenue_excluding_subsidy = farebox_revenue + other_revenue'),
  ('total_revenue_def',          'sum',   NULL,                     'total_revenue = total_revenue_excluding_subsidy + subsidy'),
  ('annual_surplus_deficit_def', 'sum',   'annual_surplus_deficit', 'annual_surplus_deficit = total_revenue - total_expenses'),
  ('financial_assets_components','sum',   'other_financial_assets', 'total_financial_assets = cash_and_investments + other_financial_assets'),
  ('liabilities_components',     'sum',   'other_liabilities',      'total_liabilities = long_term_debt + other_liabilities'),
  ('non_financial_assets_components','sum','other_non_financial_assets','total_non_financial_assets = tangible_capital_assets + other_non_financial_assets'),
  ('average_fare_def',           'ratio', 'average_fare',           'average_fare = total_revenue_excluding_subsidy / ridership'),
  ('cost_per_hour_def',          'ratio', 'cost_per_hour',          'cost_per_hour = operating_expenses / revenue_service_hours'),
  ('cost_per_rider_def',         'ratio', 'cost_per_rider',         'cost_per_rider = operating_expenses / ridership'),
  ('farebox_recovery_def',       'ratio', 'farebox_recovery_ratio', 'farebox_recovery_ratio = total_revenue_excluding_subsidy / operating_expenses'),
  ('subsidy_per_rider_def',      'ratio', 'subsidy_per_rider',      'subsidy_per_rider = subsidy / ridership'),
  ('trips_per_revenue_hour_def', 'ratio', 'trips_per_revenue_hour', 'trips_per_revenue_hour = ridership / revenue_service_hours'),
  ('net_debt_def',               'sum',   'net_debt',               'net_debt = total_liabilities - total_financial_assets'),
  ('total_assets_identity',      'sum',   NULL,                     'total_assets = total_financial_assets + total_non_financial_assets'),
  ('accumulated_surplus_identity','sum',  NULL,                     'accumulated_surplus = total_assets - total_liabilities'),
  ('debt_to_assets_def',         'ratio', 'debt_to_assets',         'debt_to_assets = total_liabilities / total_assets'),
  ('net_debt_per_capita_def',    'ratio', 'net_debt_per_capita',    'net_debt_per_capita = net_debt / service_area_population')
ON CONFLICT (equation_code) DO NOTHING;
