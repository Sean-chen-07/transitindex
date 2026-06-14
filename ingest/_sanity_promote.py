"""Promote the pending values the sanity-check workflow marked 'approve'.

Reads the workflow output (verdicts per agency), collects the 'approve' pending ids,
and promotes them with the same fast set-based, fill-gaps, dedup transaction as
_bulk_promote.py -- restricted to those ids. 'review' ids are left pending.
"""

import json
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from transitindex_ingest.config import load_config
from transitindex_ingest.db.postgres import PostgresRepository
from transitindex_ingest.promotion import _PROMOTED_NOTE

out = json.loads(open(sys.argv[1], encoding="utf-8").read())
results = out.get("result") if isinstance(out, dict) else out

approve, review = [], []
for r in results or []:
    for v in r.get("verdicts", []):
        (approve if v.get("decision") == "approve" else review).append(int(v["id"]))
print(f"verdicts: approve={len(approve)}  review={len(review)}", flush=True)
if not approve:
    print("nothing to promote", flush=True)
    sys.exit(0)

repo = PostgresRepository(load_config().database_url)
c = repo._conn
KEY = "pv.agency_id, pv.metric_id, pv.reporting_period_id, pv.mode_id, pv.service_scope"

before = c.execute("SELECT COUNT(*) FROM core.metric_values WHERE is_current").fetchone()[0]
with c.transaction():
    c.execute("DROP TABLE IF EXISTS sset")
    c.execute(f"""
        CREATE TEMP TABLE sset AS
        SELECT DISTINCT ON ({KEY})
               pv.id, pv.agency_id, pv.metric_id, pv.reporting_period_id, pv.mode_id,
               pv.service_scope, pv.value, pv.unit, pv.currency, pv.quality,
               pv.comparable_flag, pv.crosscheck_value, pv.source_document_id,
               pv.page_number, pv.table_reference, pv.extraction_method, pv.confidence
        FROM core.pending_values pv
        WHERE pv.id = ANY(%s) AND pv.review_status='pending'
          AND NOT EXISTS (
            SELECT 1 FROM core.metric_values mv
            WHERE mv.is_current AND mv.agency_id=pv.agency_id AND mv.metric_id=pv.metric_id
              AND mv.reporting_period_id=pv.reporting_period_id
              AND mv.mode_id IS NOT DISTINCT FROM pv.mode_id
              AND mv.service_scope=pv.service_scope)
        ORDER BY {KEY}, pv.confidence DESC, pv.id DESC
    """, (approve,))
    inserted = c.execute("SELECT COUNT(*) FROM sset").fetchone()[0]
    c.execute("""
        INSERT INTO core.metric_values
          (agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, unit,
           currency, quality, comparable_flag, crosscheck_value, restatement_of_id, is_current, notes)
        SELECT agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, unit,
               currency, quality, comparable_flag, crosscheck_value, NULL, true, NULL
        FROM sset
    """)
    src = c.execute("""
        INSERT INTO core.metric_value_sources
          (metric_value_id, source_document_id, page_number, table_reference, extraction_method, confidence)
        SELECT mv.id, ps.source_document_id, ps.page_number, ps.table_reference, ps.extraction_method, ps.confidence
        FROM sset ps
        JOIN core.metric_values mv
          ON mv.is_current AND mv.agency_id=ps.agency_id AND mv.metric_id=ps.metric_id
         AND mv.reporting_period_id=ps.reporting_period_id
         AND mv.mode_id IS NOT DISTINCT FROM ps.mode_id AND mv.service_scope=ps.service_scope
         AND mv.value=ps.value
        WHERE ps.source_document_id IS NOT NULL
    """).rowcount
    stamped = c.execute(
        "UPDATE core.pending_values SET review_status='approved', reviewer_notes=%s, updated_at=now() "
        "WHERE id = ANY(%s) AND review_status='pending'",
        (_PROMOTED_NOTE, approve),
    ).rowcount

after = c.execute("SELECT COUNT(*) FROM core.metric_values WHERE is_current").fetchone()[0]
pend = c.execute("SELECT COUNT(*) FROM core.pending_values WHERE review_status='pending'").fetchone()[0]
print(f"approved+stamped: {stamped}  | new live values: {inserted} (links {src}) | dedup/collapsed: {stamped - inserted}", flush=True)
print(f"current live: {before} -> {after}", flush=True)
print(f"still pending (left for your manual review): {pend}", flush=True)
