"""One-time bulk promote: approve every pending PDF value with confidence >= 0.80.

Resilient to the Supabase pooler dropping the connection mid-run: on an
OperationalError it rebuilds the repo and retries the same row. Resumable -- it
only looks at rows still 'pending', and skips any already stamped 'promoted', so
re-running continues where it left off without double-promoting.
"""

import sys
import time
from decimal import Decimal

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from psycopg import OperationalError

from transitindex_ingest.config import load_config
from transitindex_ingest.db.postgres import PostgresRepository
from transitindex_ingest.promotion import _PROMOTED_NOTE, promote_one

MIN_CONF = Decimal("0.80")
DSN = load_config().database_url


def make_repo():
    return PostgresRepository(DSN)


repo = make_repo()

# Reset any row left 'approved' but not 'promoted' by the earlier failed run.
with repo._conn.transaction():
    reset = repo._conn.execute(
        "UPDATE core.pending_values SET review_status='pending', reviewer_notes=NULL, updated_at=now() "
        "WHERE review_status='approved' AND extraction_method='llm_assisted' "
        "AND reviewer_notes IS DISTINCT FROM %s",
        (_PROMOTED_NOTE,),
    ).rowcount
print(f"reset {reset} half-approved row(s) back to pending", flush=True)

rows = repo._conn.execute(
    "SELECT id, confidence FROM core.pending_values "
    "WHERE review_status='pending' AND extraction_method='llm_assisted' ORDER BY id"
).fetchall()
qualify = [pid for pid, conf in rows if conf is not None and conf >= MIN_CONF]
below = len(rows) - len(qualify)
print(f"still pending: {len(rows)} | qualify (>= {MIN_CONF}): {len(qualify)} | below/none: {below}", flush=True)

promoted = 0
errors = []
for pid in qualify:
    for attempt in range(5):
        try:
            p = repo.get_pending_value(pid)
            if p is None or p.reviewer_notes == _PROMOTED_NOTE:
                break  # already handled
            repo.update_pending(pid, review_status="approved")
            promote_one(repo, pid)
            promoted += 1
            if promoted % 50 == 0:
                print(f"  ...promoted {promoted}/{len(qualify)}", flush=True)
            break
        except OperationalError:
            try:
                repo._conn.close()
            except Exception:
                pass
            time.sleep(1.5)
            repo = make_repo()  # reconnect, retry same pid
        except Exception as exc:
            errors.append((pid, f"{type(exc).__name__}: {exc}"))
            break
    else:
        errors.append((pid, "gave up after 5 reconnect attempts"))

print(f"DONE: promoted={promoted}  errors={len(errors)}", flush=True)
for pid, e in errors[:15]:
    print(f"  ERR pid={pid}: {e}", flush=True)

try:
    live = repo._conn.execute("SELECT COUNT(*) FROM core.metric_values WHERE is_current").fetchone()[0]
    live_pdf = repo._conn.execute(
        "SELECT COUNT(*) FROM core.metric_value_sources WHERE extraction_method='llm_assisted'"
    ).fetchone()[0]
    pend = repo._conn.execute("SELECT COUNT(*) FROM core.pending_values WHERE review_status='pending'").fetchone()[0]
    print(f"current live values: {live} | PDF-sourced links: {live_pdf} | still pending: {pend}", flush=True)
except OperationalError:
    print("(final counts unavailable -- connection dropped; re-run to verify)", flush=True)
