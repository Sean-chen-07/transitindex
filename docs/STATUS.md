# TransitIndex — Documentation Status

> **This file is the single source of truth for documentation status.** Every design,
> planning, and reference doc in the repo is listed below with its current build state.
> A future Claude session should read this first to see at a glance what is built and
> what remains, then **update it at the end of the session** whenever a doc's status
> changes or a doc is added/moved. Status reflects the *code reality*, not what a doc's
> own header claims (several doc headers are stale — see the Notes column).
>
> **Status legend:** `done` = everything the doc specs is shipped & tested ·
> `in-progress` = partially built, real work remaining · `living` = a reference that
> tracks reality and is maintained, not a build plan · `stale-header` = built, but the
> doc's own header/status line is out of date and should be refreshed.
>
> **Last updated:** 2026-06-14

## Design (`docs/design/`)

| Doc | Status | Scope |
|-----|--------|-------|
| [DESIGN.md](design/DESIGN.md) | in-progress | Web design system (two-mood thesis, tokens, typography, components). Card grid + 6 free metrics + fleet-scale shipped. Detail view redesigned 2026-06-09 (Component #3 superseded) and the **2-tab detail (Highlights + Financials) shipped 2026-06-10** per detail-view-metrics.md. Remaining gaps are cross-cutting display rules: carry-forward / stale-amber states, estimate toggle, mode→color legend (F4). |
| [detail-view-metrics.md](design/detail-view-metrics.md) | done | Source of truth for the agency detail page: 2 tabs (Highlights hero boxes + ratios/service tables · Financials all-years statement grid), all 32 metrics placed, history-display + rank-badge rules, Recharts, metric-set sync checklist. **Built 2026-06-10** (web/src/components/detail/ + server/metrics/detail-model.ts): viewing un-gated for everyone, demo agency removed, subscription now gates the per-agency financials CSV at /api/agency/[slug]/download. Pricing copy still TODO(pricing). |
| [data-model.md](design/data-model.md) | done | Conceptual data model: flat metric layer, provenance, mixed-frequency periods, ranks layer, balance-sheet family, equation graph. All entities exist in db/schema.sql + migrations 001-015. *Header says "Proposed (pre-build)" — stale.* |
| [schema-design.md](design/schema-design.md) | done | Concrete build-ready Postgres schema (types, constraints, indexes, locked decisions). Every table/index/decision shipped under db/migrations/. Near-duplicate of data-model.md (see merge candidates). *Header says "pre-migration" — stale.* |
| [statcan-loader-design.md](design/statcan-loader-design.md) | done | Architecture for the fast, idempotent, diff-aware StatCan + Hamilton bulk loader. Shipped in commit 17a466b (jobs/bulk_load.py, CLI statcan-load/hamilton-load, .bat wrappers). *Header says "PLAN ONLY — no code" — stale.* |

## Planning (`docs/planning/`)

| Doc | Status | Scope |
|-----|--------|-------|
| [transitindex-mvp.md](planning/transitindex-mvp.md) | in-progress | CEO/MVP plan: thesis, free/paid rank gate, two-milestone scope. M1 web + M2 ingest substantially built; not done because live data load is still pending. |
| [phase-plan.md](planning/phase-plan.md) | in-progress | Master roadmap (4 phases / 2 milestones), tech stack, ingestion strategy, review logs. Both milestones built; remaining: per-agency PDF adapters, live data load. **Doc's 2026-05-31 "M1 0% started" headline is STALE — refresh.** |
| [M1-WEB-PLAN.md](planning/M1-WEB-PLAN.md) | in-progress | M1 web build plan: free directory, detail pages, $20/yr Stripe paywall, server-only choke point. All code shipped; only Step 9 (live StatCan rank backfill in prod) outstanding. |
| [lane-0-foundation-spec.md](planning/lane-0-foundation-spec.md) | done | Build spec for the DB foundation (migrations, roles, seeds, tests, acceptance criteria). All 7 migrations + seeds + tests present; extended past spec (migrations 008-015). *Header "nothing committed" — stale.* |
| [backend-restructure-brief.md](planning/backend-restructure-brief.md) | done | Brief for equation graph + period rollup + per-metric dictionary + DB/workbook restructure. All four goals shipped (equations.py, migrations 012-015, dictionary). *Header "Not started" — stale.* |
| [balance-sheet-and-frequency-plan.md](planning/balance-sheet-and-frequency-plan.md) | in-progress | PSAB balance-sheet family + native monthly/quarterly frequency + carry-forward + workbook + web balance-sheet display. Ingest/DB shipped (11 metrics, migration 014, ratios). **2026-06-10:** web balance-sheet shipped as Section B of the Financials tab; §6's EN+FR statement anchors, printed_label/table_reference tool fields, and PSAB identities in flags.py (run at staging via validate_cohort in run_pdf) all landed. **Gaps:** carry-forward web display; gold fixtures need real verified values; prior_value (yoy) lookup not wired; 6-sheet workbook superseded by per-agency tabs. |
| [pdf-extractor-plan-a-offline.md](planning/pdf-extractor-plan-a-offline.md) | done | **New 2026-06-12; offline Phases 0–1 BUILT + tested 2026-06-12.** Chunked-hybrid extractor improvement (from the 10-PDF smoke test, 38% review rate): smoke fixture baseline, per-segment recording + value serializers, gold candidates (3 docs in `tests/fixtures/gold/candidates/` awaiting the user's manual confirmation gate), 0.5% merge tolerance, canonical units from refdata, source-quote digit check, 0.3 confidence floor, sourced-currency sanity floor, dead per-chunk cache_control removal + page-label fix, chunk section/scale context, offline replay report (`eval/replay.py`). Suite green offline. Replay on the smoke fixture: conflicts 150→103, conf≤0.5 169→122. |
| [metric-standards-review.md](planning/metric-standards-review.md) | living | **New 2026-06-14; design review, no product code changed.** First-principles audit of all 32 metrics in `refdata.METRICS` against CUTA/NTD/PSAB. Part A: per-metric standards table + reasoning; Part B: statement reconstruction + identity pass/fail (balance sheet closes; operating statement can't — missing amortization/other/annual-result); Part D: proposed additions (amortization, annual_surplus_deficit, total_revenue/expenses enterprise lens, other_operating_expenses, asset_consumption_ratio). **User decisions taken 2026-06-14** (in the "Decisions taken" block, and the body reconciled to match): rate only the 5 hero boxes (retires the 2 balance-sheet ranked ratios); drop `fleet_capacity`+weights → non-ranked 4-class fleet composition (Bus·Light rail·Heavy rail·Commuter rail, counted by trains); pin `operating_expenses` (amortization excluded + `cost_basis` field) and `operating_revenue` (earned only). Open: OTP rank badge (footnote vs drop). Implementation in metric-set-build-plan.md. |
| [metric-set-build-plan.md](planning/metric-set-build-plan.md) | in-progress | **New 2026-06-14; not yet built.** Phased implementation plan for the metric-standards-review decisions: (1) ranking → 5 hero metrics via a `RATED_METRICS` allow-list; (2) `operating_revenue` boundary in the dictionary; (3) `cost_basis` dimension (contract + migration 017 + repo + derived ratios); (4) add amortization/other_operating_expenses/total_revenue/total_expenses/annual_surplus_deficit/asset_consumption_ratio; (5) fix `expense_components` + net-debt + component-bounds identities in flags.py; (6) drop `fleet_capacity`+`MODE_CAPACITY_WEIGHT` → 4-class composition from per-mode `fleet_size`; (7) extractor/gold/OTP-badge/docs. Names the parity guardrail (refdata↔04_metrics.sql↔yaml) + suggested commit sequence. Asset-consumption-ratio gated on sourcing its 2 inputs. |
| [pdf-extractor-plan-b-api.md](planning/pdf-extractor-plan-b-api.md) | in-progress | **New 2026-06-12; Phase 2 OFFLINE code BUILT + tested 2026-06-12 (steps 2.1–2.6) + per-segment model routing.** `service_scope`+`basis` enums on `ExtractedValue`/tool/merge `_key`, out-of-scope filtering (drop mode_subset/city_wide + budget/forecast, keep restated), doc-context (`doc_type`/`author_label`/`year`) plumbed through `ExtractionRequest`→`run_pdf`→`scan`→`cli`, definition-canon (`dictionary.extraction_guidance`) + doc-aware intro lines, text chunks→Sonnet & image batches→Opus (measured $0.89→$0.61/PDF), and `eval/smoke.py` runner. Suite green offline. **Held:** step 2.7 PAID run done once (validated scope split vs hand-read TTC 2019); Phases 3 (prefilter/Batch/Sonnet) & 4 (corroboration) gated; per-metric canonical definition work is next. |

## Reference (`docs/reference/`)

| Doc | Status | Scope |
|-----|--------|-------|
| [data-dictionary.md](reference/data-dictionary.md) | living | Plain-language, machine-checked spec for every metric. **Auto-generated** by dictionary.py from metric_dictionary.yaml — do not hand-edit; regenerate via `python -m transitindex_ingest.dictionary`. |
| [reference-ingest-cli.md](reference/reference-ingest-cli.md) | living | Complete command reference for the ingestion CLI. Matches ingest/.../cli.py exactly (subcommands, args, defaults, env vars). |
| [managing-data.md](reference/managing-data.md) | living | No-code how-to for viewing / hand-entering data via export-xlsx/import-xlsx + bulk loaders. **Refreshed 2026-06-07** to match the shipped per-agency calendar-year workbook (one tab per agency; months → quarter/YTD/Year; Fleet block + Fleet scale; white/grey colour code). Commands, .bat loaders, --reset all accurate. |
| [source-registry.md](reference/source-registry.md) | in-progress | Maps each launch agency × metric to its source + license/tier + adapter build order. Metric catalog shipped (32 codes); only 2 of ~13 source adapters built; agency-source matrix + adapter roadmap + license tables largely unbuilt. |
| [update-frequency.md](reference/update-frequency.md) | living | Finest update frequency / publication lag / source per agency × metric; three-speed model. Schema requirement satisfied; most cadence adapters seeded-but-disabled with no code; carry-forward UI absent. Actively maintained. |
| [foi-sourcing-plan.md](reference/foi-sourcing-plan.md) | in-progress | Data-sourcing strategy + FOI playbook (FOI = fallback), per-agency channel table, request templates. Only request templates landed in code; central "kill synthetic gold fixture" action still open (see TODOS.md). |
| [pdf-storage-and-scanning.md](reference/pdf-storage-and-scanning.md) | living | Raw PDFs in Supabase Storage (bucket `annual-reports`) + `core.documents` catalog/scan-queue (migration 016) + `docs-*` CLI + Scan button on the review console. Shipped: storage.py, catalog.py, scan.py, review/console.py; 64 PDFs uploaded + cataloged, local copies removed. |

## Cross-cutting (repo root)

| Doc | Status | Scope |
|-----|--------|-------|
| [../TODOS.md](../TODOS.md) | living | Action-item ledger + open decisions captured from CEO/design/eng/devex reviews. Stays at repo root. STATUS.md tracks *doc* status; TODOS.md tracks *work items*. |

---

### Merge candidates (overlapping docs — not auto-merged)

- **design/data-model.md + design/schema-design.md** — near-duplicate (concept vs concrete view of the *same* shipped schema, both `done`). Future: fold schema-design into a "Concrete schema" section of data-model.
- **planning/phase-plan.md + planning/M1-WEB-PLAN.md + planning/transitindex-mvp.md** — overlapping milestone/scope narratives. Future: a planning index with the two sub-plans linked beneath.
- **reference/source-registry.md + reference/update-frequency.md** — both agency × metric matrices over the same launch-agency rows.
- **planning/balance-sheet-and-frequency-plan.md + planning/backend-restructure-brief.md** — both pre-build briefs feeding the now-shipped equation-graph / balance-sheet / rollup work.

### How to maintain this file
At session end, for any doc you touched or any status that changed:
1. Update the row's **Status** and **Scope** to match the code reality (verify against `db/migrations/`, `ingest/`, `web/src/` — not the doc's own header).
2. Add a new row if you created a doc; move its row to the right category if you relocated it.
3. Bump the **Last updated** date.
4. When a `stale-header` doc gets its header fixed, drop the stale note.
