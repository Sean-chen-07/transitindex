-- migrate:up

-- Financial-statement metric additions (metric-set-build-plan.md Phase 4 + 5,
-- addendum #2/#3): 5 sourced income-statement / revenue lines + 5 derived
-- residuals so the statements close, and the equations that link them. Follows
-- migration 014's balance-sheet pattern: idempotent inserts mirroring
-- db/seeds/04_metrics.sql + 07_equations.sql, so an existing DB picks them up via
-- dbmate and a fresh DB gets them from the seeds. No table changes -- these live
-- in core.metrics / core.metric_equations like every other metric. All 10
-- additions are NON-rated (never in RATED_METRICS). The three balance-sheet
-- residuals + other_revenue + annual_surplus_deficit are derived; the rest are
-- sourced. asset_consumption_ratio / accumulated_amortization /
-- gross_tangible_capital_assets are DEFERRED (addendum #3) -- not added here.
-- Catalog 31 -> 41 (the live set no longer includes fleet_capacity's successor).

INSERT INTO core.metrics (code, display_name, unit, unit_type, is_derived, formula, higher_is_better) VALUES
  ('amortization',               'Amortization',                'CAD', 'currency', false, NULL,                                                   NULL),
  ('other_operating_expenses',   'Other Operating Expenses',    'CAD', 'currency', false, NULL,                                                   NULL),
  ('total_revenue',              'Total Revenue',               'CAD', 'currency', false, NULL,                                                   NULL),
  ('farebox_revenue',            'Farebox Revenue',             'CAD', 'currency', false, NULL,                                                   NULL),
  ('total_expenses',             'Total Expenses',              'CAD', 'currency', false, NULL,                                                   NULL),
  ('other_revenue',              'Other Revenue',               'CAD', 'currency', true,  'farebox_revenue + other_revenue',                      NULL),
  ('annual_surplus_deficit',     'Annual Surplus / (Deficit)',  'CAD', 'currency', true,  'total_revenue - total_expenses',                       NULL),
  ('other_financial_assets',     'Other Financial Assets',      'CAD', 'currency', true,  'cash_and_investments + other_financial_assets',        NULL),
  ('other_liabilities',          'Other Liabilities',           'CAD', 'currency', true,  'long_term_debt + other_liabilities',                   NULL),
  ('other_non_financial_assets', 'Other Non-Financial Assets',  'CAD', 'currency', true,  'tangible_capital_assets + other_non_financial_assets', NULL)
ON CONFLICT (code) DO NOTHING;

INSERT INTO core.metric_equations (equation_code, kind, defines, display) VALUES
  ('earned_revenue_components',      'sum', 'other_revenue',              'total_revenue_excluding_subsidy = farebox_revenue + other_revenue'),
  ('total_revenue_def',              'sum', NULL,                         'total_revenue = total_revenue_excluding_subsidy + subsidy'),
  ('annual_surplus_deficit_def',     'sum', 'annual_surplus_deficit',     'annual_surplus_deficit = total_revenue - total_expenses'),
  ('financial_assets_components',    'sum', 'other_financial_assets',     'total_financial_assets = cash_and_investments + other_financial_assets'),
  ('liabilities_components',         'sum', 'other_liabilities',          'total_liabilities = long_term_debt + other_liabilities'),
  ('non_financial_assets_components','sum', 'other_non_financial_assets', 'total_non_financial_assets = tangible_capital_assets + other_non_financial_assets')
ON CONFLICT (equation_code) DO NOTHING;

-- Extend the enforced expense-components identity to the 5-term PSAB basis
-- (labour + energy + materials + amortization + other = operating_expenses); the
-- 3-term form false-flagged honest PSAB statements. Refresh the display caption.
UPDATE core.metric_equations
SET display = 'operating_expenses = labour_cost + energy_fuel_cost + materials_services_cost + amortization + other_operating_expenses'
WHERE equation_code = 'expense_components';

-- migrate:down

UPDATE core.metric_equations
SET display = 'operating_expenses = labour_cost + energy_fuel_cost + materials_services_cost'
WHERE equation_code = 'expense_components';

-- Equations first (metric_equations.defines references core.metrics.code).
DELETE FROM core.metric_equations WHERE equation_code IN (
  'earned_revenue_components','total_revenue_def','annual_surplus_deficit_def',
  'financial_assets_components','liabilities_components','non_financial_assets_components'
);
DELETE FROM core.metrics WHERE code IN (
  'amortization','other_operating_expenses','total_revenue','farebox_revenue','total_expenses',
  'other_revenue','annual_surplus_deficit','other_financial_assets','other_liabilities',
  'other_non_financial_assets'
);
