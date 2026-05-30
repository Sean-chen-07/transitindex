-- migrate:up

-- Transit modes (bus, subway, ...). Reference table; `code` is the stable handle.
CREATE TABLE core.modes (
  id           bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code         text UNIQUE NOT NULL,
  display_name text NOT NULL,
  description  text
);

-- Agencies. `typology` was dropped (2026-05-30): modes + service_area_population
-- carry agency scale instead.
CREATE TABLE core.agencies (
  id                      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  slug                    text UNIQUE NOT NULL,
  legal_name              text NOT NULL,
  short_name              text,
  country                 text NOT NULL DEFAULT 'CA',
  subdivision             text NOT NULL,                 -- province/state code
  service_area_population integer,                       -- nullable scale signal
  primary_modes           text[],                        -- denormalized from agency_modes; kept in sync
  fiscal_year_end_month   smallint NOT NULL DEFAULT 12 CHECK (fiscal_year_end_month BETWEEN 1 AND 12),
  currency                text NOT NULL DEFAULT 'CAD',
  parent_agency_id        bigint REFERENCES core.agencies(id),
  created_at              timestamptz NOT NULL DEFAULT now(),
  updated_at              timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX agencies_subdivision_idx ON core.agencies (subdivision);
CREATE INDEX agencies_parent_idx      ON core.agencies (parent_agency_id);

-- Agency <-> mode many-to-many.
CREATE TABLE core.agency_modes (
  agency_id    bigint NOT NULL REFERENCES core.agencies(id) ON DELETE CASCADE,
  mode_id      bigint NOT NULL REFERENCES core.modes(id),
  year_started smallint,
  status       text NOT NULL DEFAULT 'active' CHECK (status IN ('active','planned','discontinued')),
  PRIMARY KEY (agency_id, mode_id)
);

-- Metric definitions (not values). Universal set; mode-specific splits attach via
-- metric_values.mode_id later, not via separate metric rows.
CREATE TABLE core.metrics (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code             text UNIQUE NOT NULL,
  display_name     text NOT NULL,
  description      text,
  unit             text NOT NULL,
  unit_type        text CHECK (unit_type IN ('count','ratio','currency','time','distance')),
  applicable_modes text[],                               -- NULL = universal/system-wide
  is_derived       boolean NOT NULL DEFAULT false,
  formula          text,
  higher_is_better boolean,                              -- NULL = neutral (no good/bad framing)
  cuta_reference   text,                                 -- internal consistency only, never shown
  ntd_reference    text                                  -- future US field mapping
);

-- migrate:down

DROP TABLE IF EXISTS core.metrics;
DROP TABLE IF EXISTS core.agency_modes;
DROP TABLE IF EXISTS core.agencies;
DROP TABLE IF EXISTS core.modes;
