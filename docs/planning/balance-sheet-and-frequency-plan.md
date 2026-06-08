# TransitIndex — Data Expansion Plan (Balance Sheets + Native Frequency)
**Version:** 0.1 | **Status:** Proposed (2026-05-31, pre-build) | **Supersedes:** the four design memos this synthesizes

> **Why this doc exists.** The Excel workbook surfaces a tiny fraction of what the database
> can hold. It calls `annual_period()` for every row and reads only `mode_id IS NULL`, so a
> frequency-aware Postgres schema is flattened into one annual, system-wide grid. This plan
> unlocks three things the DB **already supports** with almost no schema change: (1) a
> **balance-sheet metric family**, (2) **monthly** capture of fast-moving ridership/revenue,
> and (3) a **carry-forward + per-metric "as of"** display model so stale-but-real numbers
> stay visible without ever being faked into the data. Authored from a 5-agent design pass.
>
> **Scope discipline (CLAUDE.md):** this is additive. The only genuinely new *code primitive*
> is a `quarterly_period()` builder. Everything else is seed rows (11 new metrics), workbook
> layout, extraction-prompt tightening, and the doc edits listed in §7.

---

## 1. Goal & scope

Increase the *amount* of credible data shown — without weakening the "every public number is
dispute-proof" promise.

- **In:** balance-sheet (statement of financial position) metrics; monthly ridership/revenue
  at native cadence; a carry-forward display rule; a frequency-aware Excel workbook; a website
  "Financial Position" tab; an accuracy-preserving extraction strategy for financial statements.
- **Out (unchanged / deferred):** any DB table migration (none needed); compare view & accounts
  (still Phase 3); the public API (still demand-gated).

---

## 2. The new balance-sheet metric family

Canadian transit financial statements follow **PSAB / PS 1201** (public-sector accounting), not
corporate GAAP. The governing identities are:

- **Financial assets − Liabilities = Net debt** (or net financial assets, if positive)
- **Net debt + Non-financial assets = Accumulated surplus**

These identities are what make balance-sheet data *self-checking* — the same property the
existing `sum_mismatch` flag already exploits for the income statement.

**Final set: 8 sourced line items + 3 derived = 11 new metric rows.** The metric catalog grows
**20 → 31** (22 sourced + 9 derived). All currency lines: `unit='CAD'`, `unit_type='currency'`,
`mode_id` NULL, `service_scope='total'`. **Native cadence = annual** (quarterly only for
TransLink, the one agency that publishes a quarterly statement of financial position).

| code | unit / type | derived | higher_is_better | ranked? (`comparable_flag`) | role / cross-check |
|---|---|---|---|---|---|
| `total_financial_assets` | CAD / currency | f | null | **no** (false) | LHS of net-debt identity |
| `total_liabilities` | CAD / currency | f | null | no | RHS of net-debt identity |
| `total_non_financial_assets` | CAD / currency | f | null | no | mostly TCA + inventories/prepaids |
| `total_assets` | CAD / currency | f | null | no | = financial + non-financial (headline) |
| `tangible_capital_assets` | CAD / currency | f | null | no | net book value; subset of non-financial |
| `accumulated_surplus` | CAD / currency | f | null | no | the bottom line ("net worth") |
| `long_term_debt` | CAD / currency | f | null | no | subset of liabilities |
| `cash_and_investments` | CAD / currency | f | null | no | liquidity; subset of financial assets |
| `net_debt` | CAD / currency | **t** | false | no | `total_liabilities − total_financial_assets`; printed value rides in `crosscheck_value` |
| `debt_to_assets` | % / ratio | **t** | false | **yes** (true) | `total_liabilities / total_assets` — scale-free leverage |
| `net_debt_per_capita` | CAD / currency | **t** | false | **yes** (true) | `net_debt / service_area_population` — the civic headline |

