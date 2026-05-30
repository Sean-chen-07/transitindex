-- migrate:up

-- Source documents. license drives the mandatory attribution string. Raw non-API
-- files (PDFs, scraped pages) are archived to cloud storage at archive_uri.
CREATE TABLE core.source_documents (
  id               bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  agency_id        bigint REFERENCES core.agencies(id) ON DELETE SET NULL,
  document_type    text NOT NULL CHECK (document_type IN
                     ('annual_report','quarterly_update','budget','ceo_report','board_report',
                      'statcan_table','open_data_csv','gtfs','manual_entry','press_release')),
  title            text,
  publication_date date,
  source_url       text,
  archive_uri      text,                                 -- cloud-storage key of the saved raw file
  file_hash        text,                                 -- detects changes on re-fetch
  license          text CHECK (license IN
                     ('statcan_open','ogl_toronto','ogl_ottawa','ogl_calgary','ogl_edmonton',
                      'ogl_montreal','ogl_metrovancouver','ogl_mississauga','public_document')),
  retrieved_at     timestamptz,
  verified_at      timestamptz,
  verified_by      text
);

-- Now that source_documents exists, wire up the crosscheck FK left dangling in 003.
ALTER TABLE core.metric_values
  ADD CONSTRAINT metric_values_crosscheck_source_fk
  FOREIGN KEY (crosscheck_source_document_id) REFERENCES core.source_documents(id) ON DELETE SET NULL;

-- Links a value to its source(s). A value can have several (published-vs-calculated cross-check).
CREATE TABLE core.metric_value_sources (
  metric_value_id    bigint NOT NULL REFERENCES core.metric_values(id) ON DELETE CASCADE,
  source_document_id bigint NOT NULL REFERENCES core.source_documents(id) ON DELETE CASCADE,
  page_number        integer,
  table_reference    text,                               -- "Table 4.2"
  extraction_method  text CHECK (extraction_method IN ('manual','llm_assisted','structured_import','statcan_passthrough')),
  confidence         numeric CHECK (confidence >= 0 AND confidence <= 1),
  PRIMARY KEY (metric_value_id, source_document_id)
);

-- Append-only audit of value changes.
CREATE TABLE core.metric_value_audit (
  id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  metric_value_id bigint NOT NULL REFERENCES core.metric_values(id) ON DELETE CASCADE,
  changed_at      timestamptz NOT NULL DEFAULT now(),
  changed_by      text NOT NULL DEFAULT current_user,
  change_type     text NOT NULL,
  old_value       numeric,
  new_value       numeric,
  reason          text
);

-- Audit trigger: enforced no matter which language/pipeline writes the value
-- (tool-agnostic contract). Logs inserts and value-changing updates.
CREATE FUNCTION core.log_metric_value_change() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    INSERT INTO core.metric_value_audit (metric_value_id, change_type, old_value, new_value)
    VALUES (NEW.id, 'insert', NULL, NEW.value);
  ELSIF TG_OP = 'UPDATE' AND NEW.value IS DISTINCT FROM OLD.value THEN
    INSERT INTO core.metric_value_audit (metric_value_id, change_type, old_value, new_value)
    VALUES (NEW.id, 'update', OLD.value, NEW.value);
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER metric_values_audit
  AFTER INSERT OR UPDATE ON core.metric_values
  FOR EACH ROW EXECUTE FUNCTION core.log_metric_value_change();

-- migrate:down

DROP TRIGGER IF EXISTS metric_values_audit ON core.metric_values;
DROP FUNCTION IF EXISTS core.log_metric_value_change();
ALTER TABLE core.metric_values DROP CONSTRAINT IF EXISTS metric_values_crosscheck_source_fk;
DROP TABLE IF EXISTS core.metric_value_audit;
DROP TABLE IF EXISTS core.metric_value_sources;
DROP TABLE IF EXISTS core.source_documents;
