# TransitIndex — Metric-Set Build Plan

**Version:** 1.1 | **Status:** Phase 1 built (commit `6142e19`); Phases 2–7 + the v1.1 addendum
ready to implement (2026-07-01) | **Rationale:**
[metric-standards-review.md](metric-standards-review.md) (read it for the *why*; this doc is the
*how*).

This implements the 2026-06-14 decisions: **rate only the five hero metrics**, **pin the operating
boundaries**, **add the financial-statement metrics**, and **drop the weighted fleet metric in
favour of a four-class composition**. Phases are ordered smallest-and-safest first, so each can land
and be verified on its own.

> **The parity guardrail (read first).** The metric set has *three* mirrors kept in lock-step by
> tests: `ingest/transitindex_ingest/refdata.py` `METRICS` ↔ `db/seeds/04_metrics.sql` ↔
> `ingest/transitindex_ingest/metric_dictionary.yaml`. **Every add/remove must touch all three in
> the same commit**, plus a gold fixture and the web placement map. The full sync checklist lives in
> [../design/detail-view-metrics.md](../design/detail-view-metrics.md) §10. After any change, run
> `python -m transitindex_ingest.dictionary` to regenerate `docs/reference/data-dictionary.md`.

**Decisions implemented here** (canonical list in the review's "Decisions taken" block):
- Rated set = **5 hero boxes**: `ridership`, `total_revenue_excluding_subsidy`, `on_time_performance`,
  `cost_per_rider`, `subsidy_per_rider`. Everything else view-only.
- `operating_expenses` pinned to **amortization-excluded** basis + a new structured `cost_basis`.
- `total_revenue_excluding_subsidy` (formerly `operating_revenue`, renamed) = **all revenue except
  subsidy** — the StatCan line; the old "earned only" pin is superseded (see the revenue decision below).
- **Revenue section = five lines (2026-06-14, user — final).** Show: **Farebox revenue**
  (`farebox_revenue`) + **Other revenue** (`other_revenue`, the broad non-fare/non-subsidy
  catch-all) = **Total revenue excluding subsidy** (`total_revenue_excluding_subsidy` ★); then **+ Subsidy**
  (`subsidy`) **= Total revenue** (`total_revenue`). Ties out with **no residual**:
  `total_revenue_excluding_subsidy` is *defined* as `total_revenue − subsidy`, which is exactly the
  StatCan 23-10-0307 line ("Total revenue, excluding subsidies") — so the StatCan mapping becomes
  definitionally exact.
- **Definitional shift (supersedes the earlier "earned only" pin).** The earned subtotal now means
  "all revenue except subsidy" — a touch broader than strict operating (it sweeps ancillary + any
  capital/investment revenue into the earned side). **Therefore `farebox_recovery_ratio` and
  `average_fare` use `farebox_revenue` as the numerator, not this broad subtotal**, or they
  inflate for capital-heavy agencies (standards-review landmine 1). `other_operating_revenue` is no
  longer needed — dropped.
- **Add:** `amortization`, `other_operating_expenses`, `annual_surplus_deficit`, `total_revenue`,
  `total_expenses`, `farebox_revenue` (promote to core), `other_revenue` (broad non-fare/
  non-subsidy residual). ~~`asset_consumption_ratio` + its two inputs~~ — deferred 2026-07-01
  (addendum #3). Definition: `total_revenue_excluding_subsidy = total_revenue − subsidy`.
- **Drop:** `fleet_capacity` + `MODE_CAPACITY_WEIGHT`; replace with a 4-class fleet composition.
- **Naming — codes match the statement line (2026-06-14, user).** Revenue metrics are *renamed* to
  read like their displayed lines: `passenger_fare_revenue` → **`farebox_revenue`**;
  `operating_revenue` → **`total_revenue_excluding_subsidy`** (= the StatCan 23-10-0307 measure label
  verbatim); `total_operating_subsidy` → **`subsidy`**. `other_revenue` / `total_revenue` already
  match. These are **live codes**, so the rename adds a DB migration (rename in `core.metrics` +
  `metric_values` + `pending_values`), the StatCan adapter `_MEASURE_TO_METRIC`, `RATED_METRICS`, the
  derived ratios, web, and tests — all in the parity commit.

**Still open (does not block the rest):**
- **OTP rank badge** — keep the rank with a "definitions vary" footnote, *or* drop just OTP's badge
  (rated set → 4). Phase 1 keeps OTP rated; the badge/footnote is a web-only toggle (Phase 7).
- ~~**`asset_consumption_ratio`** needs two new sourced inputs~~ — **resolved 2026-07-01: DEFER**
  (addendum #3 below — the inputs are too rarely reported to be worth tracking).

---

## Addendum v1.1 — decisions added 2026-07-01 (user)

These extend the 2026-06-14 decisions; where they touch a phase, the delta is listed at the end.

1. **Entity scope = company-wide (whole organization) for every financial metric.** Settled after
   the scope argument: every financial-statement metric — all revenue lines, all expense lines,
   `subsidy`, and the whole balance-sheet family — is the figure for the **entire reporting
   organization** (conventional + specialized/paratransit + every business line), taken from the
   audited financial statements. **Never** a transit-segment, conventional-only, or single-division
   carve-out. Two boundary cases, stated so the extractor cannot misread them:
   - *Multi-division agencies* (TransLink incl. roads/bridges, Metrolinx incl. GO + UP + PRESTO):
     use the audited entity totals — no segment carve-outs.
   - *Transit as a city division* (Calgary Transit, Edmonton ETS, Hamilton HSR): "company-wide"
     means the **transit division's own schedule/segment** inside the city's statements — never the
     municipality-wide totals (the extractor already drops `city_wide` values; keep that filter).
   Service metrics (`ridership`, hours, km, OTP, fleet) keep the `service_scope` dimension exactly
   as-is. *Implementation:* an entity-scope sentence in every financial metric's dictionary entry,
   and extractor guidance that financial lines carry `service_scope="total"`.

2. **The statements must balance — add the balance-sheet residuals.** `assets = liabilities +
   equity` must close at every level of the tracked set, the same way the expense side closes.
   Today `cash_and_investments ⊂ total_financial_assets`, `long_term_debt ⊂ total_liabilities`,
   and `tangible_capital_assets ⊂ total_non_financial_assets` have no residuals, so components
   cannot sum to their totals. **Add three derived residuals** (same pattern as `other_revenue`):
   - `other_financial_assets` = `total_financial_assets − cash_and_investments`
   - `other_liabilities` = `total_liabilities − long_term_debt`
   - `other_non_financial_assets` = `total_non_financial_assets − tangible_capital_assets`
   Each gets a SumEquation with `defines=` the residual, and Phase 5 gains the three component
   identities. The plan's component-*bounds* checks are subsumed by these equalities (a residual
   solving negative IS the bound violation — flag it), but keep the bounds as cheap standalone
   checks where both sides are sourced.

3. **Amortization only — the rest of the family is deferred** (the "depreciation" decision,
   trimmed 2026-07-01, user): only `amortization` (the annual expense line, printed on every
   statement of operations) ships. `accumulated_amortization`, `gross_tangible_capital_assets`,
   and `asset_consumption_ratio` are **deferred**: they live in the TCA note detail that many
   agencies don't report cleanly, and there is no point building detail that data will rarely
   hit. The Phase-4 decision gate is resolved: DEFER (documented, not silently dropped).

4. **Subsidy stays ONE line; a component is never the total.** Keep `subsidy` as the single
   combined government **operating** funding line (the fed/prov/municipal split was already
   rejected 2026-06-14 — reported too inconsistently to split). The extraction rule to encode:
   a line naming a single level of government or a single program ("federal gas tax",
   "provincial operating grant", "municipal contribution") is a **component** — record `subsidy`
   only from a line that is the combined total (or leave it for the identity to solve); **never
   promote one level or one program to the total.**

5. **Extraction-grade definition pass over every metric — but keep it lean (2026-07-01, user).**
   Every `metric_dictionary.yaml` entry is tightened so the LLM extractor makes the fewest
   possible mistakes — clarity about what a number IS, not more numbers to hunt for. Do not add
   metrics or sub-breakdowns whose data rarely appears in real reports. Each entry must state:
   (a) the **entity scope** line from #1 (financial metrics);
   (b) an explicit **component-vs-total** confusion (the federal-subsidy mistake, generalized:
       `long_term_debt` vs `total_liabilities`, `cash_and_investments` vs `total_financial_assets`,
       `farebox_revenue` vs `total_revenue_excluding_subsidy`, one expense object vs
       `operating_expenses`, …);
   (c) **scale/unit guidance** — statements print $000s or $M; the recorded value is whole CAD;
   (d) **sign conventions** where they exist (`annual_surplus_deficit` negative = deficit;
       `net_debt` negative = net financial assets);
   (e) the **cost_basis / amortization** note on every expense line (Phase 3).
   `dictionary.extraction_guidance()` then carries all of it into the `pdf/llm.py` prompts —
   the extractor prompt is regenerated, not hand-edited (per the locked rule: the extractor is
   always updated when the metric set changes).

**Phase deltas from this addendum:**
- **Phase 4** gains the three balance-sheet residuals (table updated in place below); the
  asset-consumption gate is resolved to **defer** (its ratio + two inputs do not ship). Final
  set: 32 − 1 (`fleet_capacity`) + 10 additions = **41 metrics**.
- **Phase 5** gains three component identities (`financial_assets_components`,
  `liabilities_components`, `non_financial_assets_components`).
- **Phase 2/7** dictionary work expands to the full definition pass (#1, #4, #5).
- **Migration numbering:** `017_reconcile_primary_modes.sql` already exists — this plan's
  migrations start at **018**.

---

## Phase 0 — Pre-flight

1. Branch off the current working branch (`pdf-review-console-and-load`) or a fresh one from
   `master`; do not work on `master`.
2. Baseline green: `cd ingest && python -m pytest` (the suite is offline/stdlib). Record the count
   so regressions are visible.
3. Confirm the three mirrors currently agree (the parity tests pass) before touching anything.

---

## Phase 1 — Ranking: rate only the five hero metrics  *(smallest, highest-value, low-risk)*

**Goal:** only `ridership`, `total_revenue_excluding_subsidy`, `on_time_performance`, `cost_per_rider`,
`subsidy_per_rider` carry ranks. This retires the two balance-sheet ranked ratios and never ranks
any other size figure.

**Today:** `comparable_flag = code not in NON_RANKABLE_METRICS` (set in `jobs/derived_recompute.py`
~L128 and `workbook.py` ~L670), and `NON_RANKABLE_METRICS` only lists the 9 balance-sheet dollars.
`jobs/rank_refresh.compute_ranks` ranks any value with `comparable_flag=True` whose `service_scope`
matches; callers pass a `rank_metric_codes` list (`jobs/bulk_load.py`: StatCan
`["ridership","total_revenue_excluding_subsidy"]`, Hamilton `["ridership"]`).

**Change — drive everything off a positive allow-list:**
1. `refdata.py`: add
   ```python
   RATED_METRICS: frozenset[str] = frozenset({
       "ridership", "total_revenue_excluding_subsidy", "on_time_performance",
       "cost_per_rider", "subsidy_per_rider",
   })
   ```
   Keep `NON_RANKABLE_METRICS` for now (other code reads it) but it is superseded by `RATED_METRICS`
   for the comparable_flag decision; add a comment that `RATED_METRICS` is the source of truth.
2. `jobs/derived_recompute.py` and `workbook.py`: change `comparable_flag=code not in
   NON_RANKABLE_METRICS` → `comparable_flag=code in RATED_METRICS`.
3. `jobs/rank_refresh.py`: at the top of `refresh_ranks` / `bulk_refresh_ranks`, skip any
   `metric_code not in RATED_METRICS` (belt-and-suspenders so a stray caller can't rank a non-rated
   metric). Leave the `comparable_flag` + `service_scope` filter as-is.
4. Audit every adapter that builds `MetricValueRecord` (statcan_307, hamilton_hsr, the PDF promotion
   path, manual/workbook import): ensure `comparable_flag` is set from `RATED_METRICS`, not hand-set
   to `True`. The five rated codes all come through these paths, so this is where it bites.

**Verify:**
- `tests/test_rank_refresh.py`: update expectations — only the five codes produce rank rows; OTP
  still ranks; `debt_to_assets`/`net_debt_per_capita`/`operating_expenses`/etc. produce none.
- Add a test asserting `compute_ranks`/`refresh_ranks` is a no-op for a non-rated metric.
- `web`: the detail page rank badges already key off the directory-card metrics
  (detail-view-metrics.md §3.1 `agency-card.tsx` `METRIC_SLOTS`) — confirm fleet (Phase 6) is the
  only hero that changes.

---

## Phase 2 — revenue boundaries (dictionary only, no schema)

**Goal (revised 2026-06-14, Decision #4):** `total_revenue_excluding_subsidy` is *defined* as `total_revenue −
subsidy` — i.e. **"total revenue excluding subsidy"**, exactly the StatCan
23-10-0307 line. This **supersedes the earlier strict "earned only" pin**: ancillary, capital, and
investment revenue now sit *inside* this line; only **subsidy** is excluded. The rider-share ratios
(`farebox_recovery_ratio`, `average_fare`) use `farebox_revenue`, so the breadth of this line
never reaches them.

1. `metric_dictionary.yaml` → `total_revenue_excluding_subsidy`: define as all revenue **except** government
   operating subsidy/transfers; note it equals `total_revenue − subsidy`. Pin the
   split on the **subsidy** side: `subsidy` is government **operating** funding;
   **third-party fare-program reimbursements (One Fare, U-Pass) are subsidy, not farebox** — they
   reduce `farebox_revenue`, not `total_revenue_excluding_subsidy`. Add a `confusions` line on One Fare.
2. `metric_dictionary.yaml` → `farebox_revenue`: passenger fares only (the rider-share
   numerator); excludes ancillary income, subsidy, and program reimbursements.
3. Regenerate the dictionary (`python -m transitindex_ingest.dictionary`); this also refreshes the
   PDF extractor guidance (`dictionary.extraction_guidance()` feeds `pdf/llm.py`).

**Verify:** parity test still green (no structural change); diff `data-dictionary.md` shows the
`total_revenue_excluding_subsidy` + `farebox_revenue` sections changed.

---

## Phase 3 — `cost_basis` dimension for `operating_expenses` *(the load-bearing fix)*

**Goal:** an amortization-excluded ("operating") expense is never ranked-derived against an
amortization-included ("psab_total") one. Note: `pdf/llm.py` already has a `basis` field, but it
means actual/budget/forecast/restated — this is a *different* axis; name it `cost_basis`.

1. **Contract** (`ingest/transitindex_ingest/contract.py`): add
   `CostBasis = Literal["operating", "psab_total"]` + `COST_BASES` frozenset; add field
   `cost_basis: CostBasis = "operating"` to `MetricValueRecord`; validate in `__post_init__`.
2. **Schema migration** (next number, `db/migrations/018+_*.sql` (017 is taken)): add `cost_basis text` (default
   `'operating'`, CHECK in the enum) to `core.metric_values` and `core.pending_values`; backfill
   existing rows to `'operating'`. Mirror in `web/src/db/schema/core.ts`.
3. **Repository / models** (`db/repository.py`, `db/postgres.py`, `db/memory.py`, `db/models.py`):
   carry `cost_basis` through insert/promote/read.
4. **Derived ratios** (`jobs/derived_recompute.py`): when computing `farebox_recovery_ratio`,
   `cost_per_rider`, `cost_per_hour`, `subsidy_per_rider`, **use the `operating`-basis
   `operating_expenses`**. **Numerator note (Decision #4):** `farebox_recovery_ratio` and
   `average_fare` take `farebox_revenue` as the numerator — *not* the broad `total_revenue_excluding_subsidy`
   (= `total_revenue − subsidy`), which would inflate them for capital-heavy agencies. If only a `psab_total` expense exists for the cohort, either (a) derive
   `operating = psab_total − amortization` when `amortization` is present (preferred — see Phase 4),
   or (b) compute the ratio but set `comparable_flag=False` and add a flag. Document which.
5. **Extractor** (`pdf/llm.py`): add `cost_basis` to the tool-row schema for expense lines and
   prompt the model to read "(excludes amortization)" vs a PSAB statement-of-operations total.

**Verify:** `tests/test_contract.py` (new field + validation); `tests/test_derived_recompute.py`
(ratios pick the operating-basis input; mixed-basis cohort behaves per the chosen rule);
`tests/test_balance_sheet.py` unaffected.

---

## Phase 4 — Add the financial-statement metrics

All new metrics are **non-rated** (not in `RATED_METRICS`). For each: add to `refdata.METRICS` +
`db/seeds/04_metrics.sql` (parity) + a `metric_dictionary.yaml` entry + a gold fixture (Phase 7).
A `db/migrations/018+_*.sql` (017 is taken) (or a sibling) INSERTs the new metric rows into `core.metrics` for
existing DBs (follow migration 014's balance-sheet pattern).

| New metric | unit / type | derived | role |
|---|---|---|---|
| `amortization` | CAD / currency | f | reconciles expense components; lets `operating = psab_total − amortization` |
| `other_operating_expenses` | CAD / currency | f | residual so components sum |
| `total_revenue` | CAD / currency | f | enterprise lens (PSAB statement-of-operations total); top of the revenue block |
| `farebox_revenue` | CAD / currency | f | "Farebox revenue" — passenger fares only; the farebox-recovery / average-fare numerator (promoted from optional D.4) |
| `other_revenue` | CAD / currency | **t** | broad non-fare/non-subsidy residual: `total_revenue_excluding_subsidy − farebox_revenue` |
| `total_expenses` | CAD / currency | f | enterprise lens |
| `annual_surplus_deficit` | CAD / currency | **t** | `total_revenue − total_expenses`; flow→stock bridge |
| `other_financial_assets` | CAD / currency | **t** | residual: `total_financial_assets − cash_and_investments` (addendum #2) |
| `other_liabilities` | CAD / currency | **t** | residual: `total_liabilities − long_term_debt` (addendum #2) |
| `other_non_financial_assets` | CAD / currency | **t** | residual: `total_non_financial_assets − tangible_capital_assets` (addendum #2) |

**equations.py:**
- **Update `expense_components`** SumEquation: terms become `labour_cost + energy_fuel_cost +
  materials_services_cost + amortization + other_operating_expenses = operating_expenses`. (This is
  the PSAB-total basis; the operating basis is that minus `amortization`.)
- **Add** `earned_revenue_components` SumEquation: `farebox_revenue + other_revenue =
  total_revenue_excluding_subsidy`, `defines="other_revenue"` (farebox is sourced from the PDF; `total_revenue_excluding_subsidy`
  = "total revenue excluding subsidy" is sourced directly by StatCan; `other_revenue` is the broad
  residual).
- **Add** `total_revenue_def` SumEquation: `total_revenue_excluding_subsidy + subsidy =
  total_revenue` (ties out by construction — `total_revenue_excluding_subsidy` is *defined* as `total_revenue −
  subsidy`, so no residual term; when all three are sourced this is a cross-source check, not a plug).
- **Add** `annual_surplus_deficit_def` SumEquation: `annual_surplus_deficit = total_revenue −
  total_expenses`, `defines="annual_surplus_deficit"`.
- **Add the three balance-sheet component equations (addendum #2)**, each `defines=` its residual:
  `financial_assets_components` (`cash_and_investments + other_financial_assets =
  total_financial_assets`), `liabilities_components` (`long_term_debt + other_liabilities =
  total_liabilities`), `non_financial_assets_components` (`tangible_capital_assets +
  other_non_financial_assets = total_non_financial_assets`).
- **Cross-period roll-forward** `accumulated_surplus(end) = accumulated_surplus(start) +
  annual_surplus_deficit` is *not* a within-period SUM/RATIO — handle like `PERIOD_ROLLUP`
  (a reserved derivation code / a separate check), not a member of `EQUATIONS`. Out of scope for the
  solver; add as a documented cross-period validation later.

**Decision gate — resolved 2026-07-01: DEFERRED.** `asset_consumption_ratio` and its two inputs
(`accumulated_amortization`, `gross_tangible_capital_assets`) do **not** ship — the user's call:
the TCA-note detail is too rarely reported for the tracked agencies to be worth building against.
Ship the other additions. Revisit only if the data proves reliably available.

---

## Phase 5 — Identity enforcement in `validation/flags.py`

**Goal:** make the enforced identities actually closeable, and add the checks the balance-sheet plan
promised but never implemented.

1. **`sum_mismatch` Identity 1** (`flags.py` `sum_mismatch`): change the `components` tuple to
   `("labour_cost","energy_fuel_cost","materials_services_cost","amortization",
   "other_operating_expenses")` so it sums to `operating_expenses` (PSAB basis). Only fire when all
   present (existing behaviour). This stops the false flags / mis-bucketing called out in Part B.
2. **Subsidy identity** (Identity 2): keep, but it is exact only when the annual result is ~0. With
   `annual_surplus_deficit` available, prefer checking
   `total_revenue − total_expenses ≈ annual_surplus_deficit` and treat the subsidy≈expenses−revenue
   check as informational (or widen its tolerance). Document the change.
3. **Add the net-debt identity** to `validate_cohort`: `net_debt ≈ total_liabilities −
   total_financial_assets` → `sum_mismatch` (the plan §2 claims it; today it's only in the
   `equations.py` solver cross-check).
4. **Add component-bounds** (plan §2): `cash_and_investments ≤ total_financial_assets`,
   `long_term_debt ≤ total_liabilities`, `tangible_capital_assets ≤ total_non_financial_assets`
   → `sum_mismatch`.
5. **Add the three balance-sheet component identities (addendum #2)** to `validate_cohort`:
   `cash_and_investments + other_financial_assets ≈ total_financial_assets`,
   `long_term_debt + other_liabilities ≈ total_liabilities`, `tangible_capital_assets +
   other_non_financial_assets ≈ total_non_financial_assets` → `sum_mismatch` (fire only when all
   terms present, matching the expense-components behaviour).

**Verify:** `tests/test_validation.py` + `tests/test_balance_sheet.py`: a clean PSAB statement with
all five expense objects no longer flags; a broken one does; the new bounds fire.

---

## Phase 6 — Drop `fleet_capacity`; ship the 4-class fleet composition

**Remove:**
1. `refdata.py`: delete the `fleet_capacity` entry from `METRICS` and delete `MODE_CAPACITY_WEIGHT`.
2. `db/seeds/04_metrics.sql`: delete the `fleet_capacity` row (parity).
3. `metric_dictionary.yaml`: delete the `fleet_capacity` entry (parity).
4. Delete `jobs/fleet_capacity_aggregate.py` and the `MODE_WEIGHTED_FLEET` constant in
   `equations.py`; remove its imports/uses (`tests/test_fleet_capacity.py` is removed too).
5. `db/migrations/018+_*.sql` (017 is taken) (or sibling): delete `fleet_capacity` metric rows + its
   `metric_values`/`pending_values`; drop the `mode_capacity_weight` column (revert migration 015).

**Add the composition (display grouping of existing per-mode `fleet_size`):**
6. `refdata.py`: add a `FLEET_CLASS` map mode→class:
   `bus,brt,trolleybus → "bus"`; `light_rail,streetcar → "light_rail"`; `subway → "heavy_rail"`;
   `commuter_rail → "commuter_rail"`; `ferry,paratransit,on_demand → excluded`.
7. `metric_dictionary.yaml` → `fleet_size`: change the rail-counting guidance from "count cars
   unless trainsets" to **"count trains for rail; one bus = one vehicle"** (the user's call), and
   note the four display classes. ⚠️ **Data caveat:** any existing per-mode `fleet_size` rail values
   entered as *cars* must be re-checked/re-entered as *trains* — flag this for the data load, do not
   silently reinterpret.
8. **Web** (`web/src/server/metrics/detail-model.ts` + `agency-card.tsx` `METRIC_SLOTS`):
   - remove `fleet_capacity` from the hero/`METRIC_SLOTS` set (6 → 5 boxes; leave at five or fill
     the slot — a layout call);
   - render the fleet composition as four labelled counts (Bus · Light rail · Heavy rail · Commuter
     rail) from per-mode `fleet_size`, **not ranked**;
   - update `detail-view-metrics.md` §2 map (drop fleet_capacity row; add the composition) and §3.1.

**Verify:** parity tests green after the 3-mirror delete; `tests/test_fleet_capacity.py` removed; a
detail-model test renders the 4 classes; the directory card shows 5 heroes.

---

## Phase 7 — Extractor, fixtures, OTP badge, docs

1. **Extractor** (`pdf/llm.py`): the tool `metric_code` enum auto-syncs from `METRICS` (locked by
   test) — no manual enum edit. Confirm: `fleet_capacity` disappears; the six new codes appear;
   `cost_basis` (Phase 3) and the One Fare guidance (Phase 2) are in the prompt via the regenerated
   dictionary.
2. **Gold fixtures** (`eval/gold.py`, `tests/fixtures/gold/`): add a fixture row per new metric
   (recommend TransLink for the clean PSAB statement, per the balance-sheet plan §6); remove
   `fleet_capacity` fixtures; add a `should_flag` case for a now-closeable expense-components
   identity.
3. **OTP badge (open sub-decision):** implement the chosen option — either keep OTP's rank badge and
   add a "definitions vary by agency" footnote on the detail page, or drop just OTP's badge (then
   also remove `on_time_performance` from `RATED_METRICS` in Phase 1, taking the rated set to 4).
   Either way, record each agency's on-time window in a structured field (a new
   `agencies`/value-level attribute), not free-text notes.
4. **Docs:** regenerate `data-dictionary.md`; bump `docs/STATUS.md`; add superseding pointers in
   `balance-sheet-and-frequency-plan.md` (its two ranked balance-sheet ratios are retired) and
   `detail-view-metrics.md` (fleet hero replaced).

---

## Suggested commit sequence

1. Phase 1 (ranking) — self-contained, shippable alone.
2. Phase 2 (total_revenue_excluding_subsidy dictionary) — trivial, shippable alone.
3. Phase 4 + 5 (additions + identities) — together, since the identity needs the new metrics.
4. Phase 3 (cost_basis) — after the additions, since the operating-basis derivation uses
   `amortization`.
5. Phase 6 (fleet) — independent of 2–5; can go any time after Phase 1.
6. Phase 7 (extractor/fixtures/OTP/docs) — last, after the set is final.

Each commit: run `cd ingest && python -m pytest` and `python -m transitindex_ingest.dictionary`
before committing; keep the three mirrors in parity in the same commit.
