-- migrate:up

-- Staging area for extracted values awaiting review. Same shape as metric_values,
-- plus the provenance that must survive to promotion + the review workflow fields.
-- On approval -> INSERT into metric_values + metric_value_sources.
CREATE TABLE core.pending_values (
  id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  agency_id           bigint NOT NULL REFERENCES core.agencies(id) ON DELETE CASCADE,
  metric_id           bigint NOT NULL REFERENCES core.metrics(id),
  reporting_period_id bigint NOT NULL REFERENCES core.reporting_periods(id),
  mode_id             bigint REFERENCES core.modes(id),
  service_scope       text NOT NULL CHECK (service_scope IN ('conventional','specialized','total','system_wide')),
  value               numeric NOT NULL,
  unit                text NOT NULL,
  currency            text,
  quality             text NOT NULL CHECK (quality IN ('verified','preliminary','estimated','imputed')),
  comparable_flag     boolean NOT NULL DEFAULT true,
  crosscheck_value    numeric,
  -- provenance carried until promotion
  source_document_id  bigint REFERENCES core.source_documents(id) ON DELETE SET NULL,
  page_number         integer,
  table_reference     text,
  extraction_method   text CHECK (extraction_method IN ('manual','llm_assisted','structured_import','statcan_passthrough')),
  confidence          numeric CHECK (confidence >= 0 AND confidence <= 1),
  -- review workflow
  review_status       text NOT NULL DEFAULT 'pending' CHECK (review_status IN ('pending','approved','rejected','needs_edit')),
  flags               text[],                            -- yoy_spike, cross_source_disagreement, unit_mismatch, sum_mismatch
  reviewer_notes      text,
  created_at          timestamptz NOT NULL DEFAULT now(),
  updated_at          timestamptz NOT NULL DEFAULT now()
);

-- Materialized ranks. comparison_set = all | subdivision (typology dropped).
-- Only the ordinal rank is ever shown, so no minimum pool needed.
CREATE TABLE core.metric_ranks (
  id                  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  agency_id           bigint NOT NULL REFERENCES core.agencies(id) ON DELETE CASCADE,
  metric_id           bigint NOT NULL REFERENCES core.metrics(id),
  reporting_period_id bigint NOT NULL REFERENCES core.reporting_periods(id),
  comparison_set      text NOT NULL CHECK (comparison_set IN ('all','subdivision')),
  rank                integer,
  denominator         integer,
  direction           text,                              -- from metrics.higher_is_better; NULL = neutral
  computed_at         timestamptz NOT NULL DEFAULT now()
);

-- Feed catalog: backs the stale-feed UI state and the cron stall alert.
CREATE TABLE core.source_feeds (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code             text UNIQUE NOT NULL,
  display_name     text NOT NULL,
  tier             smallint,
  expected_cadence text CHECK (expected_cadence IN ('monthly','quarterly','annual')),
  enabled          boolean NOT NULL DEFAULT true
);

-- One row appended per feed run (health history).
CREATE TABLE core.feed_runs (
  id                 bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  feed_id            bigint NOT NULL REFERENCES core.source_feeds(id) ON DELETE CASCADE,
  started_at         timestamptz,
  finished_at        timestamptz,
  status             text CHECK (status IN ('ok','stalled','schema_break','error')),
  rows_fetched       integer,
  schema_fingerprint text,
  last_good_at       timestamptz,
  message            text
);

-- migrate:down

DROP TABLE IF EXISTS core.feed_runs;
DROP TABLE IF EXISTS core.source_feeds;
DROP TABLE IF EXISTS core.metric_ranks;
DROP TABLE IF EXISTS core.pending_values;
