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
