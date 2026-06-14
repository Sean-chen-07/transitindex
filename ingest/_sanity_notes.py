"""Annotate the 'review' pending rows with the sanity-check reason (reviewer_notes),
so the human reviewer sees WHY each was held back."""

import json
import sys

from transitindex_ingest.config import load_config
from transitindex_ingest.db.postgres import PostgresRepository

out = json.loads(open(sys.argv[1], encoding="utf-8").read())
results = out.get("result") if isinstance(out, dict) else out
pairs = []
for r in results or []:
    for v in r.get("verdicts", []):
        if v.get("decision") == "review":
            pairs.append((f"sanity: {str(v.get('reason',''))[:280]}", int(v["id"])))

repo = PostgresRepository(load_config().database_url)
with repo._conn.transaction():
    repo._conn.cursor().executemany(
        "UPDATE core.pending_values SET reviewer_notes=%s WHERE id=%s AND review_status='pending'",
        pairs,
    )
print(f"annotated {len(pairs)} pending rows with the sanity-check reason")
