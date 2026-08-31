# TransitIndex — Agency Detail View: Metrics & Presentation Spec

> **Status:** Design agreed 2026-06-09; **SHIPPED 2026-06-10** (`web/src/components/detail/` +
> `web/src/server/metrics/detail-model.ts`). **Supersedes** the 5-tab dense-spreadsheet detail
> design in [DESIGN.md](DESIGN.md) Component #3 and the standalone "Financial Position" 5th tab
> of the retired balance-sheet-and-frequency plan (git history).
>
> **What this doc is.** The single source of truth for *which* of the 32 metrics appear on the
> agency detail page, *where* each one lives, *how* it is displayed, and *how its history over
> the years is shown*. This is the "list of metrics that get published and how" reference.

---

## 1. Summary — two tabs

When you click an agency card you land on a **two-tab** detail page:

1. **Highlights** — a friendly overview: five hero numbers with charts, then the calculated
   ratios, service/fleet facts, and fleet composition as compact value tables. The approachable
   surface.
2. **Financials** — the agency's numbers laid out like its real audited financial statements,
   with every year shown as a column. The reference surface.

This replaces the previous plan of a five-tab Bloomberg-style spreadsheet
(*Ridership & Service / Financials / Fleet & Assets / Financial Position / Trends*). The old
"Financial Position" tab is **folded into** the single Financials tab as its second section.

**Two display rules decided this session, applied throughout:**

- **Rank badges** (`#3 of 14`) appear **only** on the five metrics already ranked on the
  directory card. Everything else shows the value with no rank.
- **History charts** are for the things people actually track over time (the five hero numbers).
  The ratios and service/fleet facts are shown as current values only; the Financials tab shows
  history as year columns instead of charts.

---

## 2. The complete metric map

`★` = shows a rank badge (the five directory-card metrics). "History" = how earlier years surface.
The weighted `fleet_capacity` hero is retired (metric-set-build-plan.md Phase 6); the fleet
composition (Bus / Light rail / Heavy rail / Commuter rail, from per-mode `fleet_size`) is a
separate non-ranked block, not a numbered row here. This table is otherwise pre-Phase-4/5 and due
a full pass in Phase 7 (financial-statement additions + the revenue/subsidy code renames are not
yet reflected).

| # | Metric | code | Tab · section | Rank | History shown as | Example · cadence |
|---|--------|------|---------------|:----:|------------------|-------------------|
| 1 | Ridership | `ridership` | Highlights · Hero | ★ | drop-down chart | 521M boardings · **monthly** |
| 2 | Operating revenue | `operating_revenue` | Highlights · Hero | ★ | drop-down chart | $1.42B · **monthly** |
| 3 | On-time performance | `on_time_performance` | Highlights · Hero | ★ | drop-down chart | 81% · monthly→annual |
| 4 | Cost per rider | `cost_per_rider` | Highlights · Hero | ★ | drop-down chart | $4.60 · annual |
| 5 | Subsidy per rider | `subsidy_per_rider` | Highlights · Hero | ★ | drop-down chart | $1.95 · annual |
| 6 | Farebox recovery ratio | `farebox_recovery_ratio` | Highlights · Ratios | — | none (current only) | 58% · annual |
| 7 | Cost per revenue hour | `cost_per_hour` | Highlights · Ratios | — | none (current only) | $185/hr · annual |
| 8 | Trips per revenue hour | `trips_per_revenue_hour` | Highlights · Ratios | — | none (current only) | 52 trips/hr · annual |
| 9 | Average fare | `average_fare` | Highlights · Ratios | — | none (current only) | $2.65 · annual* |
| 10 | Revenue service hours | `revenue_service_hours` | Highlights · Service & Fleet | — | none (current only) | 9.8M hrs · annual |
| 11 | Vehicle revenue km | `vehicle_revenue_km` | Highlights · Service & Fleet | — | none (current only) | 220M km · annual |
| 12 | Fleet size | `fleet_size` | Highlights · Service & Fleet | — | none (current only) | 2,100 · annual |
| 13 | Fleet average age | `fleet_average_age` | Highlights · Service & Fleet | — | none (current only) | 7.4 yrs · annual |
| 14 | Accessible fleet % | `accessible_fleet_pct` | Highlights · Service & Fleet | — | none (current only) | 100% · annual |
| — | Fleet composition (Bus / Light rail / Heavy rail / Commuter rail) | `fleet_size` (per mode) | Highlights · Fleet composition | — | none (current only) | 4 labelled counts · annual |
| 15 | Farebox revenue | `farebox_revenue` | Financials · P&L | — | year columns | $ · annual |
| 16 | Other revenue | `other_revenue` | Financials · P&L | — | year columns | $ · annual |
| 17 | Government subsidy | `subsidy` | Financials · P&L | — | year columns | $ · annual |
| 18 | Total revenue | `total_revenue` | Financials · P&L | — | year columns | $ · annual |
| 19 | Labour cost | `labour_cost` | Financials · P&L | — | year columns | $ · annual |
| 20 | Energy & fuel cost | `energy_fuel_cost` | Financials · P&L | — | year columns | $ · annual |
| 21 | Materials & services cost | `materials_services_cost` | Financials · P&L | — | year columns | $ · annual |
| 22 | Other operating expenses | `other_operating_expenses` | Financials · P&L | — | year columns | $ · annual |
| 23 | Total operating expenses | `operating_expenses` | Financials · P&L | — | year columns | $ · annual |
| 24 | Amortization | `amortization` | Financials · P&L | — | year columns | $ · annual |
| 25 | Total expenses | `total_expenses` | Financials · P&L | — | year columns | $ · annual |
| 26 | Surplus / (deficit) | `annual_surplus_deficit` | Financials · P&L | — | year columns | $ · annual |
| 27 | Capital expenditure (memo) | `capital_expenditure` | Financials · P&L | — | year columns | $ · annual |

