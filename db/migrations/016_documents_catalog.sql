-- migrate:up

-- The PDF catalog + scan work-queue. One row per source PDF held in cloud
-- object storage (Supabase Storage). Distinct from core.source_documents:
-- source_documents is per-value provenance, created lazily when a value is
-- extracted; this table is the operator's inventory of every collected PDF and
-- tracks whether it has been scanned yet. A successful scan links back to the
-- source_documents row it produced (source_document_id).
CREATE TABLE core.documents (
  id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  agency_id           bigint NOT NULL REFERENCES core.agencies(id) ON DELETE CASCADE,
  year                smallint NOT NULL,                 -- nominal report year; FY agencies by year-END
  -- The richer, operator-facing doc vocabulary (from pdfs/MANIFEST.md). Mapped to
  -- the narrower core.source_documents.document_type at scan time (see catalog.py).
  doc_type            text NOT NULL CHECK (doc_type IN
                        ('annual_report','financial_statement','service_plan',
                         'business_plan','community_report')),
  author_label        text NOT NULL CHECK (author_label IN ('T','C')),  -- [T] transit-own / [C] city
  storage_key         text NOT NULL UNIQUE,              -- path within the bucket, e.g. ttc/ttc-2019.pdf
  source_url          text,                              -- where the PDF was obtained (nullable; backfilled)
  file_hash           text,                              -- sha256 of the stored bytes; detects re-uploads
  file_bytes          bigint,                            -- size, for display
  scan_status         text NOT NULL DEFAULT 'unscanned'
                        CHECK (scan_status IN ('unscanned','scanned','failed')),
  scanned_at          timestamptz,
  staged_count        integer,                           -- pending_values rows the last scan produced
  last_error          text,                              -- failure message when scan_status='failed'
  source_document_id  bigint REFERENCES core.source_documents(id) ON DELETE SET NULL,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now(),
  -- One catalog row per (agency, year, doc kind, author). e.g. Edmonton 2019 has
  -- both a city financial_statement [C] and an ETS service_plan [T] — different rows.
  UNIQUE (agency_id, year, doc_type, author_label)
);

CREATE INDEX documents_scan_status_idx ON core.documents (scan_status);

-- The web app reads this (read-only) to render the operator console / any future
-- public "sources" listing. Writes happen only from the ingest role.
GRANT SELECT ON core.documents TO web_reader;

-- migrate:down

DROP TABLE IF EXISTS core.documents;
