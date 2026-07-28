# TransitIndex — TODOS

Deferred work and decisions, captured from the 2026-05-29 CEO review.
"Written down or it doesn't exist." Source of truth for build order is the MVP
sequence in `phase-plan.md` and the approved office-hours design doc.

## P1 — blockers (resolve before/at start of build)

### Confirm source licensing per feed before ANY public render
- **What:** Verify each launch source permits derived public display with attribution.
- **Why:** The CUTA trap (anti-derivation terms — back-room only) and per-city variance
  in municipal open-data licences mean a wrong assumption ships an unlicensed product.
  Facts aren't copyrightable in Canada, but a source's *compilation* can be restricted.
- **Context:** StatCan open licence = yes, attribution required. Municipal portals =
  verify per city (Calgary/Edmonton/Ottawa). Agency PDFs = facts free, confirm no
  redistribution restriction. CUTA = never a cited public source. See source-registry.md.
- **Effort:** S (research, not code). **Priority:** P1. **Blocks:** public launch.

### ~~Pick ORM: Drizzle vs Prisma~~ ✓
- **Completed v0.0.1.0 (2026-05-31):** Drizzle introspect (pull-only; no push/migrate).

### ~~StatCan agency-code → slug mapping table~~ ✓
- **Expanded 2026-06-04:** `STATCAN_AGENCY_MAP` now covers 11 agencies. Added Winnipeg Transit,
  `"Halifax transit"` (lowercase t — verify on next CSV download), `"Réseau de transport de
  Longueuil"` (RTL), and Regina Transit. Strings for STL Laval and Grand River Transit are NOT
  confirmed from the live CSV — download 23-10-0307 and search for them before adding.

## P2 — should land in the MVP branch

### Value-contract test + StatCan fixture parse test
- **What:** A contract test asserting every adapter emits the identical row shape
  (agency, metric, period type + real start/end, mode, service_scope, value, unit,
  currency, source doc/page/url + license + retrieved date, quality, confidence);
  plus a fixture-based parse test for the StatCan adapter.
- **Why:** The contract is what keeps adapters/validation/store/web decoupled and
  country-agnostic. Without the test, later adapters drift and the decoupling rots.
- **Effort:** S-M. **Priority:** P2.

> NOTE: Peer-percentile ranking moved INTO MVP scope (it is the free tier: free = ranking,
> paid = ranking + raw number). See phase-plan.md Phase 2. Needs `comparable_flag` +
> province (`subdivision`) peer-set logic at build time (typology dropped 2026-05-30).

## P3 — follow-ups

### Index on agencies(subdivision)
- **What:** Add the index backing the directory filter/listing.
- **Why:** The all-CA-agencies directory is the only list view; filter perf.
- **Effort:** S. **Priority:** P3.

## Design (from plan-design-review 2026-05-30)
Full spec in phase-plan.md "Design" section + DESIGN.md. Items below are build/debt.

### Rank period-comparability (eng + data-model) — P1/P2
- **What:** Rank computation must compare the same *period* across agencies, not only the
  same scope. Agency missing the latest period → rank on latest comparable period or sit out
  (flagged), never silently mixed across years.
- **Why:** A rank mixing FY2024 vs FY2023 is a wrong number — the exact dispute-proof
  failure the product exists to prevent. Pairs with the existing scope guard.
- **Blocks:** any public rank render. **Confirm in eng review / record in data-model.md.**

### ~~Strict period-matched ratios — P2~~ ✓
- **Completed v0.0.3.0:** The equation-graph solver (`equations.py` + `jobs/derived_recompute.py`)
  computes every derived value from SAME-period values only, partitioned by (mode, scope). No
  cross-period mixing is possible by construction.
- **What:** Derived ratios (cost-per-rider, farebox recovery, subsidy-per-rider) computed
  only from same-period inputs; labeled "as of FYxxxx"; "= a ÷ b" note; no TTM/mixed estimate.
- **Why:** Mixed-period ratios are attackable; annual is the native cadence for these metrics.

