# TransitIndex — Agency Detail View: Metrics & Presentation Spec

> **Status:** Design agreed 2026-06-09 (user-driven session). **Not built yet** — the live
> detail page is still the old Snapshot/Trends switch (`web/src/app/agency/[slug]/page.tsx`).
> **Supersedes** the 5-tab dense-spreadsheet detail design in [DESIGN.md](DESIGN.md) Component #3
> and the standalone "Financial Position" 5th tab in
> [balance-sheet-and-frequency-plan.md §5](../planning/balance-sheet-and-frequency-plan.md).
>
> **What this doc is.** The single source of truth for *which* of the 32 metrics appear on the
> agency detail page, *where* each one lives, *how* it is displayed, and *how its history over
> the years is shown*. This is the "list of metrics that get published and how" reference.

---

## 1. Summary — two tabs

When you click an agency card you land on a **two-tab** detail page:

1. **Highlights** — a friendly overview: six hero numbers with charts, then the calculated
   ratios and service/fleet facts as compact value tables. The approachable surface.
2. **Financials** — the agency's numbers laid out like its real audited financial statements,
   with every year shown as a column. The reference surface.

This replaces the previous plan of a five-tab Bloomberg-style spreadsheet
(*Ridership & Service / Financials / Fleet & Assets / Financial Position / Trends*). The old
"Financial Position" tab is **folded into** the single Financials tab as its second section.

**Two display rules decided this session, applied throughout:**

- **Rank badges** (`#3 of 14`) appear **only** on the six metrics already ranked on the
  directory card. Everything else shows the value with no rank.
- **History charts** are for the things people actually track over time (the six hero numbers).
  The ratios and service/fleet facts are shown as current values only; the Financials tab shows
  history as year columns instead of charts.

---

## 2. The complete metric map (all 32)

`★` = shows a rank badge (the six directory-card metrics). "History" = how earlier years surface.

| # | Metric | code | Tab · section | Rank | History shown as | Example · cadence |
|---|--------|------|---------------|:----:|------------------|-------------------|
| 1 | Ridership | `ridership` | Highlights · Hero | ★ | drop-down chart | 521M boardings · **monthly** |
| 2 | Operating revenue | `operating_revenue` | Highlights · Hero | ★ | drop-down chart | $1.42B · **monthly** |
| 3 | On-time performance | `on_time_performance` | Highlights · Hero | ★ | drop-down chart | 81% · monthly→annual |
| 4 | Cost per rider | `cost_per_rider` | Highlights · Hero | ★ | drop-down chart | $4.60 · annual |
| 5 | Subsidy per rider | `subsidy_per_rider` | Highlights · Hero | ★ | drop-down chart | $1.95 · annual |
| 6 | Fleet scale | `fleet_capacity` | Highlights · Hero | ★ | drop-down chart | 4,800 · annual |
| 7 | Farebox recovery ratio | `farebox_recovery_ratio` | Highlights · Ratios | — | none (current only) | 58% · annual |
| 8 | Cost per revenue hour | `cost_per_hour` | Highlights · Ratios | — | none (current only) | $185/hr · annual |
| 9 | Trips per revenue hour | `trips_per_revenue_hour` | Highlights · Ratios | — | none (current only) | 52 trips/hr · annual |
| 10 | Average fare | `average_fare` | Highlights · Ratios | — | none (current only) | $2.65 · annual* |
| 11 | Revenue service hours | `revenue_service_hours` | Highlights · Service & Fleet | — | none (current only) | 9.8M hrs · annual |
| 12 | Vehicle revenue km | `vehicle_revenue_km` | Highlights · Service & Fleet | — | none (current only) | 220M km · annual |
| 13 | Fleet size | `fleet_size` | Highlights · Service & Fleet | — | none (current only) | 2,100 · annual |
| 14 | Fleet average age | `fleet_average_age` | Highlights · Service & Fleet | — | none (current only) | 7.4 yrs · annual |
| 15 | Accessible fleet % | `accessible_fleet_pct` | Highlights · Service & Fleet | — | none (current only) | 100% · annual |
| 16 | Operating revenue ‡ | `operating_revenue` | Financials · Operations | — | year columns | $ · annual |
| 17 | Labour cost | `labour_cost` | Financials · Operations | — | year columns | $ · annual |
| 18 | Energy & fuel cost | `energy_fuel_cost` | Financials · Operations | — | year columns | $ · annual |
| 19 | Materials & services cost | `materials_services_cost` | Financials · Operations | — | year columns | $ · annual |
| 20 | Total operating expenses | `operating_expenses` | Financials · Operations | — | year columns | $ · annual |
| 21 | Total operating subsidy | `total_operating_subsidy` | Financials · Operations | — | year columns | $ · annual |
| 22 | Capital expenditure | `capital_expenditure` | Financials · Operations | — | year columns | $ · annual |
| 23 | Cash & investments | `cash_and_investments` | Financials · Position | — | year columns | $ · annual |
| 24 | Total financial assets | `total_financial_assets` | Financials · Position | — | year columns | $ · annual |
| 25 | Long-term debt | `long_term_debt` | Financials · Position | — | year columns | $ · annual |
| 26 | Total liabilities | `total_liabilities` | Financials · Position | — | year columns | $ · annual |
| 27 | Net debt | `net_debt` | Financials · Position | — | year columns | $ · annual |
| 28 | Tangible capital assets | `tangible_capital_assets` | Financials · Position | — | year columns | $ · annual |
| 29 | Total non-financial assets | `total_non_financial_assets` | Financials · Position | — | year columns | $ · annual |
| 30 | Total assets | `total_assets` | Financials · Position | — | year columns | $ · annual |
| 31 | Accumulated surplus | `accumulated_surplus` | Financials · Position | — | year columns | $ · annual |
| 32 | Debt to assets | `debt_to_assets` | Financials · Position | — | year columns | % · annual |
| 33 | Net debt per capita | `net_debt_per_capita` | Financials · Position | — | year columns | $ · annual |

