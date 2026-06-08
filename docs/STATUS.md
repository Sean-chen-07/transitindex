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
> **Last updated:** 2026-06-08

## Design (`docs/design/`)

| Doc | Status | Scope |
|-----|--------|-------|
| [DESIGN.md](design/DESIGN.md) | in-progress | Web design system (two-mood thesis, tokens, typography, components). Card grid + 6 free metrics + fleet-scale shipped. **Gap:** the 5 financial-statement detail tabs (Ridership&Service / Financials / Fleet&Assets / Financial Position / Trends) are not built — detail UI is a Snapshot/Trends switch. |
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
| [balance-sheet-and-frequency-plan.md](planning/balance-sheet-and-frequency-plan.md) | in-progress | PSAB balance-sheet family + native monthly/quarterly frequency + carry-forward + workbook + web Financial Position tab. Ingest/DB shipped (11 metrics, migration 014, ratios). **Gaps:** web "Financial Position" tab (0 files in web/), 6-sheet workbook superseded by per-agency tabs, PSAB identity checks live in solver not flags.py. |

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
