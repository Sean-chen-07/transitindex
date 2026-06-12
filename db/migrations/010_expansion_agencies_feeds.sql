-- migrate:up

-- Migration 010: expansion agencies + hamilton open-data source feed.
-- Adds 11 data-collection-target agencies (already in 06_agencies_full.sql for
-- the directory, now promoted to the tracked set) and the hamilton_open_data feed.
-- Idempotent (ON CONFLICT DO NOTHING throughout).
SET client_encoding = 'UTF8';

INSERT INTO core.agencies (slug, legal_name, short_name, country, subdivision, fiscal_year_end_month, currency, primary_modes) VALUES
  ('winnipeg-transit',       'Winnipeg Transit',                        'Winnipeg Transit',  'CA', 'MB', 12, 'CAD', ARRAY['bus','brt']),
  ('hamilton-street-railway','Hamilton Street Railway',                  'HSR',               'CA', 'ON', 12, 'CAD', ARRAY['bus']),
  ('brampton-transit',       'Brampton Transit',                         'Brampton Transit',  'CA', 'ON', 12, 'CAD', ARRAY['bus','brt']),
  ('grand-river-transit',    'Grand River Transit',                      'GRT',               'CA', 'ON', 12, 'CAD', ARRAY['bus','light_rail']),
  ('stl-laval',              'Société de transport de Laval',            'STL',               'CA', 'QC', 12, 'CAD', ARRAY['bus']),
  ('rtl-longueuil',          'Réseau de transport de Longueuil',         'RTL',               'CA', 'QC', 12, 'CAD', ARRAY['bus']),
  ('york-region-transit',    'York Region Transit',                      'YRT',               'CA', 'ON', 12, 'CAD', ARRAY['bus','brt']),
  ('halifax-transit',        'Halifax Transit',                          'Halifax Transit',   'CA', 'NS', 12, 'CAD', ARRAY['bus','ferry']),
  ('durham-region-transit',  'Durham Region Transit',                    'DRT',               'CA', 'ON', 12, 'CAD', ARRAY['bus']),
  ('saskatoon-transit',      'Saskatoon Transit',                        'Saskatoon Transit', 'CA', 'SK', 12, 'CAD', ARRAY['bus']),
  ('regina-transit',         'Regina Transit',                           'Regina Transit',    'CA', 'SK', 12, 'CAD', ARRAY['bus'])
ON CONFLICT (slug) DO NOTHING;

INSERT INTO core.agency_modes (agency_id, mode_id, status)
SELECT a.id, m.id, 'active'
FROM core.agencies a
JOIN core.modes m ON true
WHERE (a.slug, m.code) IN (VALUES
  ('winnipeg-transit','bus'), ('winnipeg-transit','brt'),
  ('hamilton-street-railway','bus'),
  ('brampton-transit','bus'), ('brampton-transit','brt'),
  ('grand-river-transit','bus'), ('grand-river-transit','light_rail'),
  ('stl-laval','bus'),
  ('rtl-longueuil','bus'),
  ('york-region-transit','bus'), ('york-region-transit','brt'),
  ('halifax-transit','bus'), ('halifax-transit','ferry'),
  ('durham-region-transit','bus'),
  ('saskatoon-transit','bus'),
  ('regina-transit','bus')
)
ON CONFLICT (agency_id, mode_id) DO NOTHING;

INSERT INTO core.source_feeds (code, display_name, tier, expected_cadence, enabled) VALUES
  ('hamilton_open_data', 'Hamilton HSR Open Data (ArcGIS)', 1, 'monthly', true)
ON CONFLICT (code) DO NOTHING;

-- migrate:down

DELETE FROM core.source_feeds WHERE code = 'hamilton_open_data';

DELETE FROM core.agency_modes am
USING core.agencies a
WHERE am.agency_id = a.id
  AND a.slug IN (
    'winnipeg-transit', 'hamilton-street-railway', 'brampton-transit',
    'grand-river-transit', 'stl-laval', 'rtl-longueuil', 'york-region-transit',
    'halifax-transit', 'durham-region-transit', 'saskatoon-transit', 'regina-transit'
  );

DELETE FROM core.agencies WHERE slug IN (
  'winnipeg-transit', 'hamilton-street-railway', 'brampton-transit',
  'grand-river-transit', 'stl-laval', 'rtl-longueuil', 'york-region-transit',
  'halifax-transit', 'durham-region-transit', 'saskatoon-transit', 'regina-transit'
);
