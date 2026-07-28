# TransitIndex — Source Registry
**Version:** 0.1 (pre-build)  
**Purpose:** Every launch agency × every universal metric × the specific source that supplies it.  
This document drives ingestion adapter prioritization and is the legal record of what we're allowed to use commercially.

---

## How to read this

- **Tier 0** — Structured, API/CSV, auto-ingestible, no human review needed.
- **Tier 1** — Structured per-agency, scriptable with one parser per agency/source, minimal human review.
- **Tier 2** — PDF, requires LLM-assisted extraction + human review queue.
- **⚠ RESTRICTED** — License issue; do NOT use as a cited public source in the product.
- **❓ UNKNOWN** — Source not confirmed; needs manual verification before build.
- **— (dash)** — Metric not applicable to this agency type.
- **[ ]** — Applicable but source not yet identified; genuine white space.

Derived metrics (farebox recovery ratio, cost per rider, cost per hour, subsidy per rider) are **calculated** from their components — they are not fetched independently unless a primary source publishes them directly, in which case we store both the raw figure and the cited published value as a cross-check.

---

## Universal Metrics Reference

| Code | Metric | Unit | Definition |
|---|---|---|---|
| `annual_ridership` | Annual Unlinked Passenger Trips | count | Total boardings, conventional service |
| `operating_expenses` | Total Operating Expenses | CAD | All costs to operate the service |
| `operating_revenue` | Total Operating Revenue (Farebox) | CAD | Fare revenue + other operating income |
| `farebox_recovery_ratio` | Farebox Recovery Ratio | % | Operating Revenue / Operating Expenses |
| `revenue_service_hours` | Revenue Service Hours | hours | Vehicle hours in revenue service |
| `cost_per_hour` | Operating Cost per Revenue Hour | CAD/hr | Operating Expenses / Revenue Service Hours |
| `cost_per_rider` | Operating Cost per Rider | CAD | Operating Expenses / Ridership |
| `subsidy_per_rider` | Subsidy per Rider | CAD | (Expenses − Revenue) / Ridership |
| `fleet_size` | Total Fleet Size (Active) | count | Revenue vehicles in active fleet |
| `vehicle_revenue_km` | Revenue Vehicle Kilometres | km | Vehicle distance in revenue service |
| `average_fare` | Average Fare per Trip | CAD | *(derived)* Operating Revenue ÷ Ridership |
| `trips_per_revenue_hour` | Trips per Revenue Hour | trips/hr | *(derived)* Ridership ÷ Revenue Service Hours |
| `on_time_performance` | On-Time Performance | % | Share of scheduled service delivered on time |
| `total_operating_subsidy` | Total Operating Subsidy | CAD | Government funding covering the operating gap |
| `labour_cost` | Labour Cost (Wages + Benefits) | CAD | Employee wages and benefits (largest expense line) |
| `energy_fuel_cost` | Energy / Fuel Cost | CAD | Fuel and traction power |
| `materials_services_cost` | Materials & Contracted Services | CAD | Maintenance materials + contracted services |
| `fleet_average_age` | Average Fleet Age | years | Mean age of active revenue vehicles |
| `accessible_fleet_pct` | Accessible Fleet Share | % | Share of active fleet that is accessible |
| `capital_expenditure` | Capital Expenditure | CAD | Spending on vehicles and infrastructure |

> **Catalog = 20 metrics (updated 2026-05-30):** the original 9 backbone + 11 financial-statement/asset
> metrics. The 6 *(derived)* rows compute from their inputs. The added sourced metrics (subsidy, labour,
> energy, materials, vehicle-km, on-time, fleet age, accessible %) are primarily **Tier 2** (annual-report
> PDF, Milestone 2) — same source as `operating_expenses` for each agency; their per-agency source cells in
> the matrices below are **not yet enumerated** (deferred — treat as the agency's annual report unless a
> structured feed is found). Full types + direction cues in lane-0-foundation-spec.md.
> Also note: the *Typology:* label in each agency section below is **descriptive only** — typology was
> dropped as a stored field 2026-05-30.