*Average fare's inputs (revenue, ridership) are both monthly, so it *can* be charted monthly later
if we promote it to a hero — for now it's a current-value ratio.
‡ Operating revenue intentionally appears twice: once as a Highlights hero, once as the top line of
the operations statement. That's the only deliberate repeat. 33 rows = 32 unique metrics + 1 repeat.

**Not on Highlights, by decision:** `operating_expenses` and `total_operating_subsidy` (the big total
dollar figures) live only on the Financials tab. The taxpayer angle is still represented on Highlights
by **subsidy per rider** (hero). See §6 open item if you later want the total-subsidy dollar up top.

---

## 3. Tab 1 — Highlights

```
HIGHLIGHTS

┌─ Ridership ───── #3/14 ┐ ┌─ Operating revenue #5/14┐ ┌─ On-time perf ── #2/14 ┐
│ 521M boardings         │ │ $1.42B                  │ │ 81%                    │
│ ▲ 4.2% vs 2024         │ │ ▲ 4.4% vs 2024          │ │ ▼ 1.3% vs 2024         │
└────────────────────────┘ └─────────────────────────┘ └────────────────────────┘
┌─ Cost per rider #8/14 ─┐ ┌─ Subsidy per rider #6/14┐ ┌─ Fleet scale ─── #4/14 ┐
│ $4.60                  │ │ $1.95                   │ │ 4,800                  │
│ ▲ 2.1% vs 2024         │ │ ▲ 5.0% vs 2024          │ │ — flat vs 2024         │
└────────────────────────┘ └─────────────────────────┘ └────────────────────────┘
     ↑ click any box → history chart drops down beneath that row

EFFICIENCY RATIOS                    SERVICE & FLEET
Farebox recovery        58%          Revenue service hours    9.8M hrs
Cost per revenue hour   $185/hr      Vehicle revenue km       220M km
Trips per revenue hour  52           Fleet size               2,100
Average fare            $2.65        Fleet average age        7.4 yrs
                                     Accessible fleet %       100%
```

### 3.1 Hero boxes (6) — the directory-card metrics
- The exact six metrics on the directory card (`agency-card.tsx` `METRIC_SLOTS`): **Ridership ·
  Operating revenue · On-time performance · Cost per rider · Subsidy per rider · Fleet scale**.
