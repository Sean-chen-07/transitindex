-- migrate:up

-- The metric equation graph + derivation provenance (backend-restructure-brief.md goal 1).
--
-- core.metric_equations is a READ-ONLY display catalog mirroring the executable
-- catalog in ingest/transitindex_ingest/equations.py (parity, like metrics <-> seeds).
-- core.metric_value_derivations + _inputs record, for every value the solver produced,
-- the equation used and the EXACT input value rows it consumed -- a citation tree that
-- bottoms out in sourced+cited values, so a back-solved number stays dispute-proof.

CREATE TABLE core.metric_equations (
  equation_code text PRIMARY KEY,
  kind          text NOT NULL CHECK (kind IN ('sum', 'ratio')),
  defines       text REFERENCES core.metrics(code),  -- metric this equation defines (NULL = a pure constraint identity)
  display       text NOT NULL                         -- human formula caption
);

CREATE TABLE core.metric_value_derivations (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  metric_value_id bigint NOT NULL REFERENCES core.metric_values(id) ON DELETE CASCADE,
  -- An equation_code from core.metric_equations, or a reserved aggregation code
  -- such as 'period_rollup' (annual = sum of the 12 monthly values). Free text by
  -- design so aggregations that are not within-period algebra can be recorded too.
  equation_code   text NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now()
);
-- A value is current+derived at most once, but superseded derived rows keep their
-- own derivation (a frozen snapshot), so this is one derivation per value row.
CREATE UNIQUE INDEX metric_value_derivations_value_idx
  ON core.metric_value_derivations (metric_value_id);

CREATE TABLE core.metric_value_derivation_inputs (
  derivation_id         bigint NOT NULL REFERENCES core.metric_value_derivations(id) ON DELETE CASCADE,
  input_metric_value_id bigint NOT NULL REFERENCES core.metric_values(id) ON DELETE CASCADE,
  PRIMARY KEY (derivation_id, input_metric_value_id)
);

-- The web is a pure reader; these carry ids + equation codes only (no raw values),
-- so exposing them for the "how we computed this" provenance display is paywall-safe.
GRANT SELECT ON core.metric_equations              TO web_reader;
GRANT SELECT ON core.metric_value_derivations      TO web_reader;
GRANT SELECT ON core.metric_value_derivation_inputs TO web_reader;

-- migrate:down

DROP TABLE IF EXISTS core.metric_value_derivation_inputs;
DROP TABLE IF EXISTS core.metric_value_derivations;
DROP TABLE IF EXISTS core.metric_equations;