> **Balance-sheet expansion (2026-05-31, [balance-sheet-and-frequency-plan.md](../planning/balance-sheet-and-frequency-plan.md)):**
> +11 metrics → catalog of **31**. The 8 sourced balance-sheet lines (`total_financial_assets`,
> `total_liabilities`, `total_non_financial_assets`, `total_assets`, `tangible_capital_assets`,
> `accumulated_surplus`, `long_term_debt`, `cash_and_investments`) come from each agency's
> **audited statement of financial position** — i.e. the **annual report PDF** (`annual_report_pdfs`,
> Tier 2), same source class as `operating_expenses`. **TransLink** also publishes a *quarterly*
> statement of financial position (`translink_quarterly`). **MiWay → City of Mississauga** and
> **Burlington Transit → City of Burlington** appear only inside the municipality's **consolidated
> annual financial statements** — extract the transit segment if broken out, otherwise record
> nothing and flag the gap (never attribute the whole city's balance sheet to transit). Per-agency
> source cells for these lines are **not yet enumerated** (treat as the agency's audited AFS until a
> structured feed is found). `net_debt`/`debt_to_assets`/`net_debt_per_capita` are **CALC**.

---

## Source Catalog

Every source referenced in the matrix below is defined here with license and access method.

### Tier 0 — Auto-ingestible

| ID | Source | Agency Coverage | License | Format | URL | Notes |
|---|---|---|---|---|---|---|
| **SC-251** | StatCan 23-10-0251-01 | National / Provincial | StatCan Open Licence (commercial OK, attribution required) | CSV + API | https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2310025101 | Monthly. Revenue + ridership. No agency breakdown. Use SC-307 instead. |
| **SC-307** | StatCan 23-10-0307-01 | ~20 major agencies | StatCan Open Licence (commercial OK, attribution required) | CSV + API | https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=2310030701 | Monthly by agency. **Primary source for ridership + operating revenue.** Covers TTC, STM, TransLink, Calgary, Edmonton; **Metrolinx at GTHA level only** (not GO-specific); **BC Transit Victoria system only**. Does **NOT** cover OC Transpo, MiWay, or Burlington. (Corrected per update-frequency.md — supersedes the earlier assumption.) |

### Tier 1 — Per-agency structured

| ID | Source | Agency | License | Format | URL | Notes |
|---|---|---|---|---|---|---|
| **TOR-OD** | Toronto Open Data — TTC datasets | TTC | OGL – Toronto (commercial OK) | CSV | https://open.toronto.ca/dataset/ttc-bus-delay-data/ (and related) | Multiple ridership/service datasets. Confirm which tables cover financials. |
| **MTL-OD** | Données ouvertes Montréal | STM | OGL – Montréal (commercial OK) | CSV | https://donnees.montreal.ca/ | Check for ridership and service-hours CSV. Annual report is cleaner for financials. |
| **YVR-OD** | Metro Vancouver / TransLink Open Data | TransLink | OGL – Metro Vancouver (commercial OK, GTFS has commercial-fee risk — separate) | CSV | https://www.translink.ca/about-us/doing-business-with-translink/app-developer-resources | Ridership data available. GTFS: TransLink reserves right to charge commercial users — flag for Pro tier. |
| **YOW-OD** | Ottawa Open Data | OC Transpo | OGL – Ottawa (commercial OK) | CSV | https://open.ottawa.ca/ | Monthly ridership. Annual budget CSVs. |
| **YYC-OD** | Calgary Open Data | Calgary Transit | OGL – Alberta lineage (commercial OK) | CSV | https://data.calgary.ca/ | Monthly ridership and service hours available. |
| **YEG-OD** | Edmonton Open Data | Edmonton ETS | OGL – Edmonton (commercial OK) | CSV | https://data.edmonton.ca/ | Ridership CSVs. Check for service hours. |
| **MIS-OD** | City of Mississauga Open Data | MiWay | OGL – Mississauga (commercial OK) | CSV | https://www.mississauga.ca/city-of-mississauga-open-data-catalogue/ | Confirm coverage — may not have financials. |

### Tier 2 — PDF (LLM-assisted extraction + human review)

| ID | Source | Agency | License | Format | Typical URL pattern | Fiscal Year |
|---|---|---|---|---|---|---|
| **TTC-AR** | TTC Annual Report | TTC | Public document (facts free to use; no redistribution restriction stated) | PDF | https://www.ttc.ca/about-the-ttc/annual-reports | Calendar (Jan–Dec) |
| **TTC-CEO** | TTC CEO Report (monthly board deck) | TTC | Public document | PDF | https://www.ttc.ca/about-the-ttc/governance/board-meetings | Monthly. Rich operational stats. |
| **STM-AR** | STM Rapport Annuel | STM | Public document | PDF (French) | https://www.stm.info/en/about/corporate-governance/annual-reports | Calendar |
| **TL-AR** | TransLink Annual Report | TransLink | Public document | PDF | https://www.translink.ca/about-us/corporate-overview/annual-report | Calendar |
| **MTX-AR** | Metrolinx Annual Report | Metrolinx/GO | Public document | PDF | https://www.metrolinx.com/en/about-us/corporate-documents/annual-report | Fiscal Apr–Mar |
| **MTX-BP** | Metrolinx Business Plan | Metrolinx | Public document | PDF | https://www.metrolinx.com/en/about-us/corporate-documents/business-plan | Apr–Mar |
| **OCT-AR** | OC Transpo Annual Report / City of Ottawa Annual Report | OC Transpo | Public document | PDF | https://ottawa.ca/en/city-hall/finance-and-corporate-services/financial-reports | Calendar |
| **YYC-AR** | City of Calgary Annual Report | Calgary Transit | Public document | PDF | https://www.calgary.ca/cfod/finance/annual-report.html | Calendar |
| **YEG-AR** | City of Edmonton Annual Report | Edmonton ETS | Public document | PDF | https://www.edmonton.ca/city_government/city_finances/annual-report | Calendar |
| **MIS-AR** | City of Mississauga Annual Report / Budget | MiWay | Public document | PDF | https://www.mississauga.ca/business-and-finance/budget-and-finances/ | Calendar |
| **BCT-AR** | BC Transit Annual Report | BC Transit | Public document | PDF | https://www.bctransit.com/about/annual-reports | Fiscal Apr–Mar |
| **BUR-BUD** | City of Burlington Budget Documents | Burlington Transit | Public document | PDF | https://www.burlington.ca/en/your-city/budget.aspx | Calendar |

### Restricted / Reference Only

| ID | Source | Status | Notes |
|---|---|---|---|
| **CUTA-STATS** | CUTA Canadian Transit Statistics (formerly "Fact Book") | ⚠ RESTRICTED | Members-only, paid. Anti-derivation terms likely prohibit use in a commercial data product. Use ONLY as a private cross-check — never as a cited public source. Contact: techservices@cutaactu.ca |

---

## Agency × Metric Matrix

### Legend
`0-SC307` = Tier 0, StatCan table  
`1-YYC-OD` = Tier 1, open data portal  
`2-TTC-AR` = Tier 2, PDF annual report  
`CALC` = derived from other metrics  
`—` = not applicable  
`[ ]` = applicable, source not yet confirmed (white space)  

---

### 1. TTC (Toronto Transit Commission)
*Typology: Major Multimodal | Modes: Bus, Subway, Streetcar, Paratransit (Wheel-Trans) | FY: Calendar*

| Metric | Primary Source | Backup Source | Tier | Notes |
|---|---|---|---|---|
| `annual_ridership` | **SC-307** | TOR-OD, TTC-CEO | 0 | StatCan monthly → sum to annual. Split by mode via TTC-CEO. |
| `operating_expenses` | **TTC-AR** | OCT-AR | 2 | Broken out by mode in annual report. Also appears in City of Toronto budget. |
| `operating_revenue` | **SC-307** | TTC-AR | 0/2 | StatCan gives farebox only; TTC-AR adds other operating income. |
| `farebox_recovery_ratio` | **CALC** (revenue/expenses) | TTC-AR publishes directly | CALC | Cross-check against published figure in annual report. |
| `revenue_service_hours` | **TTC-CEO** | TTC-AR | 2 | Monthly CEO Report publishes RSH by mode. Annual report has annual total. |
| `cost_per_hour` | **CALC** | — | CALC | |
| `cost_per_rider` | **CALC** | — | CALC | |
| `subsidy_per_rider` | **CALC** | — | CALC | Subsidy = expenses − revenue. City of Toronto subsidy figure in budget docs. |
| `fleet_size` | **TTC-AR** | TTC-CEO | 2 | Annual report has fleet roster by mode. |

---

### 2. STM (Société de transport de Montréal)
*Typology: Major Multimodal | Modes: Bus, Métro | FY: Calendar*

| Metric | Primary Source | Backup Source | Tier | Notes |
|---|---|---|---|---|
| `annual_ridership` | **SC-307** | MTL-OD, STM-AR | 0 | StatCan covers STM. |
| `operating_expenses` | **STM-AR** | — | 2 | Rapport annuel in French — parser must handle French formatting. |
| `operating_revenue` | **SC-307** | STM-AR | 0/2 | |
| `farebox_recovery_ratio` | **CALC** | STM-AR publishes directly | CALC | |
| `revenue_service_hours` | **STM-AR** | — | 2 | Published in the annual report. |
| `cost_per_hour` | **CALC** | — | CALC | |
| `cost_per_rider` | **CALC** | — | CALC | |
| `subsidy_per_rider` | **CALC** | — | CALC | Subsidy from Québec government + island of Montréal. STM-AR. |
| `fleet_size` | **STM-AR** | — | 2 | |

⚠ Sourcing (STM-AR): recent reports are served as interactive web pages with bot protection — a naive HTTP GET returns HTML, not a PDF. Fetch the direct PDF asset URLs (`stm.info/sites/default/files/...`) or use a real headless browser. Reports are French: "Rapport financier annuel" = the audited financials (**the extraction source**); "Rapport annuel / d'activité" = the activity report. File-naming convention (catalog.py): `stm-<year>.pdf` = financial report, `stm-activity-<year>.pdf` = activity report; both are STM-authored [T].

---

### 3. TransLink (Metro Vancouver)
*Typology: Major Multimodal | Modes: Bus, SkyTrain (Expo/Millennium/Canada Lines), SeaBus, West Coast Express, HandyDART | FY: Calendar*

| Metric | Primary Source | Backup Source | Tier | Notes |
|---|---|---|---|---|
| `annual_ridership` | **SC-307** | YVR-OD, TL-AR | 0 | |
| `operating_expenses` | **TL-AR** | — | 2 | TransLink publishes consolidated + by mode. |
| `operating_revenue` | **SC-307** | TL-AR | 0/2 | |
| `farebox_recovery_ratio` | **CALC** | TL-AR | CALC | |
| `revenue_service_hours` | **TL-AR** | YVR-OD | 2/1 | Check if open data has service hours. |
| `cost_per_hour` | **CALC** | — | CALC | |
| `cost_per_rider` | **CALC** | — | CALC | |
| `subsidy_per_rider` | **CALC** | — | CALC | Subsidy sources: BC government, Mayors' Council, property tax levy. |
| `fleet_size` | **TL-AR** | — | 2 | |

⚠ GTFS commercial note: TransLink GTFS has a commercial-fee clause. Use open data portal CSVs for metrics — don't rely on GTFS for anything in the paid tier until terms are confirmed.

---

### 4. Metrolinx / GO Transit
*Typology: Regional Rail | Modes: Commuter Rail, Bus | FY: **April 1 – March 31** (Ontario fiscal year)*

| Metric | Primary Source | Backup Source | Tier | Notes |
|---|---|---|---|---|
| `annual_ridership` | **MTX-AR** | SC-307 | 2/0 | Non-calendar FY — StatCan row alignment needs care. Annual report primary. |
| `operating_expenses` | **MTX-AR** | MTX-BP | 2 | |
| `operating_revenue` | **MTX-AR** | SC-307 | 2/0 | |
| `farebox_recovery_ratio` | **CALC** | MTX-AR | CALC | GO Transit historically has very low farebox recovery (~35–45%). |
| `revenue_service_hours` | **MTX-AR** | MTX-BP | 2 | Reported as train-km + bus-km; convert or store both. |
| `cost_per_hour` | **CALC** | — | CALC | |
| `cost_per_rider` | **CALC** | — | CALC | |
| `subsidy_per_rider` | **CALC** | — | CALC | Province of Ontario subsidy dominant; in annual report. |
| `fleet_size` | **MTX-AR** | — | 2 | Rail cars + locomotives + buses separately. |

⚠ FY alignment: When displaying Metrolinx alongside calendar-year agencies, label as "FY2024-25" and surface the mismatch flag in the compare view.

---

### 5. OC Transpo (Ottawa)
*Typology: Mid-size Bus + LRT | Modes: Bus, O-Train (LRT) | FY: Calendar*

| Metric | Primary Source | Backup Source | Tier | Notes |
|---|---|---|---|---|
| `annual_ridership` | **OC Transpo KPI page** (octranspo.com — monthly, HTML/PDF scrape) | YOW-OD | 2 | **Not in SC-307.** Monthly ridership is HTML/PDF (needs a scraper), not a clean CSV. Per update-frequency.md. |
| `operating_expenses` | **OCT-AR** | City of Ottawa Budget (PDF) | 2 | OC Transpo section of City Annual Report. |
| `operating_revenue` | **OCT-AR / Ottawa budget status reports** (quarterly) | YOW-OD | 2 | **Not in SC-307.** Revenue via quarterly budget status reports. Per update-frequency.md. |
| `farebox_recovery_ratio` | **CALC** | OCT-AR | CALC | Notably low post-LRT issues (2019–2022 period). |
| `revenue_service_hours` | **OCT-AR** | YOW-OD | 2/1 | |
| `cost_per_hour` | **CALC** | — | CALC | |
| `cost_per_rider` | **CALC** | — | CALC | |
| `subsidy_per_rider` | **CALC** | — | CALC | City of Ottawa subsidy in budget docs. |
| `fleet_size` | **OCT-AR** | — | 2 | |

---

### 6. Calgary Transit
*Typology: Mid-size Bus + LRT | Modes: Bus, CTrain (LRT) | FY: Calendar*

| Metric | Primary Source | Backup Source | Tier | Notes |
|---|---|---|---|---|
| `annual_ridership` | **SC-307** | YYC-OD | 0 | Calgary Open Data has a good monthly ridership dataset. |
| `operating_expenses` | **YYC-AR** | YYC-OD | 2/1 | City annual report; check if budget CSV has operating expenses. |
| `operating_revenue` | **SC-307** | YYC-OD | 0 | |
| `farebox_recovery_ratio` | **CALC** | YYC-AR | CALC | |
| `revenue_service_hours` | **YYC-OD** | YYC-AR | 1/2 | Calgary Open Data publishes service stats — verify RSH is included. |
| `cost_per_hour` | **CALC** | — | CALC | |
| `cost_per_rider` | **CALC** | — | CALC | |
| `subsidy_per_rider` | **CALC** | — | CALC | |
| `fleet_size` | **YYC-AR** | — | 2 | |

---

### 7. Edmonton Transit Service (ETS)
*Typology: Mid-size Bus + LRT | Modes: Bus, LRT (Metro Line, Valley Line) | FY: Calendar*

| Metric | Primary Source | Backup Source | Tier | Notes |
|---|---|---|---|---|
| `annual_ridership` | **SC-307** | YEG-OD | 0 | |
| `operating_expenses` | **YEG-AR** | YEG-OD | 2/1 | City annual report; check open data for budget breakdowns. |
| `operating_revenue` | **SC-307** | YEG-OD | 0 | |
| `farebox_recovery_ratio` | **CALC** | YEG-AR | CALC | |
| `revenue_service_hours` | **YEG-OD** | YEG-AR | 1/2 | Edmonton Open Data has transit performance datasets — verify RSH. |
| `cost_per_hour` | **CALC** | — | CALC | |
| `cost_per_rider` | **CALC** | — | CALC | |
| `subsidy_per_rider` | **CALC** | — | CALC | |
| `fleet_size` | **YEG-AR** | — | 2 | |

---

### 8. MiWay (City of Mississauga)
*Typology: Mid-size Bus | Modes: Bus only | FY: Calendar*

| Metric | Primary Source | Backup Source | Tier | Notes |
|---|---|---|---|---|
| `annual_ridership` | **MIS-AR** (City of Mississauga budget/annual) | — | 2 | **Confirmed NOT in SC-307**, and MIS-OD has routes/stops/GTFS only — no ridership dataset. Effectively annual-only despite ~38M trips. Per update-frequency.md. |
| `operating_expenses` | **MIS-AR** | MIS-OD | 2/1 | City of Mississauga Annual Report or Budget. |
| `operating_revenue` | **MIS-AR** | — | 2 | **Not in SC-307.** Annual via city budget. |
| `farebox_recovery_ratio` | **CALC** | MIS-AR | CALC | |
| `revenue_service_hours` | **MIS-AR** | MIS-OD | 2/1 | Check Mississauga Open Data for service stats. |
| `cost_per_hour` | **CALC** | — | CALC | |
| `cost_per_rider` | **CALC** | — | CALC | |
| `subsidy_per_rider` | **CALC** | — | CALC | |
| `fleet_size` | **MIS-AR** | — | 2 | |

⚠ Sourcing (MIS-AR): the good document is the **City of Mississauga "Financial and Sustainability Report"** on mississauga.ca (behind numeric, unguessable paths — navigate the city finance reports page to find it). MiWay's own "Report to the Community" is glossy and **lacks audited financials** — do not use it as the extraction source.

---

### 9. BC Transit
*Typology: Hybrid (Multi-system operator) | Modes: Bus (conventional + community) | FY: **April 1 – March 31***

| Metric | Primary Source | Backup Source | Tier | Notes |
|---|---|---|---|---|
| `annual_ridership` | **BCT-AR** | SC-307 (Victoria only) | 2/0 | ⚠ BC Transit operates ~60 systems under one umbrella. Annual report gives **system-wide** totals; **SC-307 covers only the Victoria system** — different scope, do not conflate (set `service_scope` accordingly). Model as parent agency with children. |
| `operating_expenses` | **BCT-AR** | BC government budget | 2 | Consolidated in annual report. |
| `operating_revenue` | **BCT-AR** | SC-307 | 2/0 | |
| `farebox_recovery_ratio` | **CALC** | BCT-AR | CALC | |
| `revenue_service_hours` | **BCT-AR** | — | 2 | |
| `cost_per_hour` | **CALC** | — | CALC | |
| `cost_per_rider` | **CALC** | — | CALC | |
| `subsidy_per_rider` | **CALC** | — | CALC | Provincial subsidy dominant; from BC government budget. |
| `fleet_size` | **BCT-AR** | — | 2 | System-wide. |

⚠ Parent-agency complexity: BC Transit's `parent_agency_id` should reference a future "BC Transit – Victoria" or community-level sub-agency if/when we break it out. For launch, model as one agency with a note.

---

### 10. Burlington Transit
*Typology: Small Local Bus | Modes: Bus only | FY: Calendar*

| Metric | Primary Source | Backup Source | Tier | Notes |
|---|---|---|---|---|
| `annual_ridership` | **BUR-BUD** | [ ] | 2 | ⚠ Burlington is almost certainly NOT in SC-307 (too small). Budget documents are the primary source. Ridership in annual budget reports. |
| `operating_expenses` | **BUR-BUD** | — | 2 | City of Burlington budget breakdown has transit line item. |
| `operating_revenue` | **BUR-BUD** | — | 2 | |
| `farebox_recovery_ratio` | **CALC** | BUR-BUD | CALC | Small agencies often publish this in budget docs. |
| `revenue_service_hours` | **BUR-BUD** | [ ] | 2 | ❓ May not be published at all — genuine white space. |
| `cost_per_hour` | **CALC** | — | CALC | Only calculable if RSH is found. |
| `cost_per_rider` | **CALC** | — | CALC | |
| `subsidy_per_rider` | **CALC** | — | CALC | |
| `fleet_size` | **BUR-BUD** | [ ] | 2 | Sometimes in budget docs; otherwise needs direct outreach or annual report. |

⚠ Small-agency white space: Revenue service hours is the most likely gap for Burlington. If not in budget docs, this is a genuine null — mark the field as "not reported" and suppress the derived metrics (cost/hour) rather than estimating.

---

## White Space Summary

These are the genuine gaps — metrics that are applicable but don't have a confirmed source yet.

| Agency | Metric | Status | Action |
|---|---|---|---|
| Burlington Transit | `revenue_service_hours` | ❓ No known public source | Check budget docs manually; if absent, mark as not-reported |
| Burlington Transit | `fleet_size` | ❓ May not be in budget docs | Check Burlington Transit website / budget appendices |
| All agencies | Mode-level ridership split | PDF-only for all | TTC CEO Report is best-in-class; most others only in annual reports |
| MiWay | SC-307 coverage | ✅ Resolved — NOT in SC-307 | Confirmed absent (update-frequency.md). No monthly ridership source exists; use MIS-AR (annual). |
| BC Transit | Sub-system breakdown | Not in scope (Phase 1) | Model as one agency for now; sub-systems in later phase |
| STM | French PDF parsing | Tier 2 complexity | Ensure LLM extraction prompt handles French number formatting (e.g. "1 234 567" with spaces) |

---

## Ingestion Adapter Build Order

Based on effort-to-coverage ratio — **build in this sequence:**

1. **SC-307 adapter** (Tier 0) → covers ridership + operating revenue for **7 of 10** agencies (TTC, STM, TransLink, Calgary, Edmonton; Metrolinx@GTHA, BC Transit@Victoria). **Not** OC Transpo, MiWay, or Burlington — those need agency-native sources. One adapter, runs as a cron. ~1–2 days work.
2. **Calgary + Edmonton open data adapters** (Tier 1) → adds service hours for two agencies. ~0.5 days each.
3. **TTC-CEO monthly PDF adapter** (Tier 2) → adds operating expenses, RSH, fleet, mode splits for Canada's largest agency. Sets the pattern for all PDF adapters. ~3–5 days (includes building the review queue UI).
4. **Annual report PDF adapters** (Tier 2, per agency) → operating expenses + fleet for all remaining agencies. Use TTC-CEO adapter as the template. ~1–2 days per agency after the framework exists.
5. **Burlington budget adapter** (Tier 2, manual-assist) → small agency, small data, may have white space in RSH. Do this last.
6. **BC Transit annual report** (Tier 2, fiscal year handling) → validates the non-calendar-FY ingestion path.
7. **Metrolinx annual report** (Tier 2, fiscal year + commuter-rail metrics) → validates the regional-rail mode path.

---

## Attribution Requirements

Every rendered metric value must carry an attribution notice. Required text by source:

| Source | Required Attribution |
|---|---|
| StatCan | "Source: Statistics Canada, [table name and number], [reference date]. Reproduced and distributed on an 'as is' basis with the permission of Statistics Canada." |
| Toronto Open Data | "Contains information licensed under the Open Government Licence – Toronto." |
| Ottawa Open Data | "Contains information licensed under the Open Government Licence – Ottawa." |
| Calgary / Edmonton | "Contains information licensed under the Open Government Licence – [City]." |
| Montréal Open Data | "Données reproduites avec la permission de la Ville de Montréal." |
| Metro Vancouver / TransLink Open Data | "Contains information licensed under the Open Government Licence – Metro Vancouver." |
| Agency PDFs | "Source: [Agency Name], [Document Title], [Publication Year], p.[page]." |

---

*Last updated: 2026-05-29 | Status: Pre-build draft — sources need verification against live URLs before adapter development begins.*