### WCAG 2.1 AA baseline — P2
- **What:** Real table semantics, screen-reader rank labels ("ranked 1st of 10"), mode group
  by icon+label not color alone, focus-trapped paywall dialog, 44px targets, body ≥16px,
  contrast ≥4.5:1, sparkline text alternatives.
- **Why:** Audience is civic/government; a11y is effectively required, not optional.

### Stale-feed visual treatment — P2
- **What:** When a metric is past its expected cadence, render "as of" muted + amber
  "may be outdated"; normal reporting lag stays clean. Driven by the feed-health alert.
- **Why:** Honest freshness is the trust story (invariants #2/#3).

### ~~Directory IA: search + province grouping + expand-in-place~~ ✓
- **Completed v0.0.1.0 (2026-05-31):** Unified searchable table (province is a column + search term, not grouping), accordion expand-in-place, all 136 agencies crawlable in server HTML.

### Mobile 3-level (Bloomberg/Yahoo-iOS) — P3
- **What:** L1 list (name + 1–2 ranks) → L2 full card → L3 tabbed paid sheet; sheet rows
  tap-to-expand. Optional: "N of 6 sourced" completeness meter on cards (D8 enhancement).

### Deferred design (revisit only on demand)
- AI-generated mockups / aesthetic variants — needs OpenAI key (`design setup`).
- Clickable source deep-links — dropped (D6); revisit if buyers want the live "prove it" click.
- Fresher TTM ratio estimates — rejected (D12); revisit only if buyers ask.

### From /design-review 2026-06-06 (live app, branch design/web-review)
Audit of the running web app. **F1, F2, F5, F6 fixed and committed on the branch.**
Outstanding (need a product/data or design decision):
- **F3 — detail "FULL DATA" table contradicts the rank cards (P2).** Cards say "7th/6th"
  while the table lists the same metrics "not yet ranked" with no period/year label, so rows
  read as duplicates. Show the period per row + reconcile the rank wording. Touches the
  metrics read layer, not just CSS. (Overlaps the period-comparability work above.)
  **→ ✓ Resolved by the 2-tab detail redesign (shipped 2026-06-10):** rank badges show only on the 6
  directory-card metrics; every row shows its value with its own period; no rank/blank duplication.
  See "Build the redesigned detail view" above + [detail-view-metrics.md](docs/design/detail-view-metrics.md).
- **F4 — mode-color left bar has no visible legend; 126/136 bars are one yellow (P3).**
  sr-only label + expand pills cover a11y, but the color does little for a collapsed sighted
  view. Add a small legend or accept it's decorative. (Related to the WCAG "mode group by
  icon+label not colour alone" item above.)
- ~~**F5 — header logo tap target 28px (<44px).**~~ ✓ Fixed (commit `7fee14f`): py-2 + -my-2 → 44px.
- ~~**F6 — no favicon / icon / OpenGraph image (all 404).**~~ ✓ Fixed (commit `b380f45`):
  `app/icon.svg` (coral mark) + `app/opengraph-image.tsx` (1200×630 brand card) + OG metadata.

## Architecture (from eng re-review 2026-05-30)
Resolutions captured in phase-plan.md "Architecture — eng re-review" + data-model.md.

### ~~Paywall: account-gate numbers server-side~~ ✓ — P1
- **Completed 2026-06-04 (PR #7):** Auth.js (migration 008) + `web/src/server/entitlement.ts`
  gate raw numbers behind an active Stripe subscription, checked server-side live per request;
  the free rank path stays login-free and crawlable. The structural choke point landed
  v0.0.1.0; this wired the real account + subscription check.
- **What:** Raw numbers gate behind a paid account, enforced server-side; web serves free
  public ranks (crawlable, no login, no tracking); drop the anonymous metering. Native app
  deferred to Phase 3.
- **Why:** The design review's 1-free-detail cookie meter + crawlable full-detail made the
  paid dataset trivially scrapeable (reopened invariant A1). Account-gate closes it without
  any user tracking (no App Store ATT concern).
- **Test (IRON):** unauthenticated detail request returns ranks only, never raw numbers.

### `metric_ranks` materialized table + refresh job — P1
- **What:** Precompute ranks in the data layer (`all`/`subdivision` sets);
  refresh incrementally on promote/restate. Period-comparability rule: same-period only;
  missing-period agency → "not ranked".
- **Why:** Ranks are on every free card (SEO surface); recomputing per request is wasteful
  and risks the period/scope rule drifting across call-sites.
- **Test (IRON):** same-period-only rank; missing-period → not ranked, never cross-year.

### ~~Derived-recompute step (ratios) — P2~~ ✓
- **Completed v0.0.3.0:** Replaced the one-directional `_DERIVED` dict with a bidirectional
  equation-graph solver. It back-solves any unknown (e.g. expenses from farebox + revenue),
  chains to a fixpoint, writes each solved value as a first-class `metric_value` carrying full
  provenance (`metric_value_derivations` → exact input rows, migration 013), inherits the weakest
  input's quality, and re-runs idempotently on input promote/restate. Cross-source / over-
  determination disagreements raise `sum_mismatch` / `cross_source_disagreement`.
- **What:** Post-promotion step computes period-matched ratios from approved inputs, stores
  as first-class `metric_values`, re-runs on input promote/restate; auto sanity flags.
- **Why:** Pipeline had no derived-compute step; a corrected input could leave a stale ratio.
- **Test (IRON/regression):** corrected input re-runs the ratio, no stale value.

### Incremental recompute — P3
- **What:** Both jobs recompute only the affected metric/period/agency cohort, not full rebuilds.
- **Why:** A monthly StatCan update shouldn't re-rank all 100+ agencies × all metrics.

## Data population — completed in 2026-06-04 session (feat/data-population branch)

### ✓ Done
- **StatCan 23-10-0307 expanded to 11 agencies.** Added Winnipeg Transit,
  `"Halifax transit"` (lowercase t — verify on next CSV download), RTL Longueuil
  (`"Réseau de transport de Longueuil"`), and Regina Transit to `STATCAN_AGENCY_MAP`.
  Next step: download the actual CSV and confirm all 11 strings; STL Laval / GRT / OC Transpo
  strings are unconfirmed (OC Transpo likely absent from this table).
- **11 expansion agencies seeded** in `02_agencies.sql`, `03_agency_modes.sql`, `refdata.py`,
  and migration 010. Slugs: winnipeg-transit, hamilton-street-railway, brampton-transit,
  grand-river-transit, stl-laval, rtl-longueuil, york-region-transit, halifax-transit,
  durham-region-transit, saskatoon-transit, regina-transit.
- **Hamilton HSR adapter built** (`adapters/hamilton_hsr.py`): reads ArcGIS JSON API
  (the f=csv endpoint returns 400; the JSON endpoint works). 144 months (Jan 2014–Apr 2025)
  staged to `pending_values`. CLI command: `python -m transitindex_ingest hamilton <csv>`.
  Fetch script: `run_hamilton.py` at project root.
- **ogl_hamilton** added to `contract.py` + DB migration 011 (CHECK constraint).
- **Workbook updated**: `AGENCY_NAMES` now includes all 21 tracked agencies (105 rows × 5 years).

### Next session: to-do for data population
- **Download the actual StatCan 23-10-0307 CSV** (from statcan.gc.ca) and run
  `python -m transitindex_ingest statcan <path>` to populate monthly_ridership + operating_revenue
  for 11 agencies. This is the highest-value single action.
- **Verify Halifax transit string** — the StatCan variable reference shows lowercase "t"; if
  the actual CSV differs, update STATCAN_AGENCY_MAP.
- **PDF extraction** (annual reports) for MiWay, Halifax Transit, York Region, Brampton, Metrolinx,
  BC Transit, OC Transpo: run `python -m transitindex_ingest pdf-smoke --url <pdf_url> --agency <slug>`
  then approve clean values via the review API.
- **Fill the workbook** for annual metrics: run `export-xlsx`, open the .xlsx, enter values from
  agency annual reports (TTC 2023/2024, STM, TransLink, Calgary, Edmonton, MiWay, BC Transit),
  then `import-xlsx`. Priority columns: annual_ridership, operating_expenses, operating_revenue.
- **US / NTD seed — LOADED 2026-07-28** (fetch + generator + migration 022 + seed 08 + both
  loaders all ran: 521 Full Reporter agencies; annual = 7,687 values / 3 report years with
  derived ratios + ranks; monthly = 134,235 values / 89 months, 178 rank cohorts; verify
  ok=True both). STILL OPEN:
  - spot-check NYCT / LA Metro / CTA / King County figures against FTA-published numbers,
    and re-confirm the public-domain terms on the live portal (see source-registry NTD-M row).
  Follow-ups: NTD funding-sources adapter (`4tmr-gwuu`) so `subsidy`/`subsidy_per_rider` rank
  for US agencies; fiscal-year-end refinement from the NTD Agency Information dataset
  (US agencies currently default to December); `ntd_reference` annotations in
  `metric_dictionary.yaml`.

## Data expansion — balance sheets + native frequency (2026-05-31)
Full plan: balance-sheet-and-frequency-plan.md (retired to git history, 2026-07-27 docs cleanup).

> **Mostly DELIVERED in v0.0.3.0** (the backend restructure folded this in). DONE: `quarterly_period()`;
> 11 balance-sheet metrics seeded (`refdata.METRICS` + `04_metrics.sql`, parity-tested); `net_debt` /
> `debt_to_assets` / `net_debt_per_capita` via the equation graph (population read from
> `agencies.service_area_population`); raw dollars `comparable_flag=false` (never ranked); the PSAB
> SUM identities (asset split, net-debt, accumulated-surplus) cross-checked by the solver;
> `parse_number` accounting-negatives fixed; the `printed_scale`/`printed_sign` extraction tool fields
> (model declares, code applies). The equation/derivation tables needed migrations after all
> (013 — the plan's "no migration" held for the metrics, not the graph). 2026-06-10: the EN+FR
> statement anchors landed in the `claude_pdf.py` prefilter; the PSAB asset-split + accumulated-surplus
> identities landed in `flags.py` `sum_mismatch` (and run at staging via `validate_cohort` in `run_pdf`);
> `printed_label`/`table_reference` tool fields now flow into notes + provenance. STILL DEFERRED: the
> 6-sheet workbook redesign; carry-forward web display; gold fixtures (need real verified data).

Build tasks, roughly in order:

- **`quarterly_period()` builder** (`ingest/.../periods.py`) — the one new period primitive
  (TransLink). No `period_type` enum change. **P2.**
- **Seed 11 new metrics** in `refdata.METRICS` *and* `db/seeds/04_metrics.sql` (kept in parity):
  8 sourced balance-sheet lines (`comparable_flag=false`) + `net_debt`, `debt_to_assets`,
  `net_debt_per_capita`. Catalog 20 → 31. **P2.**
- **Derived recompute** (`jobs/derived_recompute.py`): add `net_debt`, `debt_to_assets`,
  `net_debt_per_capita`; pass `service_area_population` into the inputs map for per-capita. **P2.**
- **Workbook multi-sheet redesign** (`workbook.py`): Monthly / Annual Fundamentals / Balance Sheet
  sheets keyed by a `Period` token; balance-sheet check columns; light-yellow optional cells;
  import dispatches the token to `annual_period`/`quarterly_period`. **P2.**
- **`parse_number` accounting-negatives bug** (`pdf/llm.py`): `(1,234)` currently raises and the
  value is silently dropped — strip accounting parens → `-1234`. **P1 (correctness bug).**
- **Financial-statement extraction** (`pdf/llm.py`, `pdf/claude_pdf.py`): locate-then-read
  statement pages (EN+FR title anchors); add `printed_label`/`table_reference`/`printed_scale`/
  `printed_sign`/`column_year` tool fields (model declares scale & sign, code applies); always feed
  page images for statements; harvest the prior-year comparative column = free history. **P2.**
- **PSAB identity checks** (`validation/flags.py`): asset split, net-debt identity, printed-vs-
  computed net debt, component bounds — reuse `sum_mismatch`/`cross_source_disagreement`/
  `unit_mismatch` (no new flag strings); 2% relative + absolute floor. **P2.**
- **Carry-forward display rule** (web): latest value carried forward with amber + "carried
  forward"; never stored, never ranked; charts show a gap. **P2.**
- **Gold fixtures** (`eval/gold.py`): TransLink balance sheet, one `should_flag` per failure mode,
  one French (STM) fixture; 0.5% tolerance for currency lines. **P3.**
- **Open decisions** (defaults in the plan §9): balance-sheet depth (defer reserves +
  surplus-bridge?), per-capita denominator (static pop?), TransLink quarterly balance sheet (yes?),
  restatement label (show?). **Manual-entry quality flag: ✅ DECIDED — keep `verified`** (no change).

## Deferred features (gated on demand validation: >=3 of 10 buyers pay)
- **Public API + bulk dataset download** (CSV/Parquet + JSON endpoint). Out of MVP —
  the MVP audience reads the website, they don't write code. Build only if a researcher,
  journalist, or another builder asks for raw/programmatic access. DX checklist below.
- **Compare view** (2–4 agencies side by side, type-mismatch warnings — by modes + size).
- **Accounts / watchlist / personal dashboard** (Auth.js). *Accounts + Stripe billing shipped
  2026-06-04 (PR #7); the watchlist + personal dashboard remain deferred.*
- **PDF + human-review treadmill** (TTC CEO Report adapter, annual-report adapters,
  OC Transpo scraper, board decks). This is the cost center — do not scale on conviction.
- ~~**US / NTD ingestion**~~ ✓ **BUILT 2026-07-22** (migration 022, `adapters/ntd_monthly.py` +
  `ntd_annual.py`, `ntd-monthly`/`ntd-annual` CLI, generated `refdata_us.py` registry, USD rank
  basis at a fixed 0.70 CAD→USD rate, web US-state/currency display). Remaining: the seed
  bootstrap + follow-ups tracked under "Next session: to-do for data population".
- **Bounding-box provenance deep-links** (~2× ingestion cost).

## Open decisions (from README + design doc)
- Legibility vs neutrality (recommend: strictly factual, no editorial grade).
- **Everything-paid vs free-public — ✅ DECIDED FREE-PUBLIC (2026-06-09).** Model: **viewing is unlimited
  and free** (no rank-gate, no metering, no login to read); the **paid product is data download by
  subscription, one agency at a time** (CSV/Excel of the all-years statement grid). Pricing + subscription
  mechanics deferred ("deal with it later"); bulk / multi-agency export stays the pre-existing "build when
  a researcher asks" deferral. **Inverts** the shipped free=ranks / paid=numbers model (the $20/yr demand
  test). Doc reconciliation done — superseding pointers in detail-view-metrics §6, DESIGN.md,
  transitindex-mvp, M1-WEB-PLAN, phase-plan. **Code change shipped 2026-06-10** (see build task below).
  Decisions locked 2026-06-09: **CSV only** (no .xlsx); download = **the financials statement grid**;
  no quota (per-agency = visit each agency's page); demo agency removed; after subscribing the user
  returns to the agency page they came from. **Pricing still TBD** — TODO(pricing) markers in
  subscribe-dialog.tsx, checkout.ts, account/page.tsx; the live charge is whatever STRIPE_PRICE_ID points at.
- DB host: Neon vs Supabase. Restatement display. Provenance granularity (page-level at launch).

### ~~Build the redesigned detail view (2-tab)~~ ✓ — P2
- **Completed 2026-06-10 (branch detail-view-redesign):** two tabs (Highlights + Financials) per
  [detail-view-metrics.md](docs/design/detail-view-metrics.md). Highlights = 6 hero boxes (rank badge +
  neutral YoY arrow + click-to-expand Recharts chart, Yearly/Monthly toggle on the two monthly heroes)
  over the ratios | service&fleet value tables. Financials = both statements, all years as columns,
  blank-never-zero, with the gated CSV download button. Recharts 3.8.1 added. Resolves **F3** below.
- **Access change shipped with it:** the viewing gate is removed (raw numbers reach everyone — the
  choke-point *structure* in `web/src/server/metrics/` is kept, it just no longer strips), the demo
  agency is removed, and the subscription now gates `/api/agency/[slug]/download` (CSV of the
  financials grid; session + `isPaid` checked live per request). New contract tests:
  `detail-model.test.ts`, `csv.test.ts`; `web/CLAUDE.md` invariants rewritten to match.

## DX / API (deferred — flagged by plan-devex-review 2026-05-30)

**Status:** Not in MVP. The MVP has no developer-facing surface — it's a website for
non-technical civic users (city staff, councillors, advocates). A developer-experience
review doesn't apply until there's something developers plug into. Revisit only if
people ask for programmatic access or raw data — that request is the demand signal.

**DX checklist for when you build the public API + dataset download** (so first
impressions land):
- **No-signup demo first.** A copy-paste example that returns real data with no API key
  gets people to "it works" in under 2 minutes. Require a key only to scale up.
- **Stable IDs + clear units.** Every number says what it is (e.g. "annual unlinked
  passenger trips") with its period and as-of date — the same provenance rules the
  website already enforces.
- **One copy-paste example that actually runs.** A real query returning real numbers,
  not a fill-in-the-blanks template.
- **Honest errors.** When a call fails, say what went wrong and how to fix it.
- **Respect the paywall.** Same rule as the web app — raw numbers never ship to an
  unauthenticated caller; the free API tier returns ranks only.

## Re-review action items (2026-05-31, /autoplan) — M1-FIRST

The /autoplan re-review graded the plan against the **merged** Lane 0 + Lane A code and
found the "0 critical gaps / paywall holds" status was overstated: the build inverted its
own sequencing (M2 PDF pipeline fully built; M1 `web/` = `.gitkeep`, 0% started). **User
decision: M1-first — freeze M2 additions; the next code goes into `web/`.** Full findings +
audit trail in `phase-plan.md` (RE-REVIEW section); evidence in
`~/.gstack/projects/transitindex/chenc-master-test-plan-20260531.md`.

### DONE
- **`monthly_ridership` metric added; StatCan no longer mislabels monthly trips as
  `annual_ridership`.** `statcan_307.py` maps "Total passenger trips" → `monthly_ridership`;
  metric registered in `refdata.py` + `db/seeds/04_metrics.sql` (now 21 metrics); count
  assertions updated. 135 tests pass. NOTE: M1 (StatCan-only) now has NO `annual_ridership`
  until a month→year rollup or annual sources exist — M1 ranks on `monthly_ridership`.

### P1 — before M1 ships
- ~~**Add auth to the review `/approve` endpoint** (`review/app.py`).~~ ✓ **Completed
  2026-06-04:** mutating endpoints (approve/reject/edit) require an `Authorization: Bearer
  <token>` header matching `REVIEW_API_TOKEN`; read endpoints stay open. The `review` CLI
  fails closed — it refuses to serve without a token. Covered by `test_review_api.py`.
- ~~**Reconcile DESIGN.md + the 3 wireframes to the account-gate model.**~~ ✓ **Completed v0.0.1.0 (2026-05-31):** DESIGN.md reconciled — meter language removed, "numbers gated (anonymous)" state added, 2026-05-31 status note recorded.
- ~~**Paywall integrity is UNVERIFIED until `web/` ships**~~ ✓ **Completed v0.0.1.0 (2026-05-31):** `web/` shipped. Paywall enforced via server-only choke point + disjoint types + ESLint import restriction. A1 test structured (skipped until TEST_DATABASE_URL available).
- ~~**Period-comparability in `refresh_ranks`**~~ ✓ **Done in the web read-layer (verified
  2026-06-04):** `web/src/server/data/ranks.ts` (`getLatestRankedPeriodPerMetric` +
  `reconcileRanks`) resolves each metric's latest comparable period and emits "not ranked —
  latest <label>" for any agency missing it, plus the N<5 suppression. The Python
  `refresh_ranks` job is intentionally single-period only (proven by
  `test_refresh_ranks_ignores_other_periods`); `web/CLAUDE.md` documents the web layer as the
  guard by design.

### P2
- **Reconcile the scope-guard contradiction.** Schema DECISION 3 dropped the scope-caveat
  guard, but the plan invariant + Failure Modes T2 still claim it. Either re-introduce a
  UI-rendered scope flag (BC Transit = Victoria, Metrolinx = GO+UP) in `metric_values.notes`,
  or delete the invariant/T2 claim. As-is, BC Transit (Victoria-only) ranks vs TTC whole-system.
- **Wire live validation into the real path.** *Mostly done 2026-06-10:* the PDF path
  (`scan.py` + `cli.py` `pdf` command) now passes the real `validate` into `run_pdf`, and
  `run_pdf` always runs `validate_cohort` per reporting period (the sum/PSAB identities fire at
  staging). STILL OPEN: `prior_value` stays `None` everywhere (the prior-year repo lookup doesn't
  exist, so `yoy_spike` can't fire on live runs) + auto-flag PDF↔StatCan disagreement.
- **Postgres-backed CI test.** All 135 tests run on `InMemoryRepository` (which reimplements
  the invariants in Python). Add a CI job that applies `db/migrations`, runs `db/tests/*.sql`,
  and round-trips `PostgresRepository` so the real `one_current_value` index / audit trigger /
  grants are actually exercised.
- **Replace the synthetic gold fixture with REAL values.** `ttc_annual_2024.json` reads as
  made-up round numbers; the eval grades against it. Seed it from real TTC 2024 figures
  (and an Edmonton cross-check) — see `foi-sourcing-plan.md` "Start here". Add the design
  states (error, gated-anon, N<5) flagged in the design re-review.

## Full-workbase audit (2026-06-11, multi-agent, adversarially verified)

21-agent audit across UI / security / ingest / db-infra / data-collection / dependencies;
every serious finding below survived an adversarial refute pass. **Fixed same day:**
keyboard focus rings (button.tsx/dialog.tsx), branded error/404/loading pages, dbmate
markers on migrations 010+011 (from-scratch rebuild was broken), GitHub Actions CI
(.github/workflows/ci.yml: ingest pytest · db rebuild+seeds+SQL tests · web gate incl.
build — this also delivers the "Postgres-backed CI test" item above), security headers,
exact-pin next-auth, `backup-data.bat` + `scripts/backup-data.ps1`.

### P1 — wrong-numbers / data-loss class (ingest)
- ~~**Verify pass can silently rescale a value 1000×.**~~ ✓ **Fixed 2026-06-11:** VERIFY_TOOL
  now mirrors the extract tool (corrected_value AS PRINTED + printed_scale/printed_sign,
  `apply_scale_sign` applied in `_merge_verify`); a correction that omits the scale inherits
  the original reading's, so echoed printed digits can never rescale; the verify catalogue
  marks scaled values `[printed in thousands]`. 3 regression tests in test_claude_extractor.py.
- ~~**`--reset` wipes ALL data for the feed's agencies**~~ ✓ **Fixed 2026-06-11:** new
  `Repository.wipe_feed_data` scopes the delete to the feed's **source document** (via
  `metric_value_sources`), so hand-entered/PDF-approved values for the same agency survive;
  ranks (pure derived) scoped by metric×agency; inbound `restatement_of_id` nulled so the FK
  never blocks. `--reset` now prints the per-agency blast radius and **requires `--yes`**
  (`ResetNotConfirmed` + exit 2 otherwise). `_verify` scoped to the feed so the reset invariant
  holds. Help text + managing-data.md + reference-ingest-cli.md + .bat comments corrected. 4 new
  tests in test_bulk_load.py (deletes feed rows, keeps manual_entry, refuses without --yes, dry-run).
- ~~**Workbook re-import republishes every pre-filled cell as `manual_entry`**~~ ✓ **Fixed
  2026-06-11:** `import_workbook` is now diff-aware — `add_record` skips any cell equal to the
  current DB value (new `skipped_unchanged` count) and warns when a typed value would supersede a
  non-`manual_entry` (feed/PDF) source, via the new `Repository.current_value_sources`. Paired
  fix: `promote_approved_bulk` now stamps `reviewer_notes='promoted'` (postgres + in-memory), so
  an `import-xlsx` after `statcan-load` no longer re-promotes/churns the bulk rows. 4 new tests
  (test_workbook.py: unchanged→stages nothing, edited→stages one, feed-overwrite warns;
  test_bulk_load.py: slow promote skips stamped bulk rows).
- **yoy_spike priority is understated** (see "Wire live validation" above): the workbook path
  auto-approves at tier 0 with NO magnitude guard anywhere. Treat the prior_value lookup as a
  pre-launch blocker, not P2.

### P2 — pipeline correctness
- **Extraction notes/source quotes are dropped at staging** — `core.pending_values` has no
  `notes` column, so the auditability data commit 5a7610a built never reaches the reviewer.
  Lane-0 migration + persist in insert_pending_value + carry into metric_values.notes on promote.
- **Bulk vs slow promote idempotency mismatch** — ✓ stamp half **fixed 2026-06-11**
  (`promote_approved_bulk` now stamps `reviewer_notes='promoted'` in both repos, regression test
  in test_bulk_load.py). Remaining (minor): `promote_pending` still doesn't diff, so a manual
  re-approval of an identical pending row would supersede with the same value — low priority now
  that the cross-path re-promotion is closed.
- **Review console has no human approve UI** — approving the 64-PDF financials backlog requires
  curl against the JSON API. Extend `review/console.py` with per-row approve/reject +
  "approve all unflagged from this document".

### P2 — web money-path + pre-launch checklist
- ~~**Checkout return is unhandled**~~ ✓ **Fixed 2026-06-11:** `agency/[slug]/page.tsx` now reads
  `?checkout=` and renders a top `CheckoutBanner` (new `checkout-notice.tsx`): success+active →
  teal "You're a member…"; success+pending (webhook lag) → "Payment received — activating…";
  cancel → quiet "no charge" notice. In the lag window the Financials download slot shows the
  activating notice instead of the stale Subscribe button (`DownloadButton.pendingActivation`).
  State derives only from `getSession()`+`isPaid()`; page stays force-dynamic; viewing un-gated.
  5 unit tests for `checkoutStateFrom`. Full web gate green.
- **Rate-limit the magic-link email endpoint** (Resend spam = cost + sender reputation) before
  public launch — simplest: small in-memory token bucket per email+IP.
- ~~**Anyone can forge `paid`/`checkout_start` funnel events**~~ ✓ **Fixed 2026-06-11:**
  `log-conversion.ts` client enum narrowed to `["gate_view", "wall_hit"]`. The revenue events
  were already emitted server-side (`checkout_start` in billing/checkout.ts; `paid` in the Stripe
  webhook via `recordPaidConversionOnce`), so narrowing drops no real signal — it just rejects
  forgery. New test asserts the client can't post `paid`/`checkout_start`. Full web gate green.
- **Stripe webhook ordering**: on `customer.subscription.*` re-fetch the subscription from
  Stripe instead of trusting the (possibly stale, out-of-order) event payload.
- **Env validation + crash alerting**: a 30-line zod env module (silent fallbacks currently sit
  on the checkout URL path) + Sentry free tier so a failing webhook is visible.

### P3 — UI polish batch (each small)
- Header sign-in/account link (no path to /account exists in the chrome).
- Lapsed-member download → styled renew page, not a raw text 403.
- Branded verify-request/error pages for the magic-link flow (`pages` config in auth.ts).
- /about methodology page backing the footer's trust claims.
- Directory: sort agencies with data first (hasAnyRank already in the payload).
- Dynamic-import Recharts (≈129 kB now in every detail-page load).
- Mobile: hero chart opens up to two cards below the tapped box; phone peek labels still use
  the pre-2026-06-06 metric set (bare number + empty label); sticky first column in financials.

### Timeline
- **Next.js 15 LTS ends 2026-10-21** — schedule the Next 16 upgrade; bundle the drizzle-orm
  0.4x bump into the same session.
- **Auth verdict: KEEP NextAuth v5 beta.31** (Auth.js merged into the Better Auth org 2025-09
  and still gets security maintenance; our usage is its most boring core, wired into money +
  migration 008). Revisit triggers: an unpatched advisory, needing orgs/2FA/passkeys, or a
  forced major rewrite.
