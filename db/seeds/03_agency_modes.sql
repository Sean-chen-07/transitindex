-- Seed: agency <-> mode links. Resolved by slug/code (identity ids are not hardcoded).
-- Must match each agency's primary_modes array in 02. Re-runnable.
INSERT INTO core.agency_modes (agency_id, mode_id, status)
SELECT a.id, m.id, 'active'
FROM core.agencies a
JOIN core.modes m ON true
WHERE (a.slug, m.code) IN (VALUES
  ('ttc','bus'), ('ttc','subway'), ('ttc','streetcar'), ('ttc','paratransit'),
  ('stm','bus'), ('stm','subway'),
  ('translink','bus'), ('translink','subway'), ('translink','commuter_rail'), ('translink','ferry'), ('translink','paratransit'),
  ('metrolinx','commuter_rail'), ('metrolinx','bus'),
  ('oc-transpo','bus'), ('oc-transpo','light_rail'),
  ('calgary-transit','bus'), ('calgary-transit','light_rail'),
  ('edmonton-ets','bus'), ('edmonton-ets','light_rail'),
  ('miway','bus'),
  ('bc-transit','bus'),
  ('burlington-transit','bus'),
  -- expansion agencies
  ('winnipeg-transit','bus'), ('winnipeg-transit','brt'),
  ('hamilton-street-railway','bus'),
  ('brampton-transit','bus'), ('brampton-transit','brt'),
  ('grand-river-transit','bus'), ('grand-river-transit','light_rail'),
  ('stl-laval','bus'),
  ('rtl-longueuil','bus'),
  ('york-region-transit','bus'), ('york-region-transit','brt'),
  ('halifax-transit','bus'), ('halifax-transit','ferry'),
  ('durham-region-transit','bus'), ('durham-region-transit','on_demand'),
  ('saskatoon-transit','bus'), ('saskatoon-transit','on_demand'),
  ('regina-transit','bus')
)
ON CONFLICT (agency_id, mode_id) DO NOTHING;
