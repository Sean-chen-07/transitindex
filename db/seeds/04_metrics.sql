-- Seed: the 21 universal metrics (15 sourced + 6 derived). applicable_modes = NULL
-- (system-wide) at seed. The 6 derived carry a formula; the 15 sourced carry NULL.
-- higher_is_better: NULL = neutral (no good/bad framing). Re-runnable.
INSERT INTO core.metrics (code, display_name, unit, unit_type, is_derived, formula, higher_is_better) VALUES
  ('annual_ridership',         'Annual Ridership',          'count',    'count',    false, NULL,                                                              true),
  ('monthly_ridership',        'Monthly Ridership',         'count',    'count',    false, NULL,                                                              true),
  ('revenue_service_hours',    'Revenue Service Hours',     'hours',    'time',     false, NULL,                                                              NULL),
  ('vehicle_revenue_km',       'Vehicle Revenue Kilometres','km',       'distance', false, NULL,                                                              NULL),
  ('average_fare',             'Average Fare',              'CAD',      'currency', true,  'operating_revenue / annual_ridership',                            NULL),
  ('trips_per_revenue_hour',   'Trips per Revenue Hour',    'trips/hr', 'ratio',    true,  'annual_ridership / revenue_service_hours',                        true),
  ('on_time_performance',      'On-Time Performance',       '%',        'ratio',    false, NULL,                                                              true),
  ('operating_revenue',        'Operating Revenue',         'CAD',      'currency', false, NULL,                                                              NULL),
  ('operating_expenses',       'Operating Expenses',        'CAD',      'currency', false, NULL,                                                              NULL),
  ('total_operating_subsidy',  'Total Operating Subsidy',   'CAD',      'currency', false, NULL,                                                              NULL),
  ('labour_cost',              'Labour Cost',               'CAD',      'currency', false, NULL,                                                              NULL),
  ('energy_fuel_cost',         'Energy & Fuel Cost',        'CAD',      'currency', false, NULL,                                                              NULL),
  ('materials_services_cost',  'Materials & Services Cost', 'CAD',      'currency', false, NULL,                                                              NULL),
  ('farebox_recovery_ratio',   'Farebox Recovery Ratio',    '%',        'ratio',    true,  'operating_revenue / operating_expenses',                          NULL),
  ('cost_per_rider',           'Cost per Rider',            'CAD',      'currency', true,  'operating_expenses / annual_ridership',                           false),
  ('cost_per_hour',            'Cost per Revenue Hour',     'CAD/hr',   'currency', true,  'operating_expenses / revenue_service_hours',                      false),
  ('subsidy_per_rider',        'Subsidy per Rider',         'CAD',      'currency', true,  '(operating_expenses - operating_revenue) / annual_ridership',     NULL),
  ('fleet_size',               'Fleet Size',                'count',    'count',    false, NULL,                                                              NULL),
  ('fleet_average_age',        'Fleet Average Age',         'years',    'time',     false, NULL,                                                              false),
  ('accessible_fleet_pct',     'Accessible Fleet %',        '%',        'ratio',    false, NULL,                                                              true),
  ('capital_expenditure',      'Capital Expenditure',       'CAD',      'currency', false, NULL,                                                              NULL)
ON CONFLICT (code) DO NOTHING;
