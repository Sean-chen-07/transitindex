# TransitIndex — Update Frequency Matrix
**Version:** 0.1 | **Researched:** 2026-05-29 | **Status:** Verified against primary sources

The core question: can we update numbers more often than yearly? **Yes — but frequency is driven by the metric, then by the agency.** This doc records the finest available frequency for every agency × metric, the publication lag, and the source.

---

## The single most important insight

**There are three "speeds" of transit data, and they don't move together:**

| Speed | Metrics | Why | Best frequency |
|---|---|---|---|
| **Fast** | Ridership, fare revenue | Counted continuously (fare gates, APCs); reported to boards monthly | **Monthly** (~1–2 mo lag) |
| **Medium** | Operating expenses, service hours, on-time performance | Tracked internally but reported in budget cycles | **Quarterly** (a few agencies only) |
| **Slow** | Farebox recovery, cost per rider, cost per hour, subsidy per rider, fleet size, labour cost, energy/fuel cost, materials & services, total subsidy, capital expenditure, fleet age, accessible-fleet %, **balance-sheet lines (assets, liabilities, net debt, accumulated surplus, TCA, long-term debt)** | Depend on audited annual financials; balance sheet = audited *statement of financial position* | **Annual** (almost everywhere) |

**Balance sheet is the slowest layer (added 2026-05-31).** The statement of financial position
lives in audited annual financial statements, so its native cadence is **annual** — be honest:
universal *quarterly* balance sheets are **not** promised. **TransLink** is the one agency that
publishes a quarterly statement of financial position; show it quarterly, everyone else annual.
Small agencies (MiWay, Burlington) appear inside their municipality's consolidated annual
statements. See [balance-sheet-and-frequency-plan.md](../planning/balance-sheet-and-frequency-plan.md).

**Why farebox recovery is stuck at annual:** it's `revenue / expenses`, and *expenses* come from audited year-end statements for almost every agency. A derived metric can never refresh faster than its slowest input. So the headline farebox number is annual for 9 of 10 agencies — **TransLink is the only exception** (publishes it quarterly).

**Product consequence:** This is exactly the Yahoo Finance model. The *price* (ridership) ticks monthly and makes the product feel alive; the *fundamentals* (cost structure, farebox recovery) refresh annually like earnings. Design the UI to show an "as of" date **per metric**, not one date for the whole agency.

---

## StatCan 23-10-0307-01 — the monthly backbone (and its limits)

This is the only normalized, cross-agency, monthly feed. **Monthly, ~2-month lag** (March 2026 data released May 19, 2026). Two variables only: **total passenger trips** and **total revenue excluding subsidies**.

**⚠ CRITICAL CORRECTION to the source registry:** It does NOT cover all launch agencies. Confirmed agency rows (of our 10):

| In StatCan 23-10-0307 (monthly) | NOT in it (need other sources) |
|---|---|
| ✅ TTC | ❌ OC Transpo |
| ✅ STM | ❌ MiWay |
| ✅ TransLink | ❌ Burlington Transit |
| ✅ Metrolinx (reported at **GTHA** level, not GO-specific) | |
| ✅ Calgary Transit | |
| ✅ Edmonton Transit Service | |
| ✅ BC Transit (**Victoria system only**, not the other ~80 communities) | |

This changes the build plan: my earlier registry assumed SC-307 covered OC Transpo and MiWay. **It does not.** Those two need agency-native sources for monthly ridership (OC Transpo has it; MiWay does not — see below).

---

## Master frequency matrix

Legend: **M** = monthly · **Q** = quarterly · **A** = annual · lag in parentheses

### Major Multimodal

