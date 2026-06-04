-- Seed: the source-feed catalog. M1 feeds enabled; M2 feeds seeded but disabled
-- until their adapters land. Re-runnable.
INSERT INTO core.source_feeds (code, display_name, tier, expected_cadence, enabled) VALUES
  ('manual_entry',       'Manual data entry (workbook)',      0, NULL,        true),
  ('statcan_307',        'StatCan 23-10-0307',                0, 'monthly',   true),
  ('edmonton_open_data', 'Edmonton Open Data',                1, 'monthly',   true),
  ('calgary_open_data',  'Calgary Open Data',                 1, 'monthly',   true),
  ('translink_quarterly','TransLink Quarterly Report',        2, 'quarterly', false),
  ('ttc_ceo_report',     'TTC CEO Report',                    2, 'monthly',   false),
  ('oc_transpo_kpi',     'OC Transpo KPI scrape',             2, 'monthly',   false),
  ('metrolinx_ops',      'Metrolinx Operations Report',       2, 'quarterly', false),
  ('annual_report_pdfs', 'Annual report PDFs (all agencies)', 2, 'annual',    false),
  ('hamilton_open_data', 'Hamilton HSR Open Data (ArcGIS)',   1, 'monthly',   true)
ON CONFLICT (code) DO NOTHING;
