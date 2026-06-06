-- migrate:up

-- Balance-sheet metric family: 8 sourced PSAB line items + 3 derived (net_debt,
-- debt_to_assets, net_debt_per_capita) and their 5 equations. Folds in
-- balance-sheet-and-frequency-plan.md. Idempotent inserts mirroring
-- db/seeds/04_metrics.sql + 07_equations.sql, so an existing DB picks them up via
-- dbmate and a fresh DB gets them from the seeds. No table changes -- these live
-- in core.metrics / core.metric_equations like every other metric. Catalog 20 -> 31.

INSERT INTO core.metrics (code, display_name, unit, unit_type, is_derived, formula, higher_is_better) VALUES
  ('total_financial_assets',     'Total Financial Assets',     'CAD', 'currency', false, NULL,                                         NULL),
  ('total_liabilities',          'Total Liabilities',          'CAD', 'currency', false, NULL,                                         NULL),
  ('total_non_financial_assets', 'Total Non-Financial Assets', 'CAD', 'currency', false, NULL,                                         NULL),
  ('total_assets',               'Total Assets',               'CAD', 'currency', false, NULL,                                         NULL),
  ('tangible_capital_assets',    'Tangible Capital Assets',    'CAD', 'currency', false, NULL,                                         NULL),
  ('accumulated_surplus',        'Accumulated Surplus',        'CAD', 'currency', false, NULL,                                         NULL),
  ('long_term_debt',             'Long-Term Debt',             'CAD', 'currency', false, NULL,                                         NULL),
  ('cash_and_investments',       'Cash & Investments',         'CAD', 'currency', false, NULL,                                         NULL),
  ('net_debt',                   'Net Debt',                   'CAD', 'currency', true,  'total_liabilities - total_financial_assets', false),
  ('debt_to_assets',             'Debt to Assets',             '%',   'ratio',    true,  'total_liabilities / total_assets',           false),
  ('net_debt_per_capita',        'Net Debt per Capita',        'CAD', 'currency', true,  'net_debt / service_area_population',         false)
ON CONFLICT (code) DO NOTHING;

INSERT INTO core.metric_equations (equation_code, kind, defines, display) VALUES
  ('net_debt_def',                'sum',   'net_debt',            'net_debt = total_liabilities - total_financial_assets'),
  ('total_assets_identity',       'sum',   NULL,                  'total_assets = total_financial_assets + total_non_financial_assets'),
  ('accumulated_surplus_identity','sum',   NULL,                  'accumulated_surplus = total_assets - total_liabilities'),
  ('debt_to_assets_def',          'ratio', 'debt_to_assets',      'debt_to_assets = total_liabilities / total_assets'),
  ('net_debt_per_capita_def',     'ratio', 'net_debt_per_capita', 'net_debt_per_capita = net_debt / service_area_population')
ON CONFLICT (equation_code) DO NOTHING;

-- migrate:down

-- Equations first (metric_equations.defines references core.metrics.code).
DELETE FROM core.metric_equations WHERE equation_code IN (
  'net_debt_def','total_assets_identity','accumulated_surplus_identity',
  'debt_to_assets_def','net_debt_per_capita_def'
);
DELETE FROM core.metrics WHERE code IN (
  'total_financial_assets','total_liabilities','total_non_financial_assets','total_assets',
  'tangible_capital_assets','accumulated_surplus','long_term_debt','cash_and_investments',
  'net_debt','debt_to_assets','net_debt_per_capita'
);
