# Spec: Lane 0 — Schema Foundation & Repo Scaffold
**Status:** Ready to build (Phase 1 plan approved for this slice) | **Authored:** 2026-05-30 via `/spec`
**Scope:** The blocking foundation only. Ends with a runnable, tested, seeded Postgres 16 database that both build lanes depend on. No application code in this spec.

> This is the bridge from the locked design ([phase-plan.md](phase-plan.md), [data-model.md](data-model.md), [schema-design.md](schema-design.md)) to an executable build. Table definitions are authoritative in [schema-design.md](schema-design.md); this spec adds the build-specific layer (file breakdown, tooling, seed contents, tests, acceptance criteria) and records the deltas decided in the 2026-05-30 spec session.

---

## Decisions baked into this spec (2026-05-30)
| Decision | Choice |
|---|---|
| Spec scope | Lane 0 foundation only (schema + scaffold + seed + tests) |
| Migration tool | **dbmate** — plain-SQL up/down files, language-agnostic |
| Database host | **Supabase** (Postgres 16), dev + prod |
| ORM | **Deferred** to the `web/` and `ingest/` specs (Lane 0 is pure SQL) |
| `typology` | **Removed** — modes + `service_area_population` carry agency scale; no category tag |
| TransLink SkyTrain | mapped to **`subway`** (grade-separated rapid transit), not `light_rail` |
| Metric catalog | **Full financial-statement set, 20 metrics** (14 sourced + 6 derived) |
| `metric_ranks.comparison_set` | **`all | subdivision`** (typology dropped) |
| Schema tests | Plain-SQL assertion tests run via `psql -f` |

---

## Context
TransitIndex has a fully reviewed design but zero code. Every downstream lane — the `ingest/` adapters (Lane A) and the `web/` directory (Lane B) — depends on one thing existing first: the database schema, applied and seeded, with the read-only `core` / read-write `app` split enforced at the database role level. This spec delivers that and nothing else.

## Current State
- **Not a git repo yet.** Project root `C:\Users\chenc\Projects\transitindex\` holds only planning docs (`*.md`) and `.claude/`.
- Schema decisions locked in [schema-design.md §5](schema-design.md): `core`/`app` split, `text`+CHECK enums, `text[]` mode arrays, single-value+`crosscheck_value`, DB-trigger audit, no min-denominator, raw-file `archive_uri`.

---

## Repo structure
Single repo, git-initialized at the existing project root. The shared schema lives in `db/` — owned by neither service (matches the phase-plan "neither owns it" rule and dbmate's default layout).

```
transitindex/
  db/
    migrations/        # dbmate plain-SQL up/down files (the schema contract)
    seeds/             # reference-data seed SQL (modes, agencies, metrics, feeds)
    tests/             # plain-SQL assertion tests
    schema.sql         # dbmate-generated snapshot (committed; do not hand-edit)
    README.md          # how to run migrations / seeds / tests
  web/                 # empty placeholder (Lane B)
  ingest/              # empty placeholder (Lane A)
  .env.example         # DATABASE_URL template (real .env is gitignored)
  .gitignore
  *.md                 # existing planning docs (untouched)