**Why raw dollars are not ranked:** a balance-sheet dollar figure measures *size*, not
*performance* — ranking TTC's $X billion in assets against Burlington's is meaningless. Only the
two **scale-free derived ratios** (`debt_to_assets`, `net_debt_per_capita`) are ranked, and they
flow through the existing `metric_ranks` materialization exactly like the current 6 derived
ratios. `net_debt` is derived for the cross-check but is itself a dollar figure → not ranked.

**Deferred to keep it tight (CLAUDE.md §2):** `reserves_reserve_funds` (a display-only component
with no cross-check) and `annual_surplus_deficit` (enables the surplus roll-forward identity —
a Phase-2 nicety). See Open Question #1.

### Accounting cross-checks (validation)

All fire as the **existing** staging flags — never a hard reject — and only when every operand is
present in the same (agency, period) cohort. They slot into `validation/flags.py` next to the
current `sum_mismatch` logic. **No new flag strings.**

| Check | Rule | Flag |
|---|---|---|
| Asset split | `total_assets ≈ total_financial_assets + total_non_financial_assets` | `sum_mismatch` |
| Net-debt identity | `net_debt ≈ total_liabilities − total_financial_assets` | `sum_mismatch` |
| Printed vs computed net debt | agency's *printed* net debt (`crosscheck_value`) vs computed | `cross_source_disagreement` |
| Component bounds | `cash_and_investments ≤ total_financial_assets`; `long_term_debt ≤ total_liabilities`; `tangible_capital_assets ≤ total_non_financial_assets` | `sum_mismatch` |
| Order-of-magnitude | a total implausibly small (missed "in thousands") | `unit_mismatch` |

**Tolerance:** 2% relative (matches existing `sum_mismatch`) **with an absolute floor of a few
thousand CAD**, so published rounding in "(in thousands)" statements doesn't false-positive.

---

## 3. The frequency & carry-forward rule (the cross-cutting decision)

The DB, the Excel sheet, and the website must agree on one rule. Stated once, applied in three places:

> **STORE only observed values, at each metric's native cadence, with their true period.
> NEVER store a carried-forward value — no fabricated rows, no `imputed` row used to "show an
> old number." CARRY-FORWARD is a DISPLAY-ONLY affordance: the latest known value shown into the
> current bucket, explicitly labelled "as of FY2024 · carried forward." It is never ranked and
> never charted.**

| Layer | Behaviour |
|---|---|
| **Database** | Native frequency per (agency, metric): ridership/revenue → `monthly` where a monthly source exists (StatCan covers 7 of 10 + Calgary/Edmonton open data), else annual; balance sheet → `annual_calendar`/`annual_fiscal`, `quarterly` for TransLink only. A missing period = **no row** (a real blank). `quality='imputed'` keeps its original meaning — a *stored* row a source genuinely estimated — and is **not** repurposed for carry-forward. |
| **Excel** | Blank cells stay **blank**. Carry-forward is never written into the sheet (writing it would re-import as fabricated data; import already skips blanks and never fabricates). Recency is visible via the Monthly sheet + the Gaps tab. |
| **Website** | A single value/KPI row carries the latest known value forward, styled with the **existing amber "stale-feed" state** (DESIGN.md component 8) + a "carried forward" label. **Trend charts and sparklines show a GAP** — never a flat carried segment, never interpolation across interior holes. (Same principle as the locked "no trend graph for estimates" rule.) |

**Ranking, stated once (load-bearing):** only stored rows that are `is_current=true`,
`comparable_flag=true`, and `quality ∈ {verified, preliminary}` are ranked — **same period
bucket + same scope, ordinal-only, neutral direction**. An agency whose newest balance sheet is
FY2023 is **not ranked** in the FY2024 cohort (UI: "not ranked — latest FY2023"), never ranked
across years. This is the existing period-comparability rule; balance-sheet ratios obey it unchanged.

---

## 4. Excel workbook — final structure

Replace the single annual "Data" sheet with **frequency-keyed sheets. 6 sheets total** (was 4).
Colour convention preserved — white = type here, grey = calculated / do-not-touch — plus one
addition: **light-yellow = optional / quarterly-only**, so expected blanks don't alarm a city staffer.