| Metric | TTC | STM | TransLink |
|---|---|---|---|
| Ridership | **M** (~2mo) — CEO Report + StatCan | **M** (~2mo) — **StatCan only** (own deck excludes it) | **M/Q** (~2mo) — StatCan + Quarterly Report |
| Fare revenue | **M** (~2mo) — CEO Report (vs budget, YTD) | **M** (~2mo) — StatCan only | **Q** (~2mo) — full Statement of Operations |
| Operating expenses | **A** — annual budget/year-end only | **A** — annual only | **Q** (~2mo) — full expenses by segment ✅ |
| Service hours | **M** — CEO Report (scheduled hrs, % delivered) | **M** — KPI deck (delivery rate, punctuality) | **Q** — by mode, vs budget |
| Farebox recovery | **A** | **A** | **Q** — "operating cost recovery" stated directly ✅ |
| On-time performance | **M** — CEO Report (OTP by mode, MDBF) | **M** — KPI deck | **Q** — by mode |
| Fleet size | **A** | **A** | **A** |

**TransLink is the gold standard** — the only agency publishing full quarterly financials *including* expenses and farebox recovery.
**STM is a trap** — its monthly board deck is operations-only (punctuality, reliability). No ridership, no money. Monthly STM ridership comes from StatCan, period.

### Regional Rail

| Metric | Metrolinx / GO |
|---|---|
| Ridership | **Q** — Operations Report (GO Rail/Bus, UP Express) · **M** total via StatCan (GTHA level) |
| Fare revenue | **A** — annual audited only (StatCan gives M total at GTHA) |
| Operating expenses | **A** — annual audited only |
| Service hours | **Q** — narrative in ops report; detailed annual |
| Farebox recovery | **A** |
| On-time performance | **Q** — GO Rail/Bus/UP + CSAT |
| Fleet size | **A** |
| **Fiscal year** | **April–March** — "Q2" = Jul–Sep |

### Mid-size Bus + LRT

| Metric | OC Transpo | Calgary Transit | Edmonton ETS | MiWay |
|---|---|---|---|---|
| Ridership | **M** (~1mo) — octranspo.com KPIs **(HTML/PDF, not open data)** | **M** — open data `nypk-snzd` (verify lag) | **M** (~1mo) — open data `wj6v-epas` ✅ best | **A** — no monthly open data ❌ |
| Fare revenue | **Q** — budget status reports | **M** rev via StatCan; **Q** local | **M** rev via StatCan | **A** — city budget |
| Operating expenses | **Q** — budget status reports ✅ | **Q** — CAO Quarterly Report ✅ | **Q-ish** — council updates | **A** |
| Service hours | **A** | **A** | **M** — open data `wh9u-ef4x` ✅ | **A** |
| Farebox recovery | **A** (calc) | **A** (calc) | **A** (calc) | **A** — FAO report (stale, ~2yr) |
| Fleet size | **A** | **A/live** — fleet list on open data ✅ | **A** | **A** |

**Edmonton is the best-instrumented mid-size** — monthly ridership AND monthly service hours via open data, ~1-month lag.
**OC Transpo** has monthly ridership but only as HTML/PDF → needs a scraper, not an API call.
**MiWay** is effectively annual-only despite being large (~38M trips) — its open data portal has routes/stops/GTFS but zero ridership datasets.

### Hybrid / Small Local

| Metric | BC Transit | Burlington Transit |
|---|---|---|
| Ridership | **M** (Victoria only, via StatCan); **A** system-wide | **A** — no sub-annual open data |
| Fare revenue / expenses | **A** — annual report (FY Apr–Mar, ~5mo lag) | **A** — city budget |
| Service hours | **A** | **A** |
| Farebox recovery | **A** (calc) | **A** — FAO report (stale, ~2yr) |
| Fleet size | **A** | **A** |

Both are annual-only for practical purposes. The Ontario **FAO Transit Subsidies report** has pre-computed farebox/recovery for MiWay + Burlington, but it's a one-off (data through 2022, published 2024) — not a recurring feed.

---

## What this means for the product

**You can credibly market "monthly-updated transit data"** because the headline metric — ridership — is monthly for 7 of 10 agencies. That's the number people check. Frame it like a stock ticker:

