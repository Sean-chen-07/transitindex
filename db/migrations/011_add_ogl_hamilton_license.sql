-- migrate:up

-- Migration 011: add ogl_hamilton to source_documents.license CHECK constraint.
-- Hamilton Street Railway data is published under the Open Government Licence –
-- City of Hamilton (https://www.hamilton.ca/city-initiatives/strategies-actions/open-data).

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

-- migrate:down

ALTER TABLE core.source_documents
  DROP CONSTRAINT IF EXISTS source_documents_license_check;

ALTER TABLE core.source_documents
  ADD CONSTRAINT source_documents_license_check CHECK (license IN (
    'statcan_open',
    'ogl_toronto', 'ogl_ottawa', 'ogl_calgary', 'ogl_edmonton',
    'ogl_montreal', 'ogl_metrovancouver', 'ogl_mississauga',
    'public_document'
  ));
