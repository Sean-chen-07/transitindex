"""Build per-agency context for an LLM sanity check of the remaining pending values.

For each agency that still has pending (low-confidence) PDF values, write
_sanity/<agency>.json with:
  - live:    the agency's trusted current values (metric x year) as a baseline
  - pending: the low-confidence values to judge (with pending_id)
A subagent compares each pending value against the live baseline + sibling years and
decides approve / review. Also writes _sanity/agencies.json (the work list).
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from transitindex_ingest.config import load_config
from transitindex_ingest.db.postgres import PostgresRepository
from transitindex_ingest.refdata import AGENCIES

OUT = Path(__file__).resolve().parent / "_sanity"
repo = PostgresRepository(load_config().database_url)
c = repo._conn
slug_by_id = {}
for s in AGENCIES:
    try:
        slug_by_id[repo.agency_id(s)] = s
    except ValueError:
        pass

# pending (low-confidence) PDF values to judge
pending = c.execute("""
    SELECT pv.id, pv.agency_id, m.code, rp.label, EXTRACT(YEAR FROM rp.end_date)::int,
           pv.value, pv.unit, pv.service_scope, pv.confidence, pv.flags, pv.page_number
    FROM core.pending_values pv
    JOIN core.metrics m ON m.id = pv.metric_id
    JOIN core.reporting_periods rp ON rp.id = pv.reporting_period_id
    WHERE pv.review_status='pending' AND pv.extraction_method='llm_assisted'
    ORDER BY pv.agency_id, m.code, rp.end_date
""").fetchall()

# trusted current values (baseline)
live = c.execute("""
    SELECT mv.agency_id, m.code, rp.label, EXTRACT(YEAR FROM rp.end_date)::int, mv.value, mv.unit, mv.service_scope
    FROM core.metric_values mv
    JOIN core.metrics m ON m.id = mv.metric_id
    JOIN core.reporting_periods rp ON rp.id = mv.reporting_period_id
    WHERE mv.is_current
    ORDER BY mv.agency_id, m.code, rp.end_date
""").fetchall()

by_agency = {}
for row in pending:
    pid, aid, code, label, yr, val, unit, scope, conf, flags, page = row
    slug = slug_by_id.get(aid, f"agency#{aid}")
    d = by_agency.setdefault(slug, {"agency": slug, "live": [], "pending": []})
    d["pending"].append({
        "id": int(pid), "metric": code, "period": label, "year": yr,
        "value": str(val), "unit": unit, "scope": scope,
        "confidence": str(conf) if conf is not None else None,
        "flags": list(flags) if flags else [], "page": page,
    })

for row in live:
    aid, code, label, yr, val, unit, scope = row
    slug = slug_by_id.get(aid)
    if slug in by_agency:  # only agencies that have pending work
        by_agency[slug]["live"].append({
            "metric": code, "period": label, "year": yr, "value": str(val),
            "unit": unit, "scope": scope,
        })

OUT.mkdir(exist_ok=True)
agencies = sorted(by_agency)
for slug in agencies:
    (OUT / f"{slug}.json").write_text(json.dumps(by_agency[slug], indent=2), encoding="utf-8")
    print(f"  {slug:20} pending={len(by_agency[slug]['pending']):>4}  live_baseline={len(by_agency[slug]['live'])}")
(OUT / "agencies.json").write_text(json.dumps(agencies), encoding="utf-8")
print(f"\n{sum(len(v['pending']) for v in by_agency.values())} pending across {len(agencies)} agencies -> _sanity/")