- Each box shows: rank badge · the value · a **neutral up/down arrow + % vs the prior year**.
- **The arrow is direction only — never green=good / red=bad.** Ridership up and cost-per-rider up
  are not "good" and "bad"; coloring them would break the neutral-ordinal invariant
  ([DESIGN.md](DESIGN.md) "Rank direction is NEUTRAL"). Use one accent + the arrow glyph.
- **Click → a history chart drops down** beneath that box's row (accordion).
- **vs prior year compares like-for-like:** full calendar year vs full calendar year (not this month
  vs last month) so seasonality doesn't distort the arrow. Flat / no prior year → "—".

### 3.2 Efficiency ratios (4) — current value only
- **Farebox recovery · Cost per revenue hour · Trips per revenue hour · Average fare.**
- Rendered as a compact two-column list (label | value). **No charts, no history, no rank badge.**
- (`cost_per_rider` and `subsidy_per_rider` are ratios too, but they're promoted to the hero row.)

### 3.3 Service & fleet (5) — current value only
- **Revenue service hours · Vehicle revenue km · Fleet size · Fleet average age · Accessible fleet %.**
- Same two-column list treatment, sitting **beside** the ratios (two mini-tables side by side).
- No charts, no history, no rank badge. (`on_time_performance` and `fleet_capacity` are
  service/fleet metrics but they're promoted to the hero row.)

---

## 4. Tab 2 — Financials

Laid out like the agency's audited statements, **all years shown as columns** by default. Each row is
a statement line; bold rows are the totals/subtotals.

```
STATEMENT OF OPERATIONS         2021    2022    2023    2024    2025
Fare & operating revenue        $1.1B   $0.9B   $1.2B   $1.36B  $1.42B
  Labour                        …       …       …       $1.48B  $1.55B
  Energy & fuel                 …       …       …       $0.19B  $0.21B
  Materials & services          …       …       …       $0.61B  $0.64B
  Total operating expenses      $2.0B   $2.1B   $2.2B   $2.28B  $2.40B
Operating subsidy (the gap)     …       …       …       $0.92B  $0.98B
Capital spending                …       …       …       …       …

STATEMENT OF FINANCIAL POSITION 2021    2022    2023    2024    2025
Cash & investments              …       …       …       …       …
  Total financial assets        …       …       …       …       …
Long-term debt                  …       …       …       …       …
  Total liabilities             …       …       …       …       …
Net debt                        …       …       …       …       …
Tangible capital assets         …       …       …       …       …
  Total non-financial assets    …       …       …       …       …
  Total assets                  …       …       …       …       …
Accumulated surplus             …       …       …       …       …
  Debt to assets                …       …       …       …       …
  Net debt per capita           …       …       …       …       …
```

- **Section A — Statement of Operations** (the income statement, the flow of money this year):
  rows 16–22 above.
- **Section B — Statement of Financial Position** (the balance sheet, the stock at fiscal year-end):
  rows 23–33. This is the old "Financial Position" tab, now a section here. Keep its honest caption:
  *"Balance-sheet figures are a snapshot as of each agency's fiscal year-end."*
- A **missing year is a blank cell, never a 0** (a 0 reads as "the agency collapsed"). The two
  statements may end on different latest years (operations monthly-fed; balance sheet annual-audited)
  — each carries its own period, never one page-level "last updated" stamp
  ([DESIGN.md](DESIGN.md) "Data display rules").

---

## 5. How "previous years" is shown (the history model)

Earlier years surface in three layers, lightest to heaviest — the same data, shown to fit each tab:

1. **The delta** — every Highlights hero box carries a neutral `▲/▼ % vs <last year>` tag. Answers
   "up or down" with no click.
2. **The chart** — clicking a hero box drops down a line/bar of **every year we have**.
3. **The year columns** — the Financials tab shows the full run of years as table columns (and that
   same grid is what a data download would contain).

**Granularity is honest, not uniform:**
- Only **3 metrics are monthly** — `ridership`, `operating_revenue`, `average_fare`. Their charts are
  smooth month-by-month lines, with a `Yearly / Monthly` toggle.
- **Everything else is annual** — one point per year. Where only 2–4 years exist, a **bar chart** of
  yearly values reads cleaner than a near-empty line; prefer bars for sparse annual series.
- **Gaps are gaps.** A missing interior year shows as a break in the line — never interpolated, never
  carried flat (same rule as [DESIGN.md](DESIGN.md) carry-forward / estimate-toggle: a missing trend
  is the signal). Nothing is ever fabricated into a chart.

---

## 6. Access model (free vs paid) — ✅ DECIDED 2026-06-09

- **Viewing is unlimited and free.** Every number, chart, and statement on the detail page is shown to
  everyone — no rank-gate, no metering, no login required to read. (Directory cards already show ranks
  free; now the detail numbers are free too.)
- **The paid product is data download, by subscription.** A subscriber can **download one agency's
  dataset at a time** — the all-years statement grid as CSV/Excel. Pricing and subscription mechanics are
  deferred ("deal with it later"). Bulk / multi-agency export stays the pre-existing "build when a
  researcher asks" deferral ([TODOS.md](../../TODOS.md) "Public API + bulk dataset download").

**This decision inverts the shipped model** (free = ranks, paid = the raw numbers — the $20/yr demand
test) and is the "Everything-paid vs free-public" open decision in [TODOS.md](../../TODOS.md), now
answered toward **free-public**. It therefore supersedes the free/paid split in
[transitindex-mvp.md](../planning/transitindex-mvp.md), [M1-WEB-PLAN.md](../planning/M1-WEB-PLAN.md),
[phase-plan.md](../planning/phase-plan.md), and the paywall framing in [DESIGN.md](DESIGN.md) (thesis +
Components #2/#5) — each now carries a dated superseding pointer here.

**Code consequence (build task, not done).** The server choke point in `web/src/server/metrics/`
currently strips raw values from unauthenticated responses. Viewing-free means the detail numbers ship to
everyone, and the subscription gate moves to a new **per-agency download** action. Until that lands, the
live site still gates numbers — the docs lead the code here. Tracked in [TODOS.md](../../TODOS.md).

---

## 7. Charts

- **Library: Recharts** — already an anticipated dependency ([M1-WEB-PLAN.md](../planning/M1-WEB-PLAN.md)
  `web/package.json` deps note). Gives hover tooltips and smooth lines with little code.
- **Line** for the 3 monthly metrics; **bar** for sparse annual series (≤4 points).
- **Accessibility:** every chart needs a text alternative (e.g. "+4.1% over 5 years") and the page keeps
  real `<table>` semantics for the Financials grid (WCAG 2.1 AA baseline, [DESIGN.md](DESIGN.md)).
- Tabular numbers (`font-variant-numeric: tabular-nums`) everywhere figures align.

---

## 8. Relationship to other docs (what this changes)

| Doc | What this spec changes |
|-----|------------------------|
| [DESIGN.md](DESIGN.md) | Component #3's **5-tab spreadsheet** → **2 tabs** (Highlights + Financials). The "PAID detail = dense spreadsheet" mood softens: Highlights is friendly charts; only Financials is grid-dense. See the 2026-06-09 status note added there. |
| [balance-sheet-and-frequency-plan.md §5](../planning/balance-sheet-and-frequency-plan.md) | The standalone **"Financial Position" 5th tab** becomes **Section B of the Financials tab**. The 3-section balance-sheet layout and honest "fiscal year-end snapshot" caption are preserved. |
| [phase-plan.md](../planning/phase-plan.md) | The Product/UX "PAID spreadsheet (financial-statement tabs)" line is superseded for the detail view by this 2-tab model. |
| [transitindex-mvp.md](../planning/transitindex-mvp.md) / [M1-WEB-PLAN.md](../planning/M1-WEB-PLAN.md) | **Not yet changed.** The free=ranks / paid=numbers monetization is a separate decision (§6). |

---

## 9. Build status

**Not built.** Current detail UI is a Snapshot/Trends switch (`web/src/components/detail/`,
`detail-tabs.tsx`). Build task tracked in [TODOS.md](../../TODOS.md). The 2026-06-06 design-review item
**F3** (detail "FULL DATA" table contradicts the rank cards) is resolved by this redesign — the
two-tab layout shows values with per-row periods instead of the conflicting rank/blank table.