| # | Sheet | Cadence | Row key | Contents |
|---|---|---|---|---|
| 1 | How to use | — | — | Existing + a "Which tab do I use?" section + the `Period` token explanation |
| 2 | Data Dictionary | — | one row / metric | Existing + two new columns: **Native frequency** and **Sheet** (routes the user) |
| 3 | **Monthly** | fast | Agency, Year, Month (1–12) | `annual_ridership`, `operating_revenue` → resolved via `monthly_period(year, month)` |
| 4 | **Annual Fundamentals** | slow + medium | Agency, **Period** | the 14 sourced (ridership/revenue present as the *annual* roll-up cell) + 6 derived (grey live formulas) |
| 5 | **Balance Sheet** | annual (quarterly = TransLink) | Agency, **Period** | the 8 sourced line items + `net_debt` (grey) + 2 grey **check** columns |
| 6 | Gaps | — | rolls up sheets 3–5 | live `=COUNT` per (agency, period) + "newest period present" per agency |

**One period resolver.** The Annual Fundamentals and Balance Sheet sheets use a single **`Period`
text token**: `2024` (calendar), `FY2024-25` (fiscal), or `2024-Q1` (TransLink quarterly). Export
pre-fills the right token per agency (calendar vs fiscal, from `fiscal_year_end_month`) so staff
never hand-type it. Import parses the token and dispatches to `annual_period` or the **new
`quarterly_period`**. There is **no standalone Quarterly sheet** — it would be ~90% empty; the
rare quarterly rows live in the existing sheets via the `Q` token.

**Derived formulas stay annual-only and same-sheet** (Annual Fundamentals). Do **not** build
cross-sheet / cross-frequency `SUMIFS` — it would violate the never-mix-periods rule and is
unreadable for a non-technical user. The Monthly sheet is purely additive granularity; the
**server recompute stays the source of truth** for every derived value.

**Balance-sheet check columns** (grey, do-not-edit) surface the accounting identity *at entry time*:
- `Check: Assets` → `=IF(OR(tfa="",tnfa=""),"", IF(ABS((tfa+tnfa)-total_assets)<=ABS(total_assets)*0.005,"OK","MISMATCH"))`
- `Check: Net debt` → `=IF(OR(liab="",tfa=""),"", liab-tfa)` shown beside the printed net-debt cell, so a non-accountant can eyeball consistency.

---

## 5. Website — where the new data lives & how it renders

- **New fifth tab: "Financial Position"** (peer to *Ridership & Service / Financials / Fleet &
  Assets / Trends*). A balance sheet is a point-in-time *stock* statement with a different "as of"
  grammar and cadence (annual) than the flow-based *Financials* tab — separating them keeps each
  tab's "as of" honest. Caption: *"Balance-sheet figures are a snapshot as of each agency's
  fiscal year-end."*
- **Sections inside the tab** (plain-language, mirroring a PSAB statement; reuse the workbook's
  `_PLAIN_MEANING` glosses): *What the agency owns* (`tangible_capital_assets`,
  `total_financial_assets`, `total_assets`) · *What it owes* (`long_term_debt`,
  `total_liabilities`) · *Net position* (`net_debt`, `accumulated_surplus`). Each row uses the
  existing column layout (Metric · Value · Rank · Period · As of · YoY · sparkline) — nothing new
  to learn.
- **Mixed frequency on one page:** every row carries its **own** Period + As of; never an
  agency-level "last updated" stamp. A TransLink page shows Ridership · *Mar 2026* (monthly),
  Operating cost recovery · *2025-Q1* (quarterly), Net debt · *FY2024* (annual) stacked with no
  reconciliation — the per-metric date *is* the rigor signal.
- **Carry-forward / gap** render per §3: KPI rows carry forward with the amber state + "carried
  forward"; charts show a gap.
