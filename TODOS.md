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

### StatCan agency-code → slug mapping table
- **What:** Map StatCan 23-10-0307 internal agency identifiers to TransitIndex slugs.
- **Why:** The adapter can't write `metric_values` without resolving agencies; unmapped
  rows must be skipped + alerted, not silently dropped.
- **Effort:** S. **Priority:** P1. **Blocks:** StatCan adapter.

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

### Strict period-matched ratios — P2
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

## Architecture (from eng re-review 2026-05-30)
Resolutions captured in phase-plan.md "Architecture — eng re-review" + data-model.md.

### Paywall: account-gate numbers server-side — P1
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

### Derived-recompute step (ratios) — P2
- **What:** Post-promotion step computes period-matched ratios from approved inputs, stores
  as first-class `metric_values`, re-runs on input promote/restate; auto sanity flags.
- **Why:** Pipeline had no derived-compute step; a corrected input could leave a stale ratio.
- **Test (IRON/regression):** corrected input re-runs the ratio, no stale value.

### Incremental recompute — P3
- **What:** Both jobs recompute only the affected metric/period/agency cohort, not full rebuilds.
- **Why:** A monthly StatCan update shouldn't re-rank all 100+ agencies × all metrics.

## Data expansion — balance sheets + native frequency (2026-05-31)
Full plan: [balance-sheet-and-frequency-plan.md](balance-sheet-and-frequency-plan.md). Additive —
**no `db/migrations/` change** (the existing tables absorb it). Build tasks, roughly in order:

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
- **Accounts / watchlist / personal dashboard** (Auth.js).
- **PDF + human-review treadmill** (TTC CEO Report adapter, annual-report adapters,
  OC Transpo scraper, board decks). This is the cost center — do not scale on conviction.
- **US / NTD ingestion** (schema absorbs it with zero change; no build until CA core validated).
- **Bounding-box provenance deep-links** (~2× ingestion cost).

## Open decisions (from README + design doc)
- Legibility vs neutrality (recommend: strictly factual, no editorial grade).
- Everything-paid vs free-public (revisit toward Approach C if conversion is weak).
- DB host: Neon vs Supabase. Restatement display. Provenance granularity (page-level at launch).

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
- **Add auth to the review `/approve` endpoint** (`review/app.py`). It is the only door into
  live `metric_values` and currently has none; localhost-default mitigates but a public bind
  defeats Invariant #1. Require auth on all mutating review endpoints.
- ~~**Reconcile DESIGN.md + the 3 wireframes to the account-gate model.**~~ ✓ **Completed v0.0.1.0 (2026-05-31):** DESIGN.md reconciled — meter language removed, "numbers gated (anonymous)" state added, 2026-05-31 status note recorded.
- ~~**Paywall integrity is UNVERIFIED until `web/` ships**~~ ✓ **Completed v0.0.1.0 (2026-05-31):** `web/` shipped. Paywall enforced via server-only choke point + disjoint types + ESLint import restriction. A1 test structured (skipped until TEST_DATABASE_URL available).
- **Period-comparability in `refresh_ranks`** — currently ranks only agencies in the one
  passed `period_id` (missing agency silently vanishes). Add "resolve latest comparable
  period per metric" + emit explicit "not ranked — latest FYxxxx" rows so the UI can render
  the committed state. Pairs with the N<5 minimum-denominator suppression.

### P2
- **Reconcile the scope-guard contradiction.** Schema DECISION 3 dropped the scope-caveat
  guard, but the plan invariant + Failure Modes T2 still claim it. Either re-introduce a
  UI-rendered scope flag (BC Transit = Victoria, Metrolinx = GO+UP) in `metric_values.notes`,
  or delete the invariant/T2 claim. As-is, BC Transit (Victoria-only) ranks vs TTC whole-system.
- **Wire live validation into the real path.** `staging._default_validator` passes
  `prior_value=None` (YoY flag can never fire); the PDF path passes `validator=None`. Wire
  `prior_value` + `validate_cohort` into `stage_records`; pass the real validator into
  `run_pdf`; auto-flag PDF↔StatCan disagreement. Otherwise "20 reviews/agency not 200" is unbacked.
- **Postgres-backed CI test.** All 135 tests run on `InMemoryRepository` (which reimplements
  the invariants in Python). Add a CI job that applies `db/migrations`, runs `db/tests/*.sql`,
  and round-trips `PostgresRepository` so the real `one_current_value` index / audit trigger /
  grants are actually exercised.
- **Replace the synthetic gold fixture with REAL values.** `ttc_annual_2024.json` reads as
  made-up round numbers; the eval grades against it. Seed it from real TTC 2024 figures
  (and an Edmonton cross-check) — see `foi-sourcing-plan.md` "Start here". Add the design
  states (error, gated-anon, N<5) flagged in the design re-review.