*Average fare's inputs (revenue, ridership) are both monthly, so it *can* be charted monthly later
if we promote it to a hero — for now it's a current-value ratio.

**2026-08-25 P&L redesign:** the Financials tab is a single P&L (rows 15–27). The balance-sheet
rows (`cash_and_investments` … `net_debt_per_capita`) are still collected and still exported in
the paid CSV download (`POSITION_ROWS` in `detail-model.ts`), but no longer rendered on the page.

**Not on Highlights, by decision:** the big total dollar figures live only on the Financials tab.
The taxpayer angle is still represented on Highlights by **subsidy per rider** (hero). See §6 open
item if you later want the total-subsidy dollar up top.

---

## 3. Tab 1 — Highlights

```
HIGHLIGHTS

┌─ Ridership ───── #3/14 ┐ ┌─ Operating revenue #5/14┐ ┌─ On-time perf ── #2/14 ┐
│ 521M boardings         │ │ $1.42B                  │ │ 81%                    │
│ ▲ 4.2% vs 2024         │ │ ▲ 4.4% vs 2024          │ │ ▼ 1.3% vs 2024         │
└────────────────────────┘ └─────────────────────────┘ └────────────────────────┘
┌─ Cost per rider #8/14 ─┐ ┌─ Subsidy per rider #6/14┐
│ $4.60                  │ │ $1.95                   │
│ ▲ 2.1% vs 2024         │ │ ▲ 5.0% vs 2024          │
└────────────────────────┘ └─────────────────────────┘
     ↑ click any box → history chart drops down beneath that row

EFFICIENCY RATIOS                    SERVICE & FLEET               FLEET COMPOSITION
Farebox recovery        58%          Revenue service hours 9.8M hrs Bus              1,850
Cost per revenue hour   $185/hr      Vehicle revenue km    220M km  Light rail         120
Trips per revenue hour  52           Fleet size               2,100 Heavy rail         680
Average fare            $2.65        Fleet average age       7.4 yrs Commuter rail     40
                                     Accessible fleet %       100%
```

### 3.1 Hero boxes (5) — the directory-card metrics
- The exact five metrics on the directory card (`agency-card.tsx` `METRIC_SLOTS`): **Ridership ·
  Operating revenue · On-time performance · Cost per rider · Subsidy per rider**. The weighted
  `fleet_capacity` hero is retired (metric-set-build-plan.md Phase 6) — the fleet composition is
  a separate, non-ranked block (§3.3).
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
- No charts, no history, no rank badge. (`on_time_performance` is a service metric but it's
  promoted to the hero row.)

### 3.4 Fleet composition (4) — current value only, not ranked
- **Bus (bus, BRT, trolleybus) · Light rail (light rail, streetcar) · Heavy rail (subway) ·
  Commuter rail** — four plain labelled counts, capacity-ordered (metric-set-build-plan.md Phase 6).
  Replaces the retired weighted `fleet_capacity` hero. Ferry, paratransit, and on-demand fleets are
  excluded from this block.
- Built from the existing per-mode `fleet_size` (grouped by class), NOT a new stored metric.
- Same two-column list treatment as §3.2/§3.3. **No charts, no history, no rank badge** — this is a
  composition, not a "biggest fleet" leaderboard.

---

## 4. Tab 2 — Financials

Laid out like the agency's audited statements, **all years shown as columns** by default. Each row is
a statement line; bold rows are the totals/subtotals.