- **Free vs paid (mechanism unchanged — paywall integrity holds):** raw balance-sheet dollars are
  **paid-only and never ranked** → the free surface shows only the row label + "as of FY2024" +
  "Paid view". The two derived ratios are **free as ordinal ranks only** (e.g. "Net debt per
  capita · ranked 6th · as of FY2024"); their magnitudes are stripped server-side. Ranks come
  from the materialized `metric_ranks`, **not** request-time computation, so the per-capita
  number can't be reverse-engineered from the free payload.

---

## 6. LLM extraction — accuracy-preserving strategy for financial statements

Extend the existing `Extractor` seam (`ClaudePdfExtractor`, the two-pass `record_metrics` +
`verify_metrics`) — do **not** redesign the pipeline.

- **Register the new codes** in `refdata.METRICS` + `db/seeds/04_metrics.sql` so the extraction
  tool enum can emit them. `net_debt` is derived → recomputed server-side, never emitted by the model.
- **Locate-then-read.** Extend the metric keyword anchors with statement titles, English **and**
  French: "statement of financial position" / "état de la situation financière", "net debt" /
  "dette nette", "tangible capital assets" / "immobilisations corporelles". Stage 1: a cheap call
  finds the 1–2 statement pages (otherwise they're buried under route-level ridership tables).
  Stage 2: run the existing two-pass scoped to those pages.
- **Model declares scale & sign; code applies them (highest-leverage fix).** Add optional fields
  to the tool row schema: `printed_label` (verbatim), `table_reference`, `printed_scale`
  (units|thousands|millions), `printed_sign` (positive|negative), `column_year`. Then compute
  `value = parse_number(raw) × {1, 1e3, 1e6}[scale] × (−1 if negative)`. LLMs reliably read "(in
  thousands)" off a header but are unreliable at long-number arithmetic — split the labour and
  keep every scaling decision auditable.
- **Fix `parse_number` for accounting negatives (confirmed bug).** Today `(1,234)` raises
  `ValueError` and the value is silently dropped. Strip accounting parentheses → `-1234`, as a
  safety net for when the model forgets `printed_sign`. (French "1 234 567" / "12,5" separators
  are already handled — keep them.)
- **Harvest the comparative column = free history.** Audited statements print the prior year
  beside the current one. Emit one row per (line item × `column_year`), each mapped to its own
  `annual_period`. Roughly doubles history per PDF at ~zero marginal cost; the roll-forward
  identity self-validates it.
- **Accounting-identity checks as a deterministic oracle:** the four checks from §2 run in
  `validate_cohort`, reusing the existing flags. "Identities balanced ✓" in the review queue lets
  a reviewer fast-approve a self-consistent statement (Tier-2 still lands as `pending`).
- **Restatements via `restatement_of_id`.** When a newer report's prior-year column disagrees
  >2% with a stored value, treat as a restatement: on approval, point `restatement_of_id` at the
  superseded row and flip its `is_current=false`. Newer audited report wins; old row kept for the
  audit trail.
- **Consolidated small agencies (MiWay, Burlington):** extract the transit segment/schedule if
  the municipal statement breaks one out; otherwise **record nothing and flag the gap** — never
  attribute the whole city's balance sheet to transit (a wrong attribution is worse than the
  blank the user explicitly allowed).
- **Always feed page images for statements** (the vision `document` block); never the
  text-only path — text extraction scrambles multi-column financial tables. Keep each statement
  and its referenced note (e.g. "Note 7") in the same call; use text only as the locate signal.
- **Extend the gold eval (`eval/gold.py`):** balance-sheet fixtures for one real agency-year
  (recommend **TransLink** — cleanest published statements); one `should_flag=True` case per
  failure mode (an "(in thousands)" figure, a bracketed-negative net debt, a deliberately broken
  identity); one French (STM) fixture. **Tolerance 0.5% relative** for currency lines (tighter
  than ridership — audited figures are exact).

---

## 7. What changes, doc-by-doc

This plan is the source; the edits below bring the older docs in line.

