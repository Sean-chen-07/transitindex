-- Seed: the 10 transit modes. Re-runnable (ON CONFLICT DO NOTHING).
INSERT INTO core.modes (code, display_name, description) VALUES
  ('bus',           'Bus',                    'Fixed-route conventional bus service'),
  ('subway',        'Subway / Metro',         'Grade-separated heavy rapid transit (incl. TransLink SkyTrain)'),
  ('light_rail',    'Light Rail (LRT)',       'Light rail transit'),
  ('commuter_rail', 'Commuter Rail',          'Regional/commuter heavy rail'),
  ('streetcar',     'Streetcar / Tram',       'Street-running rail'),
  ('brt',           'Bus Rapid Transit (BRT)','Dedicated-lane rapid bus'),
  ('trolleybus',    'Trolleybus',             'Overhead-electric bus'),
  ('ferry',         'Ferry',                  'Passenger water transit'),
  ('paratransit',   'Paratransit',            'Specialized accessible/door-to-door service'),
  ('on_demand',     'On-Demand Transit',      'Dynamically routed/booked service')
ON CONFLICT (code) DO NOTHING;

-- Capacity weights for the derived `fleet_capacity` metric (rail-weighted fleet
-- count). ON CONFLICT DO NOTHING above will not touch existing rows, so set the
-- weights explicitly here. The 7 weighted modes are listed; ferry, paratransit,
-- and on_demand keep capacity_weight NULL (excluded from capacity).
UPDATE core.modes SET capacity_weight = CASE code
  WHEN 'bus'           THEN 1
  WHEN 'streetcar'     THEN 2
  WHEN 'light_rail'    THEN 3
  WHEN 'subway'        THEN 4
  WHEN 'commuter_rail' THEN 5
  WHEN 'brt'           THEN 1
  WHEN 'trolleybus'    THEN 1
END
WHERE code IN ('bus','streetcar','light_rail','subway','commuter_rail','brt','trolleybus');
