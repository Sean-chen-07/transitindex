"""Read-only: is Metrolinx operating_revenue on a consistent boundary across years?

744-style = "Revenue" (fares + non-fare operating); 770-style = "Total Revenue"
(incl. third-party construction, intercompany, One Fare). We want to see whether
live + pending values are all on the SAME boundary or mixed.
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from transitindex_ingest.config import load_config
from transitindex_ingest.db.postgres import PostgresRepository

repo = PostgresRepository(load_config().database_url)
c = repo._conn
aid = repo.agency_id("metrolinx")

print("=== LIVE operating_revenue (metric_values) ===")
live = c.execute(
    """
    SELECT rp.label, EXTRACT(YEAR FROM rp.end_date)::int, mv.value, mv.service_scope
    FROM core.metric_values mv
    JOIN core.metrics m ON m.id = mv.metric_id
    JOIN core.reporting_periods rp ON rp.id = mv.reporting_period_id
    WHERE mv.agency_id = %s AND m.code = 'operating_revenue' AND mv.is_current
    ORDER BY rp.end_date
    """,
    (aid,),
).fetchall()
for r in live:
    print(f"  {r[0]:12} {int(r[2]):>14,}  scope={r[3]}")

print("\n=== PENDING operating_revenue (pending_values) with source doc ===")
pend = c.execute(
    """
    SELECT rp.label, EXTRACT(YEAR FROM rp.end_date)::int, pv.value, pv.confidence,
           pv.page_number, pv.flags, sd.title
    FROM core.pending_values pv
    JOIN core.metrics m ON m.id = pv.metric_id
    JOIN core.reporting_periods rp ON rp.id = pv.reporting_period_id
    LEFT JOIN core.source_documents sd ON sd.id = pv.source_document_id
    WHERE pv.agency_id = %s AND m.code = 'operating_revenue'
    ORDER BY rp.end_date, pv.value
    """,
    (aid,),
).fetchall()
for r in pend:
    print(f"  {r[0]:12} {int(r[2]):>14,}  conf={r[3]} page={r[4]} flags={r[5]} src={r[6]}")
