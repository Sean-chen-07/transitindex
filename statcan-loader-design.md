# StatCan / Hamilton Bulk Loader — Architecture & Implementation Plan

**Status: PLAN ONLY — no code, DB rows, or migrations changed. Awaiting "continue".**
Date: 2026-06-05 · Branch: `feat/data-population`

This document specifies a re-architecture of the StatCan 23-10-0307 and Hamilton HSR
data loaders into one **fast (seconds, not all-night), reliable, idempotent, one-click**
command wired into the existing CLI, reusing the existing adapters, value contract, and
DB invariants. It folds the good ideas from the two throwaway root scripts
(`load_statcan.py`, `reconcile_hamilton.py`) into the tested package and deletes them.

---

## 0. Why the current loader hangs (recap, already diagnosed)

The current path (`cli.py: cmd_statcan` → `staging.stage_records` → `promotion.promote_approved`
→ a 21-metric × every-period rank loop) is correct but does **one tiny SQL statement at a
time over the internet to Supabase**, each wrapped in its own `BEGIN/COMMIT`.

Measured round-trip cost for the 703-row StatCan load (workflow agent + my read of the code):

| Phase | Round-trips | Driver |
|---|---:|---|
| Staging statements | ~3,640 | per-row pending INSERT + period SELECT/INSERT + 1 source doc |
| Staging txn overhead (`BEGIN`/`COMMIT` pairs) | ~3,570 | every method opens its own `with conn.transaction()` |
| **Duplicate period lookup** | ~3,574 | `stage_records` calls `get_or_create_reporting_period`, then `insert_pending_value` calls it **again** (periods are *not* in `_id_cache`) |
| Promotion statements | ~3,850 | per-row `get_pending_value` (redundant) + SELECT-old + UPDATE-supersede + INSERT + source INSERT + status UPDATE |
| Promotion txn overhead | ~2,650 | `promote_pending` + `update_pending` each open a transaction per row |
| Rank refresh (cmd_statcan) | thousands | **21 metrics × ~59 periods × 2 comparison sets**, each a read + DELETE + per-row INSERTs |

≈ **10,000–13,000 round-trips**. At ~25–50 ms each over the pooler that is 8–50 min on a
*good* night. The actual all-night hang had three additional root causes:

1. **No `connect_timeout` and no `statement_timeout`** in `db/postgres.py` (~lines 47-55) — when
   the **session pooler** went half-dead (socket alive, server silent) psycopg blocked forever on a
   socket read.
2. The retry logic in `load_statcan.py` **deletes everything and restarts from row 0**, so a drop
   never makes forward progress.
3. The harness **auto-backgrounds** a slow command; relaunching when output looked empty spawned
   ~5 concurrent loads that wrote duplicates.

The fix is not "tune the loop" — it is to **collapse ~12,000 round-trips into ~30** with set-based
SQL, **fail fast** instead of hanging, and make the load **idempotent + self-verifying** so a
re-run can never corrupt.

---

## 1. Target architecture at a glance

```
python -m transitindex_ingest statcan-load   (or double-click load-statcan.bat)
        │
        ▼
jobs/bulk_load.py :: bulk_load(repo, records, tier, feed_code, rank_metrics)
        │
   ┌────┴───────────────────────────────────────────────────────────────┐
   │ 1. resolve ids + periods + the single source doc  (cached, ~4 RT)   │
   │ 2. bulk-stage → core.pending_values            (multi-row, ~8 RT)   │
   │ 3. flag gate: tier-0 clean → approved, flagged → stays pending      │
   │ 4. DIFF-AWARE BULK PROMOTE of the approved set                      │
   │      set-based supersede UPDATE + multi-row INSERT + source INSERT  │
   │      (skips rows whose current value is already identical)  (~20 RT)│
   │ 5. lean bulk rank refresh: only the metrics actually touched        │
   │      one cohort SELECT + set DELETE + multi-row INSERT       (~5 RT) │
   │ 6. self-verify counts + zero one_current_value dupes, write JSON    │
   └────────────────────────────────────────────────────────────────────┘
        ▲
        │  pg_advisory_xact_lock(feed_id)  — serializes any accidental concurrent run
```

