-- Seed: the 10 launch agencies. service_area_population left NULL (populate later
-- from census/agency reports - do not fabricate). primary_modes mirrors the
-- agency_modes rows seeded in 03. Re-runnable (ON CONFLICT DO NOTHING).
SET client_encoding = 'UTF8';

INSERT INTO core.agencies (slug, legal_name, short_name, country, subdivision, fiscal_year_end_month, currency, primary_modes) VALUES
  ('ttc',                'Toronto Transit Commission',                                  'TTC',              'CA', 'ON', 12, 'CAD', ARRAY['bus','subway','streetcar','paratransit']),
  ('stm',                'Société de transport de Montréal',                            'STM',              'CA', 'QC', 12, 'CAD', ARRAY['bus','subway']),
  ('translink',          'South Coast British Columbia Transportation Authority',       'TransLink',        'CA', 'BC', 12, 'CAD', ARRAY['bus','subway','commuter_rail','ferry','paratransit']),
  ('metrolinx',          'Metrolinx (GO Transit)',                                      'Metrolinx',        'CA', 'ON',  3, 'CAD', ARRAY['commuter_rail','bus']),
  ('oc-transpo',         'OC Transpo (City of Ottawa)',                                 'OC Transpo',       'CA', 'ON', 12, 'CAD', ARRAY['bus','light_rail']),
  ('calgary-transit',    'Calgary Transit',                                             'Calgary Transit',  'CA', 'AB', 12, 'CAD', ARRAY['bus','light_rail']),
  ('edmonton-ets',       'Edmonton Transit Service',                                    'ETS',              'CA', 'AB', 12, 'CAD', ARRAY['bus','light_rail']),
  ('miway',              'MiWay (City of Mississauga)',                                 'MiWay',            'CA', 'ON', 12, 'CAD', ARRAY['bus']),
  ('bc-transit',         'BC Transit',                                                  'BC Transit',       'CA', 'BC',  3, 'CAD', ARRAY['bus']),
  ('burlington-transit', 'Burlington Transit',                                          'Burlington Transit','CA','ON', 12, 'CAD', ARRAY['bus'])
ON CONFLICT (slug) DO NOTHING;
