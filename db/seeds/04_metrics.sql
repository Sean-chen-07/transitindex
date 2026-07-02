-- Seed: the 42 universal metrics (28 sourced + 14 derived). applicable_modes = NULL
-- (system-wide) at seed. The derived carry a formula; the sourced carry NULL.
-- higher_is_better: NULL = neutral (no good/bad framing). Re-runnable.
-- Ridership is ONE metric; monthly vs annual is the reporting period's granularity.
-- The balance-sheet family (8 sourced + 3 derived) precedes the 10 financial-
-- statement additions (metric-set-build-plan.md Phase 4): 5 sourced income-statement /
-- revenue lines + 5 derived residuals. All 10 additions are non-rated.
INSERT INTO core.metrics (code, display_name, unit, unit_type, is_derived, formula, higher_is_better) VALUES
  ('ridership',                'Ridership',                 'count',    'count',    false, NULL,                                                              true),
  ('revenue_service_hours',    'Revenue Service Hours',     'hours',    'time',     false, NULL,                                                              NULL),
  ('vehicle_revenue_km',       'Vehicle Revenue Kilometres','km',       'distance', false, NULL,                                                              NULL),
  ('average_fare',             'Average Fare',              'CAD',      'currency', true,  'farebox_revenue / ridership',                                     NULL),
  ('trips_per_revenue_hour',   'Trips per Revenue Hour',    'trips/hr', 'ratio',    true,  'ridership / revenue_service_hours',                               true),
  ('on_time_performance',      'On-Time Performance',       '%',        'ratio',    false, NULL,                                                              true),
  ('total_revenue_excluding_subsidy', 'Total revenue excluding subsidy', 'CAD',   'currency', false, NULL,                                                     NULL),
  ('operating_expenses',       'Operating Expenses',        'CAD',      'currency', false, NULL,                                                              NULL),
  ('subsidy',                  'Subsidy',                   'CAD',      'currency', false, NULL,                                                              NULL),
  ('labour_cost',              'Labour Cost',               'CAD',      'currency', false, NULL,                                                              NULL),
  ('energy_fuel_cost',         'Energy & Fuel Cost',        'CAD',      'currency', false, NULL,                                                              NULL),
  ('materials_services_cost',  'Materials & Services Cost', 'CAD',      'currency', false, NULL,                                                              NULL),
  ('farebox_recovery_ratio',   'Farebox Recovery Ratio',    '%',        'ratio',    true,  'farebox_revenue / operating_expenses',                            NULL),
  ('cost_per_rider',           'Cost per Rider',            'CAD',      'currency', true,  'operating_expenses / ridership',                                  false),
  ('cost_per_hour',            'Cost per Revenue Hour',     'CAD/hr',   'currency', true,  'operating_expenses / revenue_service_hours',                      false),
  ('subsidy_per_rider',        'Subsidy per Rider',         'CAD',      'currency', true,  'subsidy / ridership',                                             NULL),
  ('fleet_size',               'Fleet Size',                'count',    'count',    false, NULL,                                                              NULL),
  ('fleet_average_age',        'Fleet Average Age',         'years',    'time',     false, NULL,                                                              false),
  ('accessible_fleet_pct',     'Accessible Fleet %',        '%',        'ratio',    false, NULL,                                                              true),
  ('fleet_capacity',           'Fleet scale',               'count',    'count',    false, NULL,                                                              NULL),
  ('capital_expenditure',      'Capital Expenditure',       'CAD',      'currency', false, NULL,                                                              NULL),
  ('total_financial_assets',     'Total Financial Assets',     'CAD', 'currency', false, NULL,                                          NULL),
  ('total_liabilities',          'Total Liabilities',          'CAD', 'currency', false, NULL,                                          NULL),
  ('total_non_financial_assets', 'Total Non-Financial Assets', 'CAD', 'currency', false, NULL,                                          NULL),
  ('total_assets',               'Total Assets',               'CAD', 'currency', false, NULL,                                          NULL),
  ('tangible_capital_assets',    'Tangible Capital Assets',    'CAD', 'currency', false, NULL,                                          NULL),
  ('accumulated_surplus',        'Accumulated Surplus',        'CAD', 'currency', false, NULL,                                          NULL),
  ('long_term_debt',             'Long-Term Debt',             'CAD', 'currency', false, NULL,                                          NULL),
  ('cash_and_investments',       'Cash & Investments',         'CAD', 'currency', false, NULL,                                          NULL),
  ('net_debt',                   'Net Debt',                   'CAD', 'currency', true,  'total_liabilities - total_financial_assets',  false),
  ('debt_to_assets',             'Debt to Assets',             '%',   'ratio',    true,  'total_liabilities / total_assets',            false),
  ('net_debt_per_capita',        'Net Debt per Capita',        'CAD', 'currency', true,  'net_debt / service_area_population',          false),
  -- financial-statement additions (Phase 4): 5 sourced + 5 derived residuals, all non-rated
  ('amortization',                 'Amortization',                    'CAD', 'currency', false, NULL,                                                 NULL),
  ('other_operating_expenses',     'Other Operating Expenses',        'CAD', 'currency', false, NULL,                                                 NULL),
  ('total_revenue',                'Total Revenue',                   'CAD', 'currency', false, NULL,                                                 NULL),
  ('farebox_revenue',              'Farebox Revenue',                 'CAD', 'currency', false, NULL,                                                 NULL),
  ('total_expenses',               'Total Expenses',                  'CAD', 'currency', false, NULL,                                                 NULL),
  ('other_revenue',                'Other Revenue',                   'CAD', 'currency', true,  'farebox_revenue + other_revenue',                    NULL),
  ('annual_surplus_deficit',       'Annual Surplus / (Deficit)',      'CAD', 'currency', true,  'total_revenue - total_expenses',                     NULL),
  ('other_financial_assets',       'Other Financial Assets',          'CAD', 'currency', true,  'cash_and_investments + other_financial_assets',      NULL),
  ('other_liabilities',            'Other Liabilities',               'CAD', 'currency', true,  'long_term_debt + other_liabilities',                 NULL),
  ('other_non_financial_assets',   'Other Non-Financial Assets',      'CAD', 'currency', true,  'tangible_capital_assets + other_non_financial_assets', NULL)
ON CONFLICT (code) DO NOTHING;
