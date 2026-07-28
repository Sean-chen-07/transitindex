# TransitIndex — Documentation Status

> **This file is the single source of truth for documentation status.** Every design,
> planning, and reference doc in the repo is listed below with its current build state.
> A future Claude session should read this first, then **update it at the end of the
> session** whenever a doc's status changes or a doc is added/moved/deleted. Status
> reflects the *code reality*, not what a doc's own header claims.
>
> **Status legend:** `done` = everything the doc specs is shipped & tested ·
> `in-progress` = partially built, real work remaining · `living` = a reference that
> tracks reality and is maintained, not a build plan.
>
> **Last updated:** 2026-07-28

## Design (`docs/design/`)

| Doc | Status | Scope |
|-----|--------|-------|
| [DESIGN.md](design/DESIGN.md) | in-progress | Web design system (two-mood thesis, tokens, typography, components). Card grid + hero metrics + fleet composition shipped; 2-tab detail shipped 2026-06-10 per detail-view-metrics.md (Component #3 superseded). Remaining gaps are cross-cutting display rules: carry-forward / stale-amber states, estimate toggle, mode→color legend (F4). |
| [detail-view-metrics.md](design/detail-view-metrics.md) | living | Source of truth for the agency detail page: 2 tabs (Highlights + Financials), history-display + rank-badge rules, Recharts, metric-set sync checklist. Built 2026-06-10; viewing free for everyone, subscription gates the per-agency CSV at /api/agency/[slug]/download. §2/§4's metric-code map still partly predates the Phase 4/5 renames (deferred). Pricing copy still TODO(pricing). |
| [data-model.md](design/data-model.md) | done | Conceptual data model: flat metric layer, provenance, mixed-frequency periods, ranks layer, balance-sheet family, equation graph. All entities exist in db/schema.sql + migrations. |

## Planning (`docs/planning/`)

| Doc | Status | Scope |
|-----|--------|-------|
| [transitindex-mvp.md](planning/transitindex-mvp.md) | in-progress | CEO/MVP plan: thesis, monetization, two-milestone scope. M1 web + M2 ingest substantially built; not done because the live data load is still pending. |
| [metric-standards-review.md](planning/metric-standards-review.md) | living | First-principles audit of the metric set against CUTA/NTD/PSAB: per-metric standards table, statement reconstruction, identity checks, and the 2026-06-14 user decisions (rate only the 5 hero metrics; 4-class fleet composition; operating_expenses amortization-excluded + cost_basis; renames). Fully implemented through the v1.1 extraction-grade definition pass (2026-07-01). Open: OTP rank-badge sub-decision. |

## Reference (`docs/reference/`)

| Doc | Status | Scope |
|-----|--------|-------|
| [data-dictionary.md](reference/data-dictionary.md) | living | Plain-language, machine-checked spec for every metric. **Auto-generated** by dictionary.py from metric_dictionary.yaml — do not hand-edit; regenerate via `python -m transitindex_ingest.dictionary`. |
| [reference-ingest-cli.md](reference/reference-ingest-cli.md) | living | Complete command reference for the ingestion CLI. Matches ingest/.../cli.py exactly (subcommands, args, defaults, env vars). Includes the `ntd-monthly`/`ntd-annual` US loaders (2026-07-22). |
| [managing-data.md](reference/managing-data.md) | living | No-code how-to for viewing / hand-entering data via export-xlsx/import-xlsx + bulk loaders. Matches the shipped per-agency calendar-year workbook. |
| [source-registry.md](reference/source-registry.md) | in-progress | Maps each launch agency × metric to its source + license/tier + adapter build order. Metric catalog shipped; FTA NTD rows + adapters BUILT 2026-07-22 (`ntd_monthly.py`/`ntd_annual.py`, migration 022, USD rank basis @ fixed 0.70 CAD→USD); first network run completed 2026-07-28 (521 Full Reporter agencies seeded; annual + monthly data loaded to prod). Agency-source matrix + license tables largely unbuilt. |
| [update-frequency.md](reference/update-frequency.md) | living | Finest update frequency / publication lag / source per agency × metric; three-speed model. Most cadence adapters seeded-but-disabled; carry-forward UI absent. |
| [foi-sourcing-plan.md](reference/foi-sourcing-plan.md) | in-progress | Data-sourcing strategy + FOI playbook (FOI = fallback), per-agency channel table, request templates. Only request templates landed in code. |
| [pdf-storage-and-scanning.md](reference/pdf-storage-and-scanning.md) | living | Raw PDFs in Supabase Storage (bucket `annual-reports`) + `core.documents` catalog/scan-queue (migration 016) + `docs-*` CLI + Scan button on the review console. 64 PDFs uploaded + cataloged; cloud is the durable copy. |

## Cross-cutting (repo root)

| Doc | Status | Scope |
|-----|--------|-------|
| [../TODOS.md](../TODOS.md) | living | Action-item ledger + open decisions. STATUS.md tracks *doc* status; TODOS.md tracks *work items*. Open items from retired build plans (carry-forward display, real gold fixtures, prior_value/yoy lookup, extractor Phases 3–4, live rank backfill) are captured here. |

---

### Retired docs (2026-07-27 cleanup — recoverable from git history)

The finished build plans were deleted once their content shipped and was verified against
code; `git log --follow -- docs/<path>` recovers any of them:

`design/schema-design.md` (folded conceptually into data-model.md) ·
`design/statcan-loader-design.md` · `planning/phase-plan.md` · `planning/M1-WEB-PLAN.md` ·
`planning/lane-0-foundation-spec.md` · `planning/backend-restructure-brief.md` ·
`planning/balance-sheet-and-frequency-plan.md` · `planning/metric-set-build-plan.md` ·
`planning/pdf-extractor-plan-a-offline.md` · `planning/pdf-extractor-plan-b-api.md`

### How to maintain this file
At session end, for any doc you touched or any status that changed:
1. Update the row's **Status** and **Scope** to match the code reality (verify against `db/migrations/`, `ingest/`, `web/src/` — not the doc's own header).
2. Add a new row if you created a doc; move its row if you relocated it; note it under Retired docs if you deleted it.
3. Bump the **Last updated** date.
