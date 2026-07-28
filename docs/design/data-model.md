# TransitIndex — Data Model
**Version:** 0.2 | **Status:** Shipped — every entity below exists in `db/schema.sql` + `db/migrations/`

Reflects current decisions: **one flat metric layer**, **typology dropped (2026-05-30)**, **everything paid**. The schema below is database-agnostic but assumes PostgreSQL 16.

> **Why this shape:** Canadian transit agencies are wildly heterogeneous (TTC subway vs a small-town bus). The model makes them comparable via universal metrics in one flat table, stores mode-specific metrics in the same table (distinguished by `applicable_modes`), and uses each agency's modes + `service_area_population` to surface apples-to-oranges in the compare view. Time-series, restatements, and provenance are first-class.

---

## Core entities

### `agencies` — one row per operator
- `id`, `slug` (e.g. `ttc`, `stm`), `legal_name`, `short_name`
- `country`, `subdivision` (province/state), `service_area_population`
- `primary_modes` (denormalized array of mode codes, for fast filtering)
- `fiscal_year_end_month` (1–12) — handles non-calendar fiscal years (Metrolinx & BC Transit = 3/March)
- `currency` (default CAD)
- `parent_agency_id` (nullable FK self) — e.g. BC Transit → its community systems later

### `modes` — reference table
- `code`: `bus`, `subway`, `light_rail`, `commuter_rail`, `streetcar`, `brt`, `trolleybus`, `ferry`, `paratransit`, `on_demand`
- `display_name`, `description`

### `agency_modes` — M2M
- `agency_id`, `mode_id`, `year_started`, `status` (active/planned/discontinued)

### `metrics` — metric *definitions* (not values)
- `code` (e.g. `annual_ridership`, `farebox_recovery_ratio`, `subway_stations`)
- `display_name`, `description`, `unit`, `unit_type` (count | ratio | currency | time | distance)
- `applicable_modes` (NULL = system-wide/universal; array = mode-specific) — **this replaces the old three-layer enum. Flat.**
- `is_derived` (bool) + `formula` (text, nullable) — e.g. farebox recovery = revenue/expenses
- `higher_is_better` (bool, nullable for context-dependent)
- `cuta_reference` (CUTA definition line, for internal consistency only — not shown publicly)
- `ntd_reference` (NTD field mapping, for future US data)

### `reporting_periods` — every metric value belongs to one
- `agency_id`
- `period_type` enum: `monthly | quarterly | annual_calendar | annual_fiscal | ytd`
- `start_date`, `end_date` (the real dates — NOT just a year label)
- `label` (display string: `"2024"`, `"FY2024-25"`, `"2024-Q3"`, `"Mar 2026"`)
- Unique on (`agency_id`, `period_type`, `start_date`)
- **Load-bearing:** one agency can have monthly ridership AND quarterly expenses AND annual fleet live simultaneously (e.g. TransLink). Period type is per-value, not per-agency.

### `metric_values` — the heart of the system
- `agency_id`, `metric_id`, `reporting_period_id`
- `mode_id` (nullable; NULL = system-wide)
- `service_scope` enum: `conventional | specialized | total | system_wide` — **CUTA splits these; they are NOT summable. Never double-count.**
- `value` (numeric)
- `unit` (denormalized — guards against metric-definition drift over time)
- `currency` (nullable)
- `quality` enum: `verified | preliminary | estimated | imputed`
- `comparable_flag` (bool) — is this value safe for cross-agency comparison? (At launch: true for StatCan-derived; refined manually over time.)
- `restatement_of_id` (nullable FK self) — chain of revisions
- `is_current` (bool) — exactly ONE current value per (agency, metric, period, mode, scope) tuple
- `notes` (free text for caveats)
- `created_at`, `updated_at`

### `source_documents` — provenance roots
- `agency_id`
- `document_type` enum: `annual_report | quarterly_update | budget | ceo_report | board_report | statcan_table | open_data_csv | gtfs | manual_entry | press_release`
- `title`, `publication_date`, `source_url`, `local_storage_path`, `file_hash`
- `license` (e.g. `statcan_open` | `ogl_toronto` | `public_document` | …) — drives the required attribution text
- `retrieved_at`, `verified_at`, `verified_by`

### `metric_value_sources` — links each value to its source(s)
- `metric_value_id`, `source_document_id`
- `page_number`, `table_reference` (e.g. `"Table 4.2"`)
- `extraction_method` enum: `manual | llm_assisted | structured_import | statcan_passthrough`
- `confidence` (0–1)
- *(Future option: `bounding_box` JSON for PDF deep-link highlighting — deferred, ~2× ingestion cost)*

### `metric_value_audit` — append-only change log
- `metric_value_id`, `changed_at`, `changed_by`, `change_type`, `old_value`, `new_value`, `reason`

---

## Ingestion staging (separate from live data)

### `pending_values` — staging before human review
Same shape as `metric_values` plus:
- `review_status` enum: `pending | approved | rejected | needs_edit`
- `flags` (array): `yoy_spike | cross_source_disagreement | unit_mismatch | sum_mismatch`
- `reviewer_notes`
On approval → promoted to `metric_values` + `metric_value_sources` written. Tier-0 sources (StatCan, open data) auto-approve; Tier-2 (PDFs) require human review.

---

## Accounts (Phase 3 — everything paid)

Simplified by the "everything paid" decision — no free/Pro feature matrix.

### `users`
- `id`, `email`, `auth_provider`, `created_at`
- `subscription_status` enum: `active | inactive | trialing | past_due`
- `subscription_source` (stripe id, nullable — can be stubbed pre-payment)