| Doc | Edit |
|---|---|
| **data-model.md** | New "Balance-sheet metric family (PSAB)" subsection (the §2 set + identities + `comparable_flag=false` on raw dollars + the 2 ranked ratios). Add the §3 carry-forward rule to the computed-layer section and reframe `imputed` (method-estimated stored rows only, NOT carry-forward). |
| **schema-design.md** | Catalog grows **20 → 31**; rule "balance-sheet line items carry `comparable_flag=false`"; explicit **no table migration**; note `crosscheck_value` now used by the PDF path for printed net debt. |
| **update-frequency.md** | Add balance sheet to the SLOW tier (audited annual; quarterly = TransLink only — flag honestly that universal quarterly is *not* promised). Restate the per-metric "as of" + carry-forward display model. |
| **source-registry.md** | Add balance-sheet line items to the universal-metric reference; note `annual_report_pdfs` supplies them per agency; `translink_quarterly` carries TransLink's quarterly statement of financial position; consolidated agencies (MiWay→Mississauga, Burlington→City) source from municipal AFS. |
| **lane-0-foundation-spec.md** | Metric catalog 20 → 31 (the 11 new rows); note the one new period primitive `quarterly_period`; confirm `period_type` values unchanged (no `semiannual`). |
| **docs/data-dictionary.md** | Add the 11 new metrics with plain-language meanings + native frequency; note the table is now multi-frequency (not strictly one-row-per-year). |
| **docs/managing-data.md** | Rewrite for the multi-sheet flow: which tab per metric, the `Period` token, the colour legend (incl. light-yellow), the balance-sheet check columns, "blanks stay blank — the website carries forward, you don't." |
| **DESIGN.md** | Add the "Financial Position" 5th tab + 3-section layout; record carry-forward = reuse of the amber stale-feed state + "carried forward" label; the two new free ordinals. |
| **TODOS.md** | New build tasks (see §8 below). |

---

## 8. Build tasks (when this is approved — not done yet)

Code (Lane A, `ingest/`): `quarterly_period()` in `periods.py` · 11 new rows in `refdata.py`
*and* `db/seeds/04_metrics.sql` (kept in parity) · `net_debt` / `debt_to_assets` /
`net_debt_per_capita` + the population input in `jobs/derived_recompute.py` · multi-sheet
redesign of `workbook.py` · `parse_number` parens fix + tool-schema fields + prompt in
`pdf/llm.py` · locate-then-read keyword anchors in `pdf/claude_pdf.py` · PSAB identity checks in
`validation/flags.py` · balance-sheet + French + flag fixtures in `eval/gold.py`. Plus the doc
edits in §7. **No `db/migrations/` change** — the existing tables absorb all of it.

---

## 9. Open questions for the user (recommended defaults baked into this doc)

1. **Balance-sheet depth.** Ship the 8 sourced line items and **defer** `reserves_reserve_funds`
   + `annual_surplus_deficit`? *Recommend: defer both* — they add metrics without proportional
   cross-check value at launch. Override if councillors specifically cite reserves.
2. **`net_debt_per_capita` denominator.** Use the static `agencies.service_area_population`
   (simple; ordering barely moves year-to-year; label "per resident served") vs a year-stamped
   population metric (more correct, more work)? *Recommend: static attribute.*
3. **Import quality flag. — ✅ DECIDED (2026-05-31, user): keep `quality='verified'`.** Hand-typed
   workbook numbers stay `verified` (today's behaviour — city staff type straight from official
   published sources, so "verified" is appropriate). No code change; no paid-tier display change.
4. **TransLink quarterly balance sheet.** Show it at its native quarterly cadence (model already
   supports it) vs hold *all* balance sheets to annual for cross-agency consistency? *Recommend:
   native frequency* — TransLink quarterly, everyone else annual.
5. **Restatement visibility.** When a newer audited report restates a prior year, show a small
   "restated" label to civic users vs silently show only the latest? *Recommend: show the label*
   — it reinforces the dispute-proof positioning; both rows are kept regardless.