- **Ridership** = the live price. Updates monthly. ~2-month lag is fine (StatCan, open data).
- **Revenue** = updates monthly (big agencies via StatCan) to quarterly (TransLink, OC Transpo).
- **The fundamentals** (farebox recovery, cost per rider, cost per hour, subsidy per rider, fleet) = annual "earnings." Refresh once a year when audited statements drop. TransLink is the one agency where these go quarterly.

**Per-metric freshness is a feature, not an apology.** Show "Ridership · as of Mar 2026" next to "Farebox recovery · FY2024" and it reads as rigor, not staleness — same as a stock page showing live price + last-quarter earnings.

**Carry-forward (display only).** When a metric's newest value is older than the current bucket
(e.g. the FY2024 balance sheet while FY2025 ridership is in), the website **carries the last
known value forward** into the headline, labelled "as of FY2024 · carried forward" with the amber
stale-feed treatment. It is **never** written into the database (no fabricated rows), **never**
ranked, and trend charts show a **gap** rather than a flat line. Blanks in the Excel workbook stay
blank — the website carries forward, the editor never types a guessed number. Full rule in
[balance-sheet-and-frequency-plan.md §3](../planning/balance-sheet-and-frequency-plan.md).

---

## Ingestion refresh cadence (what runs when)

| Adapter | Runs | Pulls | Covers |
|---|---|---|---|
| **StatCan 23-10-0307** | Monthly (after ~20th) | Ridership + revenue | TTC, STM, TransLink, Metrolinx(GTHA), Calgary, Edmonton, BC Transit(Victoria) |
| **Edmonton open data** | Monthly | Ridership + service hours | Edmonton |
| **Calgary open data** | Monthly | Ridership + fleet | Calgary |
| **TTC CEO Report** | Monthly | Ridership, revenue, OTP, service hours | TTC |
| **TransLink quarterly** | Quarterly | Full financials + farebox + OTP | TransLink |
| **OC Transpo KPI scrape** | Monthly | Ridership (HTML scrape) | OC Transpo |
| **OC Transpo budget status** | Quarterly | Revenue + expense variance | OC Transpo |
| **Metrolinx ops report** | Quarterly | Ridership, OTP | Metrolinx/GO |
| **Annual report PDFs** | Annual | Expenses, farebox, fleet, service hours | ALL agencies (the slow layer) |
| **MiWay / Burlington / BC Transit** | Annual | Everything | These three are annual-only |

**Schema requirement:** `reporting_periods.period_type` must support `monthly | quarterly | annual_calendar | annual_fiscal` *simultaneously per agency* — TransLink will have monthly ridership AND quarterly expenses AND annual fleet, all live at once. The schema already handles this; this just confirms it's load-bearing.

---

## Key source URLs

- StatCan 23-10-0307-01: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2310030701
- TTC CEO Report: https://www.ttc.ca/about-the-ttc/Transparency-and-accountability
- TransLink quarterly reports: https://www.translink.ca/about-us/about-translink/corporate-reports
- Metrolinx annual/board reports: https://www.metrolinx.com/en/about-us/annual-reports
- STM monthly indicators: https://www.stm.info/en/about/financial_and_corporate_information/performance-indicators
- Calgary monthly ridership: https://data.calgary.ca/Transportation-Transit/Monthly-Ridership-By-Year/nypk-snzd
- Edmonton monthly ridership: https://data.edmonton.ca/Transit/Transit-Ridership/wj6v-epas
- OC Transpo KPIs: https://octranspo.com/en/about-us/transparency/kpis/
- FAO Ontario transit subsidies (MiWay/Burlington farebox): https://fao-on.org/en/report/transit-subsidies-2024/

---

*Confidence: High where confirmed via StatCan API and direct PDF reads (StatCan coverage, Edmonton/Calgary datasets, TransLink quarterly, TTC CEO Report, MiWay/Ottawa open-data gaps). Medium where based on report titles not opened directly (some service-hour cadences).*