### `watchlists`
- `user_id`, `agency_id`, `created_at` — starred agencies → personal dashboard

---

## Key design guarantees

- **Heterogeneity:** universal vs mode-specific is just `metrics.applicable_modes` (NULL vs array). New mode-specific metric = INSERT, not migration.
- **No double-counting:** `service_scope` keeps conventional/specialized/total as distinct, individually addressable rows.
- **Mixed frequency per agency:** `reporting_periods.period_type` is per-value. TransLink can have monthly + quarterly + annual values coexisting.
- **Fiscal years:** real start/end dates + `fiscal_year_end_month`. Charts align by fiscal year (default) or recompute to calendar.
- **Restatements:** `restatement_of_id` chains revisions; `is_current` flags the live value.
- **Provenance:** every value → `metric_value_sources` → `source_documents` (doc + page + license). Nothing renders publicly without it.
- **NTD-ready:** universal metrics carry `ntd_reference`; US data ingests into the same `metric_values` table later.

---

## Computed layer (eng re-review 2026-05-30)

The web app is a pure reader; ranks and derived ratios are computed in the data layer
(not at request time) and read like any other value.

### `metric_ranks` — materialized ranks (read-heavy, write-rare)
- `agency_id`, `metric_id`, `reporting_period_id` (the period bucket the rank is computed in)
- `comparison_set` enum: `all | subdivision` — `all` is the free default; `subdivision` (province) backs the paid re-rank (typology dropped 2026-05-30)
- `rank` (int), `denominator` (int, the N in "rank of N")
- `direction` (from `metrics.higher_is_better`; null = neutral, no good/bad framing)
- `computed_at`
- **Period-comparability rule:** rank within the latest period bucket where enough agencies
  have `comparable_flag = true` values at a matching `service_scope`. An agency missing that
  period is **not ranked** for it (UI shows "not ranked — latest FYxxxx"), never ranked across
  years. Refreshed when a `metric_values` row is promoted or restated; refresh is **incremental**
  (only the affected metric/period/comparison_set cohort).

### Derived-value computation (post-promotion)
- Derived metrics (`metrics.is_derived = true`) are computed by a recompute step that runs
  **after** inputs are promoted to `metric_values`, NOT through `pending_values` (it's math on
  already-reviewed numbers).
- **Strict period-match:** a ratio is computed only from inputs sharing a `reporting_period`,
  and the result is stored as a `metric_values` row at that shared period (annual for
  expense-based ratios). Never mix periods (e.g. FY2024 expenses ÷ 2025 ridership).
- Re-runs on input promote/restate (invariant #5) so a corrected input never leaves a stale
  ratio. Automated sanity flags (farebox > 100%, negative cost) surface like other validation flags.
- **Estimate mode (opt-in, ephemeral):** a user toggle recomputes ratios on-demand from the
  latest available inputs (mixed periods allowed), clearly labeled "estimate". These are NOT
  stored in `metric_values`, NOT entered into `metric_ranks`, and carry no trend (single point,
  computed at click time). The strict period-matched stored value stays the default and the
  only ranked / dispute-proof number.

## Balance-sheet metric family + carry-forward (2026-05-31)

Added by the balance-sheet-and-frequency plan (retired to git history). **No table
migration** — these live in `metric_values` like every other metric. The catalog grows **20 → 31**.

- **8 sourced balance-sheet line items** (PSAB / PS 1201 statement of financial position):
  `total_financial_assets`, `total_liabilities`, `total_non_financial_assets`, `total_assets`,
  `tangible_capital_assets`, `accumulated_surplus`, `long_term_debt`, `cash_and_investments`.
  All `CAD` / currency, `mode_id` NULL, `service_scope='total'`, native cadence **annual**
  (`quarterly` for TransLink only).
- **3 derived:** `net_debt` (= `total_liabilities − total_financial_assets`; printed value rides
  in `crosscheck_value`), `debt_to_assets`, `net_debt_per_capita` (= `net_debt` ÷ static
  `agencies.service_area_population`).
- **Ranking:** raw balance-sheet dollars carry **`comparable_flag = false`** (they measure size,
  not performance) — never ranked. Only the two scale-free ratios `debt_to_assets` and
  `net_debt_per_capita` are ranked, via the existing `metric_ranks` materialization.
- **Cross-checks** (PSAB identities) fire the existing flags — `sum_mismatch` for the asset
  split / net-debt identity / component bounds, `cross_source_disagreement` for printed-vs-computed
  net debt, `unit_mismatch` for order-of-magnitude. 2% relative tolerance + absolute floor.

### Carry-forward & frequency rule (load-bearing, applies DB + Excel + website)

**Store only observed values, at each metric's native cadence, with their true period. NEVER
store a carried-forward value** — no fabricated rows, no `imputed` row used to show an old number.
`quality='imputed'` keeps its original meaning (a *stored* row a source genuinely estimated) and
is **not** repurposed for carry-forward. A missing period is a real blank (no row).
**Carry-forward is DISPLAY-ONLY:** the website shows the latest known value forward, labelled "as
of FY2024 · carried forward" with the amber stale-feed state; trend charts show a **gap**, never a
flat carried segment or interpolation. Carried-forward values are never ranked and never charted.

## Open schema questions (see CLAUDE.md)
- Restatement display (latest+badge recommended)
- Provenance granularity (page-level at launch; bounding boxes deferred)
- `comparable_flag` assignment policy (source-trust at launch, manual refinement later)