```

> **Assumption:** one repo, not a separate Python repo for `ingest/`. Simpler for a solo dev; can split later. The decoupling that matters (web reads only) is enforced by DB roles, not by repo boundaries.

---

## What Lane 0 delivers
1. **`git init`** + `.gitignore` (ignores `.env`, `node_modules/`, `__pycache__/`, `.venv/`, dbmate local artifacts).
2. **dbmate installed and wired** to the Supabase connection.
3. **Migration files** building the entire `core` + `app` schema from [schema-design.md](schema-design.md) §3–4: every table, CHECK constraint, FK, index, the `one_current_value` partial unique index (PG15+ `NULLS NOT DISTINCT`), and the audit trigger.
4. **Role/grant migration** (the piece schema-design.md §6 lists as not-yet-covered): a least-privilege `web_reader` role with `SELECT` on `core` and read/write on `app` only — making "web is a pure reader" enforceable, not aspirational.
5. **Seed files** — reference/dimension data only (no metric values; those come from adapters): 10 modes, 10 agencies, the agency↔mode links, the **20** universal metric definitions, and the `source_feeds` rows.
6. **Test harness** — plain-SQL assertion tests run via `psql -f`, proving the invariants below.

---

## Implementation details

### dbmate + Supabase wiring
- **Install (Windows):** `scoop install dbmate`, or download `dbmate-windows-amd64.exe` from the dbmate GitHub releases and put it on `PATH`.
- **Connection string:** Supabase Dashboard → **Connect** → **Session pooler** string (IPv4-friendly; supports the session-level features migrations need). Do **not** use the transaction pooler (port 6543). Append `?sslmode=require`. Store as `DATABASE_URL` in `.env` (gitignored); ship `.env.example` with a placeholder.
- **Commands:** `dbmate up` (apply), `dbmate down` (revert last), `dbmate new <name>` (scaffold), `dbmate dump` (refresh `db/schema.sql`).
- **Postgres version:** any current Supabase project (PG15+) satisfies `NULLS NOT DISTINCT`. Confirm the project is PG15 or newer.

### Migration file order (one concern per file, so `down` is clean)
| # | File | Builds |
|---|---|---|
| 001 | `schemas_and_roles` | `CREATE SCHEMA core, app`; `web_reader` role; baseline grants |
| 002 | `core_reference` | `modes`, `agencies` (no typology), `agency_modes`, `metrics` |
| 003 | `core_periods_values` | `reporting_periods`, `metric_values` + `one_current_value` index |
| 004 | `core_provenance` | `source_documents`, `metric_value_sources`, `metric_value_audit` + audit trigger |
| 005 | `core_staging_ranks_feeds` | `pending_values`, `metric_ranks` (comparison_set `all|subdivision`), `source_feeds`, `feed_runs` |
| 006 | `app_tables` | `users`, `watchlists`, `agency_requests`, `conversion_events` |
| 007 | `grants_finalize` | re-grant `SELECT` on `core` / `ALL` on `app` to `web_reader` after all tables exist |

### Deltas vs schema-design.md (everything else follows that doc verbatim)
- **`agencies`**: drop the `typology` column and its CHECK. Directory index becomes `(subdivision)` (was `(subdivision, typology)`).
- **`metric_ranks.comparison_set`**: CHECK list is `all | subdivision` (drop `typology`). A mode-based set can be added later as one enum value.

### Seed — `modes` (10)
`code` (UNIQUE), `display_name`, `description`:
`bus`, `subway`, `light_rail`, `commuter_rail`, `streetcar`, `brt`, `trolleybus`, `ferry`, `paratransit`, `on_demand`.

### Seed — `agencies` (10)
`service_area_population` left NULL at seed (populate later from census/agency reports — do not fabricate). `country = 'CA'`, `currency = 'CAD'` for all.

| slug | legal_name | short_name | subdivision | FY-end-mo | modes (also → `primary_modes`) |
|---|---|---|---|---|---|
| ttc | Toronto Transit Commission | TTC | ON | 12 | bus, subway, streetcar, paratransit |
| stm | Société de transport de Montréal | STM | QC | 12 | bus, subway |
| translink | South Coast British Columbia Transportation Authority | TransLink | BC | 12 | bus, subway, commuter_rail, ferry, paratransit |
| metrolinx | Metrolinx (GO Transit) | Metrolinx | ON | 3 | commuter_rail, bus |
| oc-transpo | OC Transpo (City of Ottawa) | OC Transpo | ON | 12 | bus, light_rail |
| calgary-transit | Calgary Transit | Calgary Transit | AB | 12 | bus, light_rail |
| edmonton-ets | Edmonton Transit Service | ETS | AB | 12 | bus, light_rail |
| miway | MiWay (City of Mississauga) | MiWay | ON | 12 | bus |
| bc-transit | BC Transit | BC Transit | BC | 3 | bus |
| burlington-transit | Burlington Transit | Burlington Transit | ON | 12 | bus |

`agency_modes`: one row per (agency, mode) from the modes column above; `status = 'active'`, `year_started` NULL at seed.

> Verify legal names against the agencies' own sites before public render (README working-style rule). Names above are well-established public facts but should be confirmed at build.

### Seed — `metrics` (31: 22 sourced + 9 derived — expanded from 20 on 2026-05-31)

> **Balance-sheet expansion ([balance-sheet-and-frequency-plan.md](balance-sheet-and-frequency-plan.md)).**
> +11 rows beyond the original 20. **8 sourced** balance-sheet lines (all `CAD`/currency, native
> cadence annual): `total_financial_assets`, `total_liabilities`, `total_non_financial_assets`,
> `total_assets`, `tangible_capital_assets`, `accumulated_surplus`, `long_term_debt`,
> `cash_and_investments`. **3 derived:** `net_debt` (= liabilities − financial assets; `false`),
> `debt_to_assets` (%, `false`, **ranked**), `net_debt_per_capita` (CAD, `false`, **ranked**, ÷
> `service_area_population`). Raw dollar lines seed with `comparable_flag = false` (never ranked).
> **One new period primitive — `quarterly_period()` in `periods.py`** for TransLink; **no
> `period_type` enum change** (uses the existing `quarterly`). Keep `refdata.METRICS` and
> `db/seeds/04_metrics.sql` in parity.

#### The original 20 metrics
All `applicable_modes = NULL` at seed (system-wide); mode-level splits attach via `metric_values.mode_id` later, not via separate metric rows.

| code | unit | unit_type | derived | formula | higher_is_better |
|---|---|---|---|---|---|
| annual_ridership | count | count | f | — | true |
| revenue_service_hours | hours | time | f | — | null |
| vehicle_revenue_km | km | distance | f | — | null |
| average_fare | CAD | currency | t | operating_revenue / annual_ridership | null |
| trips_per_revenue_hour | trips/hr | ratio | t | annual_ridership / revenue_service_hours | true |
| on_time_performance | % | ratio | f | — | true |
| operating_revenue | CAD | currency | f | — | null |
| operating_expenses | CAD | currency | f | — | null |
| total_operating_subsidy | CAD | currency | f | — | null |
| labour_cost | CAD | currency | f | — | null |
| energy_fuel_cost | CAD | currency | f | — | null |
| materials_services_cost | CAD | currency | f | — | null |
| farebox_recovery_ratio | % | ratio | t | operating_revenue / operating_expenses | null 🔸 |
| cost_per_rider | CAD | currency | t | operating_expenses / annual_ridership | false |
| cost_per_hour | CAD/hr | currency | t | operating_expenses / revenue_service_hours | false |
| subsidy_per_rider | CAD | currency | t | (operating_expenses - operating_revenue) / annual_ridership | null 🔸 |
| fleet_size | count | count | f | — | null |
| fleet_average_age | years | time | f | — | false |
| accessible_fleet_pct | % | ratio | f | — | true |
| capital_expenditure | CAD | currency | f | — | null |

🔸 `farebox_recovery_ratio` and `subsidy_per_rider` defaulted to **neutral** to protect invariant #1 (no editorial grade). Flip in seed if you decide low farebox / high subsidy should read as "worse". Ties to the open "legibility vs neutrality" question (README).

**Sourcing reality:** `annual_ridership`, `operating_revenue` fill in Milestone 1 (StatCan); `revenue_service_hours` partly in M1 (Edmonton open data). The 4 derived ratios + `average_fare` + `trips_per_revenue_hour` auto-compute once their inputs exist. The remaining financial/asset metrics fill in **Milestone 2** (annual-report PDF pipeline) and show "— not yet sourced" until then (accepted tradeoff).

**Built-in cross-checks** this catalog enables: `total_operating_subsidy ≈ operating_expenses − operating_revenue`, and `labour_cost + energy_fuel_cost + materials_services_cost ≈ operating_expenses` — both feed the `sum_mismatch` / `cross_source_disagreement` validation flags.

### Seed — `source_feeds`
| code | display_name | tier | expected_cadence | enabled |
|---|---|---|---|---|
| statcan_307 | StatCan 23-10-0307 | 0 | monthly | true |
| edmonton_open_data | Edmonton Open Data | 1 | monthly | true |
| calgary_open_data | Calgary Open Data | 1 | monthly | true |
| translink_quarterly | TransLink Quarterly Report | 2 | quarterly | false |
| ttc_ceo_report | TTC CEO Report | 2 | monthly | false |
| oc_transpo_kpi | OC Transpo KPI scrape | 2 | monthly | false |
| metrolinx_ops | Metrolinx Operations Report | 2 | quarterly | false |
| annual_report_pdfs | Annual report PDFs (all agencies) | 2 | annual | false |

M1 feeds enabled; M2 feeds seeded but `enabled = false` until their adapters land.

---

## Acceptance Criteria
1. `dbmate up` on a fresh Supabase database applies all 7 migrations with no error; `dbmate down` reverses every one cleanly (full round-trip).
2. After `dbmate up` + seed load: exactly **10** `core.agencies`, **10** `core.modes`, **20** `core.metrics`; every `core.agency_modes` row resolves to a real agency + mode.
3. Each agency's `primary_modes` array exactly matches its `agency_modes` rows.
4. Inserting a `metric_values` row with an out-of-list `service_scope` or `quality` is **rejected** by the CHECK constraint.
5. Two `is_current = true` rows for the same (agency, metric, period, mode, scope) — including `mode_id IS NULL` — is **rejected** by `one_current_value`.
6. UPDATE-ing a `metric_values.value` writes exactly one `metric_value_audit` row with correct old/new values (trigger fires).
7. The `web_reader` role can `SELECT` from `core` but `INSERT`/`UPDATE` into `core` is **rejected**; it can write `app`.
8. The 6 derived metrics carry a non-null `formula`; the 14 non-derived carry NULL.
9. `db/schema.sql` snapshot is committed and matches the applied schema.
10. All plain-SQL tests pass via a single documented command.

## Testing Plan
| Layer | What | Count |
|---|---|---|
| Migration | `up`/`down` round-trip applies & reverses clean | 1 |
| Constraint | CHECK rejects bad enum; FK rejects orphan | +3 |
| Invariant | `one_current_value` blocks 2nd current (incl. NULL mode) | +2 |
| Trigger | audit row written on UPDATE | +1 |
| Grants | `web_reader` SELECT-only on `core`, write on `app` | +2 |
| Seed | counts (10 / 10 / 20); `primary_modes` ↔ `agency_modes` integrity; derived↔formula | +3 |

## Rollback Plan
Pre-launch, no live data. `dbmate down` reverses migrations; worst case, reset the Supabase database from the dashboard. Committed `db/schema.sql` + migration files reconstruct the schema from scratch.

## Effort Estimate
~1.5–3 days: 2h scaffold + git + dbmate/Supabase wiring · 6–8h migration files (schema is fully specced; this is transcription + constraints) · 2h seed (20 metrics + 10 agencies + modes + feeds) · 3–4h tests · 1h `db/README.md`.

## Files Reference
| File | Change |
|---|---|
| `.gitignore`, `.env.example` | new |
| `db/migrations/00{1..7}_*.sql` | new — the schema contract |
| `db/seeds/*.sql` | new — modes, agencies, agency_modes, metrics (20), source_feeds |
| `db/tests/*.sql` | new — invariant assertions |
| `db/README.md` | new — run migrations / seeds / tests |

## Out of Scope
- Any `metric_values` / `reporting_periods` real data → Lane A adapters.
- StatCan agency-code→slug map (TODOS P1) → ships with the SC-307 adapter spec.
- ORM introspection types, `web/` and `ingest/` code → Lanes A/B.
- Rank-refresh & derived-recompute job logic → Lane A.

## Follow-ups created by this spec (not Lane 0)
- **DESIGN.md sync:** card color-coding currently keys off `typology` (removed). Re-key off a coarse mode group (has-rail vs bus-only) or drop the accent.
- **Compare view (Phase 3):** the "different agency type" warning needs a non-typology basis (modes + `service_area_population`).
- These are doc/feature follow-ups; the schema does not wait on them.

## Related — next specs after this lands
- **Lane A-1:** SC-307 StatCan adapter — first real data (ridership + revenue, 7 agencies).
- **Lane B-1:** free directory shell — the SEO surface, every Canadian agency listed.

---
*When you initialize the GitHub repo, this doc converts cleanly into the founding issue; `/ship` can then close it on merge.*