Total ≈ **30–40 round-trips ⇒ ~2–5 seconds**. StatCan and Hamilton run the **same**
`bulk_load` function; they differ only in adapter, tier, and which metrics to rank.

---

## A. Connection strategy

**Recommendation: keep the SESSION pooler (current `.env`) and add `connect_timeout` +
`statement_timeout`.** Re-evaluate the direct connection only if you later want zero pooler
dependence — but it is **not needed** once the load finishes in seconds.

### The actual fix is the timeouts, not the host

```python
# db/postgres.py — replace the psycopg.connect(...) block (~lines 47-55)
self._conn = psycopg.connect(
    dsn,
    autocommit=True,            # REQUIRED (see existing docstring) — keep
    prepare_threshold=None,     # pooler can't do server-side prepares — keep
    keepalives=1,               # keep
    keepalives_idle=30,
    keepalives_interval=10,
    keepalives_count=5,
    connect_timeout=10,                              # NEW: fail in 10s if pooler is dead
    options="-c statement_timeout=30000",            # NEW: 30s hard cap per statement
)
```

- `connect_timeout=10` — never block forever opening a socket.
- `statement_timeout=30000` (30 s) via libpq `options` is set once at connect and applies to every
  statement. With the new set-based path the slowest single statement (a ~100-row multi-row INSERT)
  is tens of ms; 30 s is generous headroom that still kills a half-dead socket fast. (For the
  delete-first `--reset` step a `DELETE … WHERE agency_id = ANY(...)` is also sub-second.)

### Pooler vs direct vs transaction pooler — trade-offs

| Option | DSN | Pros | Cons | Verdict |
|---|---|---|---|---|
| **Session pooler** (current) | `…pooler.supabase.com:5432` | Already configured; **IPv4** (works from this Windows box); fine for a short single session | Long idle sessions can be dropped — *moot once the load is seconds* | **Recommended default** |
| Direct | `db.<ref>.supabase.co:5432` | No pooler middle-man; supports server-side prepares | Supabase direct is **IPv6-only** without the paid IPv4 add-on — likely won't connect from here; new env var to manage | Optional; only if IPv4/IPv6 access is confirmed |
| Transaction pooler | `…pooler.supabase.com:6543` | Lightest; most resistant to idle drops | No session state across statements; our bulk work is one transaction so it *could* work, but adds constraints for little gain | Not needed |

