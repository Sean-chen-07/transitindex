-- migrate:up

-- Migration 022: US / NTD ingestion groundwork.
--   1. core.agencies.ntd_id — the FTA National Transit Database 5-digit reporter
--      id (zero-padded text, e.g. '00001'), the stable key US agencies are
--      matched on. Unique where present; NULL for Canadian agencies.
--   2. us_public_domain added to the source_documents.license CHECK — NTD data
--      is a US federal government work (17 U.S.C. §105), public domain.
--   3. The two NTD source feeds (tier 0, enabled).
-- The ~700 US Full Reporter agency rows themselves are generated into
-- db/seeds/08_agencies_us.sql by ingest/scripts/generate_ntd_agencies.py
-- (mirrored in transitindex_ingest/refdata_us.py) and applied as a seed.

ALTER TABLE core.agencies ADD COLUMN IF NOT EXISTS ntd_id text;

CREATE UNIQUE INDEX IF NOT EXISTS agencies_ntd_id_uq
  ON core.agencies (ntd_id) WHERE ntd_id IS NOT NULL;

ALTER TABLE core.source_documents
  DROP CONSTRAINT IF EXISTS source_documents_license_check;

ALTER TABLE core.source_documents
  ADD CONSTRAINT source_documents_license_check CHECK (license IN (
    'statcan_open',
    'ogl_toronto', 'ogl_ottawa', 'ogl_calgary', 'ogl_edmonton',
    'ogl_montreal', 'ogl_metrovancouver', 'ogl_mississauga',
    'ogl_hamilton',
    'public_document',
    'us_public_domain'
  ));

INSERT INTO core.source_feeds (code, display_name, tier, expected_cadence, enabled) VALUES
  ('ntd_monthly', 'FTA NTD Complete Monthly Ridership (Socrata 8bui-9xvu)', 0, 'monthly', true),
  ('ntd_annual',  'FTA NTD Annual Data - Metrics (Socrata ekg5-frzt)',      0, 'annual',  true)
ON CONFLICT (code) DO NOTHING;

-- migrate:down

DELETE FROM core.source_feeds WHERE code IN ('ntd_monthly', 'ntd_annual');

ALTER TABLE core.source_documents
  DROP CONSTRAINT IF EXISTS source_documents_license_check;

ALTER TABLE core.source_documents
  ADD CONSTRAINT source_documents_license_check CHECK (license IN (
    'statcan_open',
    'ogl_toronto', 'ogl_ottawa', 'ogl_calgary', 'ogl_edmonton',
    'ogl_montreal', 'ogl_metrovancouver', 'ogl_mississauga',
    'ogl_hamilton',
    'public_document'
  ));

DROP INDEX IF EXISTS core.agencies_ntd_id_uq;

ALTER TABLE core.agencies DROP COLUMN IF EXISTS ntd_id;
