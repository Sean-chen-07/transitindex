-- Seed integrity (acceptance #2, #3, #8). Read-only; run after seeds are loaded.
-- Any failure raises an exception; run with psql -v ON_ERROR_STOP=1.
\set ON_ERROR_STOP on

DO $$
DECLARE bad int;
BEGIN
  -- Counts (#2). Agencies are now the full Canadian census (06_agencies_full.sql), a
  -- growing set — assert the 10 launch agencies are still present (the floor), not an
  -- exact count. primary_modes <-> agency_modes parity below covers every census row.
  IF (SELECT count(*) FROM core.agencies)     <  10 THEN RAISE EXCEPTION 'expected >= 10 agencies, got %',  (SELECT count(*) FROM core.agencies);     END IF;
  IF (SELECT count(*) FROM core.modes)        <> 10 THEN RAISE EXCEPTION 'expected 10 modes, got %',        (SELECT count(*) FROM core.modes);        END IF;
  IF (SELECT count(*) FROM core.metrics)      <> 32 THEN RAISE EXCEPTION 'expected 32 metrics, got %',      (SELECT count(*) FROM core.metrics);      END IF;
  IF (SELECT count(*) FROM core.source_feeds) <> 10 THEN RAISE EXCEPTION 'expected 10 source_feeds, got %', (SELECT count(*) FROM core.source_feeds); END IF;

  -- derived <-> formula presence (#8)
  IF (SELECT count(*) FROM core.metrics WHERE is_derived)                          <> 9
     THEN RAISE EXCEPTION 'expected exactly 9 derived metrics'; END IF;
  IF (SELECT count(*) FROM core.metrics WHERE is_derived AND formula IS NULL)      <> 0
     THEN RAISE EXCEPTION 'a derived metric has NULL formula'; END IF;
  IF (SELECT count(*) FROM core.metrics WHERE NOT is_derived AND formula IS NOT NULL) <> 0
     THEN RAISE EXCEPTION 'a non-derived metric carries a formula'; END IF;

  -- equation graph parity (07_equations.sql <-> equations.py): 13 equations, and every
  -- derived metric is defined by exactly one of them.
  IF (SELECT count(*) FROM core.metric_equations) <> 13
     THEN RAISE EXCEPTION 'expected 13 metric_equations, got %', (SELECT count(*) FROM core.metric_equations); END IF;
  SELECT count(*) INTO bad FROM core.metrics m
   WHERE m.is_derived
     AND NOT EXISTS (SELECT 1 FROM core.metric_equations e WHERE e.defines = m.code);
  IF bad <> 0 THEN RAISE EXCEPTION '% derived metric(s) lack a defining equation', bad; END IF;

  -- primary_modes exactly matches agency_modes, per agency (#3)
  SELECT count(*) INTO bad
  FROM core.agencies a
  WHERE ( SELECT array_agg(code ORDER BY code) FROM unnest(a.primary_modes) AS code )
        IS DISTINCT FROM
        ( SELECT array_agg(m.code ORDER BY m.code)
          FROM core.agency_modes am JOIN core.modes m ON m.id = am.mode_id
          WHERE am.agency_id = a.id );
  IF bad <> 0 THEN RAISE EXCEPTION 'primary_modes != agency_modes for % agencies', bad; END IF;

  RAISE NOTICE 'PASS 00_seed_assertions';
END $$;
