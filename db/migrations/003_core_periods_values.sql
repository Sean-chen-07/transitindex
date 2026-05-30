-- migrate:up

-- Reporting periods are real date ranges, not year labels. Period type is per-value,
-- so one agency can carry monthly + quarterly + annual simultaneously.
CREATE TABLE core.reporting_periods (
  id          bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  agency_id   bigint NOT NULL REFERENCES core.agencies(id) ON DELETE CASCADE,
  period_type text NOT NULL CHECK (period_type IN ('monthly','quarterly','annual_calendar','annual_fiscal','ytd')),
  start_date  date NOT NULL,
  end_date    date NOT NULL,
  label       text NOT NULL,                             -- "2024", "FY2024-25", "2024-Q3", "Mar 2026"
  UNIQUE (agency_id, period_type, start_date)
);

-- The heart: one flat metric layer. A single `value` column holds counts, ratios,
-- and dollars; metrics.unit / unit_type say how to read it.
CREATE TABLE core.metric_values (
  id                            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  agency_id                     bigint NOT NULL REFERENCES core.agencies(id) ON DELETE CASCADE,
  metric_id                     bigint NOT NULL REFERENCES core.metrics(id),
  reporting_period_id           bigint NOT NULL REFERENCES core.reporting_periods(id),
  mode_id                       bigint REFERENCES core.modes(id),          -- NULL = system-wide
  service_scope                 text NOT NULL CHECK (service_scope IN ('conventional','specialized','total','system_wide')),
  value                         numeric NOT NULL,
  unit                          text NOT NULL,                            -- denormalized; guards against metric-definition drift
  currency                      text,
  quality                       text NOT NULL CHECK (quality IN ('verified','preliminary','estimated','imputed')),
  comparable_flag               boolean NOT NULL DEFAULT true,            -- false only to exclude a known-bad value
  crosscheck_value              numeric,                                  -- a source's own published figure we also compute
  crosscheck_source_document_id bigint,                                   -- FK added in 004 (source_documents not yet defined)
  restatement_of_id             bigint REFERENCES core.metric_values(id), -- revision chain
  is_current                    boolean NOT NULL DEFAULT true,
  notes                         text,
  created_at                    timestamptz NOT NULL DEFAULT now(),
  updated_at                    timestamptz NOT NULL DEFAULT now()
);

-- The one-current-value invariant as a real constraint. NULLS NOT DISTINCT (PG15+)
-- is required because mode_id is nullable and a NULL mode must still collide.
CREATE UNIQUE INDEX one_current_value
  ON core.metric_values (agency_id, metric_id, reporting_period_id, mode_id, service_scope)
  NULLS NOT DISTINCT
  WHERE is_current;

CREATE INDEX metric_values_lookup_idx ON core.metric_values (agency_id, metric_id, reporting_period_id);
CREATE INDEX metric_values_cohort_idx ON core.metric_values (metric_id, reporting_period_id); -- rank cohorts

-- migrate:down

DROP TABLE IF EXISTS core.metric_values;
DROP TABLE IF EXISTS core.reporting_periods;