```
REVENUE & EXPENSES              2021    2022    2023    2024    2025
  Farebox revenue               …       …       …       $1.02B  $1.08B
  Other revenue                 …       …       …       $0.34B  $0.34B
  Government subsidy            …       …       …       $0.92B  $0.98B
Total revenue                   …       …       …       $2.28B  $2.40B
  Labour                        …       …       …       $1.48B  $1.55B
  Energy & fuel                 …       …       …       $0.19B  $0.21B
  Materials & services          …       …       …       $0.61B  $0.64B
  Other operating               …       …       …       …       …
Total operating expenses        $2.0B   $2.1B   $2.2B   $2.28B  $2.40B
  Amortization (asset wear)     …       …       …       …       …
Total expenses                  …       …       …       …       …
Surplus / (deficit)             …       …       …       …       …
Capital spending (memo)         …       …       …       …       …
```

- **One table: the P&L** (2026-08-25 redesign) — revenue components (farebox + other + subsidy)
  sum to **Total revenue**; expense components (labour + energy + materials + other) sum to
  **Total operating expenses**, plus **amortization** = **Total expenses**; the bottom line is
  **Surplus / (deficit)**.
- **Capital spending is a memo line, never summed into expenses** — buying a bus is not a cost
  that year; its cost enters the P&L as amortization spread over the asset's life. The table
  carries the note: *"Capital spending is shown for reference only — it is not counted as an
  expense; the yearly wear on assets appears as amortization."*
- **The balance sheet left the page** — its rows stay in the DB and the paid CSV download.
- A **missing year is a blank cell, never a 0** (a 0 reads as "the agency collapsed"). Each row
  carries its own period, never one page-level "last updated" stamp
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
[transitindex-mvp.md](../planning/transitindex-mvp.md), the retired M1-WEB-PLAN / phase-plan docs
(git history), and the paywall framing in [DESIGN.md](DESIGN.md) (thesis + Components #2/#5).

**Code consequence — SHIPPED 2026-06-10.** Viewing is un-gated for everyone; the subscription now
gates the per-agency financials CSV at `/api/agency/[slug]/download`.

---

## 7. Charts

- **Library: Recharts** — gives hover tooltips and smooth lines with little code.
- **Line** for the 3 monthly metrics; **bar** for sparse annual series (≤4 points).
- **Accessibility:** every chart needs a text alternative (e.g. "+4.1% over 5 years") and the page keeps
  real `<table>` semantics for the Financials grid (WCAG 2.1 AA baseline, [DESIGN.md](DESIGN.md)).
- Tabular numbers (`font-variant-numeric: tabular-nums`) everywhere figures align.

---

## 8. Relationship to other docs (what this changes)

| Doc | What this spec changes |
|-----|------------------------|
| [DESIGN.md](DESIGN.md) | Component #3's **5-tab spreadsheet** → **2 tabs** (Highlights + Financials). The "PAID detail = dense spreadsheet" mood softens: Highlights is friendly charts; only Financials is grid-dense. See the 2026-06-09 status note added there. |
| balance-sheet-and-frequency plan §5 (retired, git history) | The standalone **"Financial Position" 5th tab** becomes **Section B of the Financials tab**. The 3-section balance-sheet layout and honest "fiscal year-end snapshot" caption are preserved. |
| [transitindex-mvp.md](../planning/transitindex-mvp.md) | The free=ranks / paid=numbers monetization was superseded toward free-viewing / paid-download (§6). |

---

## 9. Build status

**Not built.** Current detail UI is a Snapshot/Trends switch (`web/src/components/detail/`,
`detail-tabs.tsx`). Build task tracked in [TODOS.md](../../TODOS.md). The 2026-06-06 design-review item
**F3** (detail "FULL DATA" table contradicts the rank cards) is resolved by this redesign — the
two-tab layout shows values with per-row periods instead of the conflicting rank/blank table.

---

## 10. Changing the published metric set — sync checklist

When a metric is added, renamed, or retired, four places must move together:

1. **`ingest/transitindex_ingest/refdata.py` `METRICS` + `db/seeds/04_metrics.sql`** — the
   canonical set, kept in parity (covered by tests).
2. **A `metric_dictionary.yaml` entry** — definition, EN/FR labels, common confusions; this
   feeds `extraction_guidance()` into the vision extraction prompt.
3. **A gold-fixture row** in `ingest/tests/fixtures/gold/` — so the eval scores the metric.
4. **The web placement constants** in `web/src/server/metrics/detail-model.ts` — which tab ·
   section the metric appears in (the map in §2).

The extraction tool's `metric_code` enum and the system prompt update **automatically** from
`METRICS` (locked by test) — no manual prompt edit needed.
