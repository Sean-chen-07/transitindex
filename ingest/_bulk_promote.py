"""Fast one-time bulk promote of pending PDF values with confidence >= 0.80.

Set-based, single transaction (no per-row round-trips):
  1. promote_set = one pending row per (agency, metric, period, mode, scope) -- the
     same figure repeats across annual reports, so dedup to the highest-confidence
     one, and only for keys that have NO current value yet (fill gaps; never clobber
     existing StatCan/hand-entered data).
  2. bulk INSERT those into core.metric_values (is_current).
  3. bulk INSERT their core.metric_value_sources provenance links.
  4. stamp EVERY qualifying pending row approved+'promoted' (clears the queue and
     blocks any re-promote); rows < 0.80 stay 'pending'.
Atomic: if anything fails the whole thing rolls back.
"""

import sys
from transitindex_ingest.config import load_config
from transitindex_ingest.db.postgres import PostgresRepository
from transitindex_ingest.promotion import _PROMOTED_NOTE

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

repo = PostgresRepository(load_config().database_url)
c = repo._conn

KEY = "pv.agency_id, pv.metric_id, pv.reporting_period_id, pv.mode_id, pv.service_scope"
QUALIFY = (
    "review_status='pending' AND extraction_method='llm_assisted' AND confidence >= 0.80"
)

before_live = c.execute("SELECT COUNT(*) FROM core.metric_values WHERE is_current").fetchone()[0]
qual_n = c.execute(f"SELECT COUNT(*) FROM core.pending_values pv WHERE {QUALIFY.replace('review_status','pv.review_status').replace('extraction_method','pv.extraction_method').replace('confidence','pv.confidence')}").fetchone()[0]

with c.transaction():
    c.execute("DROP TABLE IF EXISTS promote_set")
    c.execute(f"""
        CREATE TEMP TABLE promote_set AS
        SELECT DISTINCT ON ({KEY})
               pv.id, pv.agency_id, pv.metric_id, pv.reporting_period_id, pv.mode_id,
               pv.service_scope, pv.value, pv.unit, pv.currency, pv.quality,
               pv.comparable_flag, pv.crosscheck_value, pv.source_document_id,
               pv.page_number, pv.table_reference, pv.extraction_method, pv.confidence
        FROM core.pending_values pv
        WHERE pv.review_status='pending' AND pv.extraction_method='llm_assisted'
          AND pv.confidence >= 0.80
          AND NOT EXISTS (
            SELECT 1 FROM core.metric_values mv
            WHERE mv.is_current AND mv.agency_id=pv.agency_id AND mv.metric_id=pv.metric_id
              AND mv.reporting_period_id=pv.reporting_period_id
              AND mv.mode_id IS NOT DISTINCT FROM pv.mode_id
              AND mv.service_scope=pv.service_scope)
        ORDER BY {KEY}, pv.confidence DESC, pv.id DESC
    """)
    inserted_keys = c.execute("SELECT COUNT(*) FROM promote_set").fetchone()[0]

    c.execute("""
        INSERT INTO core.metric_values
          (agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, unit,
           currency, quality, comparable_flag, crosscheck_value, restatement_of_id, is_current, notes)
        SELECT agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, unit,
               currency, quality, comparable_flag, crosscheck_value, NULL, true, NULL
        FROM promote_set
    """)

    src = c.execute("""
        INSERT INTO core.metric_value_sources
          (metric_value_id, source_document_id, page_number, table_reference, extraction_method, confidence)
        SELECT mv.id, ps.source_document_id, ps.page_number, ps.table_reference, ps.extraction_method, ps.confidence
        FROM promote_set ps
        JOIN core.metric_values mv
          ON mv.is_current AND mv.agency_id=ps.agency_id AND mv.metric_id=ps.metric_id
         AND mv.reporting_period_id=ps.reporting_period_id
         AND mv.mode_id IS NOT DISTINCT FROM ps.mode_id AND mv.service_scope=ps.service_scope
         AND mv.value=ps.value
        WHERE ps.source_document_id IS NOT NULL
    """).rowcount

    stamped = c.execute(
        "UPDATE core.pending_values SET review_status='approved', reviewer_notes=%s, updated_at=now() "
        "WHERE review_status='pending' AND extraction_method='llm_assisted' AND confidence >= 0.80",
        (_PROMOTED_NOTE,),
    ).rowcount

after_live = c.execute("SELECT COUNT(*) FROM core.metric_values WHERE is_current").fetchone()[0]
pend = c.execute("SELECT COUNT(*) FROM core.pending_values WHERE review_status='pending'").fetchone()[0]

print(f"qualifying (conf>=0.80): {qual_n}", flush=True)
print(f"new live values inserted: {inserted_keys}  (provenance links: {src})", flush=True)
print(f"duplicates/already-present collapsed: {stamped - inserted_keys}", flush=True)
print(f"pending rows cleared (approved): {stamped}", flush=True)
print(f"current live values: {before_live} -> {after_live}", flush=True)
print(f"still pending (conf<0.80, left for review): {pend}", flush=True)