The half-dead-pooler hang was caused by the **missing timeouts**, not by the pooler itself. Once
the load is a single short, fast, timeout-guarded session, the session pooler is the simplest
correct choice. *(See Open Decision #1 if you want to switch to direct anyway.)*

Project ref for reference (from `.env`): `ffrsqxwnvzjamfajzueh` → direct host would be
`db.ffrsqxwnvzjamfajzueh.supabase.co`.

---

## B. Bulk-write strategy

**Recommendation: set-based multi-row SQL with a *diff-aware* supersede.** Reject `COPY` and
single-row `executemany`.

### Why multi-row `INSERT … VALUES`, not COPY or executemany

| Mechanism | Verdict | Reason |
|---|---|---|
| **Multi-row `INSERT … VALUES (…),(…) RETURNING id`** | **Chosen** | Returns the new `metric_value` ids needed to link `metric_value_sources`; per-row audit trigger still fires; ~100 rows/statement ⇒ ~8 statements for 703 rows |
| `COPY … FROM STDIN` | Rejected | No `RETURNING` (can't get ids for the source links), append-only (can't supersede), brittle to column drift. Triggers *do* fire, but the no-RETURNING problem is fatal here |
| `executemany` (per-row) | Rejected | Still one round-trip per row (~700) even pipelined; 40× slower than batching for no benefit |
| `INSERT … ON CONFLICT DO UPDATE` | Rejected | The `one_current_value` index is **partial (`WHERE is_current`)**; an arriving row collides with the still-`is_current=true` old row *before* we can flip it, so ON CONFLICT can't express the supersede semantics cleanly |

Batch size **100 rows/statement** (well under Postgres parameter and 1 MB statement limits;
703 rows → 8 statements).

### Caching that collapses the staging round-trips

The repo already caches agency/metric/mode/feed ids in `_id_cache`. Add two more in-memory caches
for the bulk path:

- **Reporting-period ids** keyed by `(period_type, start_date, end_date)` — eliminates the
  ~3,574-round-trip duplicate-period problem. Resolve all distinct periods once (a single
  `SELECT … WHERE (period_type,start_date,end_date) IN (…)` + one multi-row INSERT for any missing).
- **The single source_document id.** All 703 StatCan rows share one `source_url`
  (`STATCAN_307_URL`) and `document_type='statcan_table'`, so there is exactly **one**
  source document — resolve it once and reuse.

### The diff-aware supersede (the heart of the fast path)

For the **approved** subset, run this inside **one** transaction:

```sql
BEGIN;

-- (0) advisory lock so a second invocation of this feed waits, never double-writes
SELECT pg_advisory_xact_lock( <feed_id> );

-- (1) ONE read of the current cohort for the touched agencies+metrics
SELECT id, agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, quality
FROM   core.metric_values
WHERE  is_current
  AND  agency_id = ANY(%(aids)s)
  AND  metric_id = ANY(%(mids)s);
--   → classify each incoming row in Python against this map:
--       absent           → INSERT (restatement_of_id = NULL)
--       present, differs  → SUPERSEDE old + INSERT (restatement_of_id = old.id)
--       present, identical→ SKIP            (true idempotency: re-run = no-op)
--     "differs" = value OR quality changed (StatCan flips 'preliminary'→'verified')

-- (2) set-based supersede of just the rows that changed
UPDATE core.metric_values
SET is_current = false, updated_at = now()
WHERE id = ANY(%(changed_old_ids)s);          -- 1 statement, no audit row (value unchanged)

-- (3) multi-row INSERT of new + changed current rows, batched ~100/stmt
INSERT INTO core.metric_values
  (agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, unit,
   currency, quality, comparable_flag, crosscheck_value, restatement_of_id, is_current, notes)
VALUES (...),(...),...                          -- audit trigger fires per row (change_type='insert')
RETURNING id, agency_id, metric_id, reporting_period_id, mode_id, service_scope;

-- (4) multi-row INSERT of provenance links, keyed off the RETURNING ids
INSERT INTO core.metric_value_sources
  (metric_value_id, source_document_id, page_number, table_reference, extraction_method, confidence)
VALUES (...),(...),...
ON CONFLICT (metric_value_id, source_document_id) DO NOTHING;

COMMIT;
```

**Round-trip count for 703 rows:** 1 cohort read + 1 supersede + ~8 inserts + ~8 source inserts
+ a few setup = **≈ 20**, plus ~10 for periods/source/ranks/feed-run = **≈ 30 total**.

### Do we still go through `pending_values`? — Yes, and here is why

The bulk-write workflow agent proposed skipping `pending_values` entirely for trusted feeds. **That
is unsafe** and I do not recommend it: tier-0 rows can still receive validation **flags**
(`staging.py:81` — `if tier == 0 and not flags: approved else pending`), and a flagged value must
**not** auto-reach `metric_values` (the "an unreviewed value never reaches metric_values"
invariant). So the bulk path must keep the flag gate:

1. **Bulk-stage** every record into `pending_values` (cheap once batched — multi-row INSERT).
2. Compute flags in Python; tier-0 clean → `approved`, flagged → stays `pending` for review.
3. **Diff-aware bulk-promote only the `approved` subset** (the SQL above).

This keeps staging as "the only door inward," preserves provenance capture, keeps the
`InMemoryRepository` parity the test suite relies on, and still hits ~30 round-trips.

---

## C. Idempotency & resumability

### Natural key

From the `one_current_value` partial unique index (migration 003):

```
(agency_id, metric_id, reporting_period_id, mode_id, service_scope)   WHERE is_current
                                            -- NULLS NOT DISTINCT, so mode_id=NULL collides
```

That tuple **is** the natural key for "the current value." For StatCan/Hamilton, `mode_id` is
always `NULL` and `service_scope` is always `'total'`.

### Convergence model (better than both delete-first and naive supersede)

| Strategy | Re-run behavior | History | Verdict |
|---|---|---|---|
| Delete-first (throwaway scripts) | Wipes feed's rows, re-inserts all → **churns audit** (cascade-deletes old audit), loses restatement chain | Lost on every run | `--reset` only |
| Naive supersede (always insert) | Re-inserts identical rows as new restatements → **table + audit bloat** | Preserved but noisy | No |
| **Diff-aware supersede (chosen)** | Identical rows **skipped**; only genuine changes supersede | Preserved, clean | **Recommended** |

With diff-aware supersede, **re-running the same CSV is a true no-op** (0 inserts, 0 audit rows),
and a CSV with a few revised months supersedes exactly those, keeping the `restatement_of_id`
revision chain. A mid-run drop is safe because the whole promote is **one transaction** — it either
commits or rolls back; the next run simply re-converges. No "restart from row 0" logic needed.

### No-double-write guarantee

- **Single transaction** for the promote ⇒ atomic; a crash leaves the DB untouched.
- **`pg_advisory_xact_lock(feed_id)`** at the top of the transaction ⇒ a second concurrent
  invocation of the same feed **blocks** until the first finishes, then re-converges (no-op). This
  is the structural defense against the "harness backgrounded it, I relaunched, 5 ran at once"
  failure.
- **Self-verify** at the end (counts == expected, zero dupes) ⇒ the loader reports failure rather
  than silently leaving a mess.

The orphan cleanup needed for current live state (12 StatCan agencies = 0 values + 1 orphan pending
row) is handled by the loader's normal stage/promote plus a one-time `--reset` of the stale pending
row — see implementation step 1.

---

## D. Invariant preservation (the critical part)

How the bulk path upholds each DB invariant. (Schema facts verified against migrations 003/004/005/009.)

### D1. `one_current_value` unique index (partial, `WHERE is_current`, `NULLS NOT DISTINCT`)
The index only constrains `is_current=true` rows. The supersede `UPDATE … SET is_current=false`
runs **before** the `INSERT`, so at no point are there two `is_current=true` rows for a tuple. Both
operations are in the same transaction, so the index is never transiently violated as seen by other
sessions.

### D2. `metric_values_audit` trigger (`AFTER INSERT OR UPDATE … FOR EACH ROW`)
- Fires **per row** even for a multi-row `INSERT` → every new current value logs
  `change_type='insert'` automatically. No application code needed.
- The supersede `UPDATE` sets `is_current=false` but **does not change `value`**, and the trigger
  body only logs an UPDATE when `NEW.value IS DISTINCT FROM OLD.value` → **no spurious audit rows**
  from supersede.
- The trigger does **not** fire on `DELETE` (only relevant to the `--reset` path; the cascade still
  removes orphaned audit rows).

### D3. `metric_value_sources` provenance linkage
PK `(metric_value_id, source_document_id)`, both FKs `ON DELETE CASCADE`. We capture the
`RETURNING id` from the value INSERT, then bulk-INSERT the links with
`ON CONFLICT … DO NOTHING` (safe under re-run). Provenance fields
(`page_number, table_reference, extraction_method, confidence`) come from the pending row, exactly
as `promote_pending` does today.

### D4. `restatement_of_id` / supersede chain
For a **changed** row we set `restatement_of_id = <old current id>` on the new row; for a brand-new
row it is `NULL`. This reproduces `_insert_value_locked`'s behavior set-based. Skipped (identical)
rows leave the existing chain intact.

### D5. Parity with `InMemoryRepository`
The offline fake mirrors all of the above via `_write_metric_value` (`_current_index` map, audit
list, `_value_sources`, `restatement_of_id`). The new bulk method's **InMemory implementation loops
`_write_metric_value` per row** (no network, so per-row is free) while the **Postgres
implementation is set-based** — both produce byte-identical observable state, which the parity tests
assert (Section G).

---

## E. Derived metrics & ranks — touch only what changed

### Derived: a genuine no-op for these feeds
`derived_recompute` computes 6 ratios, each needing an **annual** input
(`annual_ridership` / `operating_expenses` / `revenue_service_hours`). StatCan provides only
`monthly_ridership` + `operating_revenue`; Hamilton only `monthly_ridership`. So `compute_derived`
returns `{}` for every (agency, period). **The bulk loader skips the derived step entirely** for
StatCan and Hamilton (the current `cmd_statcan` runs it as ~468 no-op round-trips).

### Ranks: lean + bulk
The current `cmd_statcan` refreshes **all 21 metrics × every period × 2 comparison sets** — thousands
of round-trips, almost all empty cohorts. Replace with a **bulk rank refresh** scoped to the metrics
the feed actually wrote:

- StatCan → `monthly_ridership`, `operating_revenue` (scope `total`)
- Hamilton → `monthly_ridership` (scope `total`)

New job `jobs/rank_refresh.py :: bulk_refresh_ranks(repo, metric_codes, period_ids, service_scope)`:

1. **One** `SELECT … WHERE is_current AND metric_id = ANY(%s) AND reporting_period_id = ANY(%s) AND comparable_flag` to pull every touched cohort. (1 RT)
2. Compute ranks in Python (reuse `compute_ranks` + the subdivision grouping), grouped by
   `(metric, period)` and by subdivision. (0 RT)
3. **Set-based** `DELETE FROM core.metric_ranks WHERE metric_id = ANY(%s) AND reporting_period_id = ANY(%s)` for both comparison sets. (1 RT)
4. **Multi-row INSERT** of all computed rank rows. (~2 RT)

`metric_ranks` has **no** unique constraint, so DELETE-then-insert (not upsert) is correct — this is
just the existing `replace_metric_ranks` made set-based. ~5 round-trips instead of thousands.

---

## F. File-by-file change list

### New files
| File | Purpose |
|---|---|
| `ingest/transitindex_ingest/jobs/bulk_load.py` | Shared `bulk_load(repo, records, *, tier, feed_code, rank_metrics, reset=False)` + thin `load_statcan(repo, csv)` / `load_hamilton(repo, csv)` wrappers; returns a `BulkLoadResult` (counts, dupes, ok, steps, seconds) |
| `ingest/tests/test_bulk_load.py` | Offline `InMemoryRepository` tests (Section G) |
| `ingest/tests/test_bulk_load_postgres.py` | Real-DB smoke, skipped unless `TEST_DATABASE_URL` set |
| `load-statcan.bat` (repo root) | Double-click wrapper → `python -m transitindex_ingest statcan-load --csv statcan_23100307.csv` |
| `load-hamilton.bat` (repo root) | Double-click wrapper → `python -m transitindex_ingest hamilton-load --csv hamilton_hsr_live.csv` |

### Modified files
| File | Change |
|---|---|
| `db/postgres.py` | (1) add `connect_timeout` + `statement_timeout` (Section A). (2) add period-id + source-doc caches. (3) add the set-based bulk method `apply_current_values(rows) -> BulkWriteSummary` implementing diff-aware supersede + multi-row INSERT + source links + advisory lock. (4) add `bulk_refresh_ranks` write helper or set-based `replace_metric_ranks_bulk`. |
| `db/memory.py` | Implement the same `apply_current_values` (loop `_write_metric_value`) and the bulk rank helper, for parity. |
| `db/repository.py` | Add the new method(s) to the `Repository` Protocol. |
| `jobs/rank_refresh.py` | Add `bulk_refresh_ranks(repo, metric_codes, period_ids, service_scope)`; keep existing `refresh_ranks` for the `ranks` CLI command. |
| `staging.py` | Add a `bulk_stage_records` path (multi-row pending INSERT + batched period/source resolution); keep `stage_records` for PDF/tier-2. *(Or: have `bulk_load` call a new staging helper; `stage_records` itself can stay untouched if we prefer minimal change.)* |
| `cli.py` | Add `statcan-load` and `hamilton-load` subcommands (`set_defaults(func=cmd_statcan_load / cmd_hamilton_load)`) that call `jobs.bulk_load`. Leave the old `statcan` / `hamilton` commands in place initially (or repoint them) — decide via Open Decision #3. |

### Deleted files (after the new path is verified)
| File | Reason |
|---|---|
| `load_statcan.py` (root) | Logic folded into `jobs/bulk_load.py` |
| `reconcile_hamilton.py` (root) | Logic folded into `jobs/bulk_load.py` |
| `reconcile_result.json` (root) | Throwaway output |

### Migration?
**None required.** Every invariant the bulk path relies on (partial unique index, audit trigger,
cascades, shared periods) already exists. *Optional, not recommended now:* a `UNIQUE … WHERE
is_current` could enable `ON CONFLICT`, but the chosen supersede approach doesn't need it.

---

## G. Test plan

### Offline (`InMemoryRepository`, no network) — the bulk of coverage
`ingest/tests/test_bulk_load.py`:
1. **Fresh load** — N records, no prior current rows → N current values, N audit `insert` rows,
   N source links, zero dupes.
2. **Idempotent re-run** — run the same records twice → second run inserts **0** new values and
   **0** new audit rows (diff-aware skip). *This is the key regression test for the
   concurrent-corruption bug class.*
3. **Diff supersede** — re-run with one record's `value` changed → exactly one supersede: old
   `is_current=false`, new `is_current=true`, `restatement_of_id` set, one new audit row.
4. **Flag gate** — a tier-0 record carrying a validation flag stays `pending` and never reaches
   `metric_values`; tier-2 never auto-promotes.
5. **`mode_id=None` participates in the key** — system-wide and per-mode rows coexist (guards the
   `NULLS NOT DISTINCT` semantics).
6. **Lean ranks** — only the touched metrics get rank rows; cohorts rank correctly (ties, direction).
7. **Postgres/InMemory parity** — drive both backends (InMemory always; Postgres if
   `TEST_DATABASE_URL`) through the same records and assert identical observable state
   (current values, audit count, source links).

Extend `test_staging_promotion.py` / `test_memory_repo.py` with a bulk-promote supersede case.

### Real-DB smoke (`ingest/tests/test_bulk_load_postgres.py`, skipped unless `TEST_DATABASE_URL`)
- Load all **703** StatCan records → assert `current count == parsed count` for the 12 agencies,
  **zero** `one_current_value` dupes, and one `metric_value_sources` link per value.
- Assert wall-clock **< ~10 s**.
- Re-run → assert **0** new values (idempotency on the real DB).
- Clean up via `DELETE … WHERE agency_id = ANY(...)`.

Baseline today: `cd ingest; python -m pytest` = 152 pass, 2 skip. New tests must keep that green.

---

## H. One-click / automation vision

**Goal:** the user double-clicks a file and the data loads in seconds with no per-command
permission prompts and no chance of the concurrent-corruption failure.

- **Entry point:** `python -m transitindex_ingest statcan-load` (and `hamilton-load`). Same fast
  `bulk_load` path for both feeds.
- **Double-click wrapper:** `load-statcan.bat` at repo root:
  ```bat
  @echo off
  cd /d "%~dp0"
  python -m transitindex_ingest statcan-load --csv statcan_23100307.csv --result load_statcan_result.json
  pause
  ```
  The user runs this in their own shell — **outside the agent harness** — so there are no
  permission prompts and no auto-backgrounding. `pause` keeps the window open to read the result.
- **Safe by construction:** finishes in seconds (won't background), single invocation, idempotent
  (diff-aware), advisory-locked (concurrent runs serialize), and self-verifying (writes
  `load_statcan_result.json` with `ok`, counts, dupes, seconds). Re-running is always safe.
- **Optional later:** a Windows Scheduled Task running the same `.bat` monthly after StatCan
  publishes (the CSV download via `curl.exe` of `…/23100307-eng.zip` can be a first step in the
  `.bat`). Not in scope for the first build.
- **Refresh-the-CSV step (optional):** the `.bat` can `curl.exe -L -o statcan_23100307.zip <url>` then
  unzip before the load (httpx/WebFetch get TLS-reset locally; `curl` works).

---

## I. Open decisions (need your call before building)

1. **Connection host.** Recommend **keep the session pooler + add timeouts** (simplest, IPv4,
   sufficient once fast). Switch to the **direct** connection only if you specifically want zero
   pooler dependence *and* confirm IPv4/IPv6 reachability. → *My pick: session pooler.*
2. **Diff-aware vs delete-first as the default.** Recommend **diff-aware supersede** (clean
   idempotency, preserves audit + restatement history), with a `--reset` flag that does the
   delete-first wipe for the one-time orphan cleanup. → *My pick: diff-aware default, `--reset`
   available.*
3. **Old `statcan` / `hamilton` CLI commands.** Either (a) leave them and add new
   `statcan-load` / `hamilton-load`, or (b) repoint the old names to the fast path and drop the slow
   bodies. → *My pick: (b) repoint — one fast path, less confusion — but (a) is safer if you want to
   compare outputs first.*
4. **Quality-change handling.** Treat a `preliminary → verified` change (same value) as a
   supersede? Recommend **yes** (so finalized StatCan months update), comparing on `(value, quality)`.
   → *My pick: yes.*
5. **Advisory lock.** Add `pg_advisory_xact_lock(feed_id)` as the concurrency guard? Recommend
   **yes** (cheap, structurally prevents the double-load mess). → *My pick: yes.*
6. **First write target.** Confirm the first real run should target the live Supabase DB and that
   Hamilton's existing 144 current values stay untouched (the loader only deletes/supersedes the
   feed it is loading). → *Assumed yes.*

---

## Appendix — key facts the design rests on (verified this session)

- `one_current_value`: `UNIQUE (agency_id, metric_id, reporting_period_id, mode_id, service_scope) NULLS NOT DISTINCT WHERE is_current` (003).
- Audit trigger: `AFTER INSERT OR UPDATE … FOR EACH ROW`; logs INSERTs and **value-changing** UPDATEs only; not DELETE (004).
- `metric_value_sources` PK `(metric_value_id, source_document_id)`, both FKs `ON DELETE CASCADE` (004). `metric_value_audit.metric_value_id` `ON DELETE CASCADE` (004).
- `reporting_periods` shared across agencies; identity `(period_type, start_date, end_date)` (009).
- `metric_ranks` has **no** unique constraint → replace = DELETE+INSERT (005).
- StatCan adapter emits `monthly_ridership` + `operating_revenue`, `service_scope='total'`,
  `mode_code=None`, one shared `SourceRef` (`statcan_table` / `statcan_passthrough` / `statcan_open`,
  `confidence=1.0`) → exactly one `source_document` for the whole load.
- 12 StatCan agencies in `STATCAN_AGENCY_MAP`; CSV has 703 records, Jan 2023–Mar 2026.
- `.env` `DATABASE_URL` → session pooler `aws-1-us-east-1.pooler.supabase.com:5432`; project ref `ffrsqxwnvzjamfajzueh`.
- `config.load_config()` reads `.env`; `cli._build_repo()` → `PostgresRepository` when
  `DATABASE_URL` set, else `InMemoryRepository` (dry run).
- Test baseline: `cd ingest; python -m pytest` = 152 pass, 2 skip; `InMemoryRepository` mirrors all invariants.
