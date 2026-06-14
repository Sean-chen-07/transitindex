<!-- AUTO-GENERATED from ingest/transitindex_ingest/metric_dictionary.yaml. Do not hand-edit: run `python -m transitindex_ingest.dictionary` to regenerate. -->

# TransitIndex — Data Dictionary

A precise, plain-language spec for every metric: what it is, what it is not, where it comes from, and the equations it links into. This file is the single source that drives PDF-extraction prompts, FOI request templates, and the spreadsheet's inline definitions.

## All metrics at a glance

| Metric | Plain meaning | Unit | Kind | Formula | Source |
|---|---|---|---|---|---|
| Ridership | Boardings (unlinked passenger trips), at the period shown. | count | Sourced | — | statcan |
| Revenue Service Hours | Hours vehicles spent in service carrying (or available to carry) passengers. | hours | Sourced | — | annual_report |
| Vehicle Revenue Kilometres | Distance vehicles travelled while in passenger service. | km | Sourced | — | annual_report |
| Average Fare | Revenue collected per rider (boarding). | CAD | Calculated | operating_revenue / ridership | derived |
| Trips per Revenue Hour | Riders carried per hour of service — a productivity measure. | trips/hr | Calculated | ridership / revenue_service_hours | derived |
| On-Time Performance | Share of scheduled service that ran on time. | % | Sourced | — | annual_report |
| Operating Revenue | Money earned from fares and other operations (excludes subsidy). | CAD | Sourced | — | statcan |
| Operating Expenses | Total cost to run the service for the period. | CAD | Sourced | — | annual_report |
| Total Operating Subsidy | Government funding covering the gap between operating cost and revenue. | CAD | Sourced | — | annual_report |
| Labour Cost | Wages, salaries, and benefits for staff. | CAD | Sourced | — | annual_report |
| Energy & Fuel Cost | Spending on fuel and electricity to move the vehicles. | CAD | Sourced | — | annual_report |
| Materials & Services Cost | Maintenance materials plus contracted-out services. | CAD | Sourced | — | annual_report |
| Farebox Recovery Ratio | Share of operating cost covered by fares/operating revenue. | % | Calculated | operating_revenue / operating_expenses | derived |
| Cost per Rider | Operating cost for each trip taken. | CAD | Calculated | operating_expenses / ridership | derived |
| Cost per Revenue Hour | Operating cost for each hour of service. | CAD/hr | Calculated | operating_expenses / revenue_service_hours | derived |
| Subsidy per Rider | Public subsidy needed for each trip taken. | CAD | Calculated | total_operating_subsidy / ridership | derived |
| Fleet Size | Number of active revenue vehicles in the fleet. | count | Sourced | — | annual_report |
| Fleet Average Age | Average age of the active vehicles. | years | Sourced | — | annual_report |
| Accessible Fleet % | Share of the active fleet that is wheelchair-accessible. | % | Sourced | — | annual_report |
| Fleet scale | A rail-weighted count of the fleet, so a metro car is not equated with a bus. | count | Sourced | — | annual_report |
| Capital Expenditure | Spending on long-term assets (vehicles, facilities, infrastructure). | CAD | Sourced | — | annual_report |
| Total Financial Assets | Cash, investments, and money owed to the agency — what could become cash. | CAD | Sourced | — | annual_report |
| Total Liabilities | Everything the agency owes — debt, payables, employee future benefits. | CAD | Sourced | — | annual_report |
| Total Non-Financial Assets | Assets the agency uses rather than sells — mainly vehicles, buildings, equipment. | CAD | Sourced | — | annual_report |
| Total Assets | Everything the agency owns (financial + non-financial combined). | CAD | Sourced | — | annual_report |
| Tangible Capital Assets | Net book value of vehicles, buildings, track and equipment (after depreciation). | CAD | Sourced | — | annual_report |
| Accumulated Surplus | The agency's bottom-line net worth, built up over time (assets − liabilities). | CAD | Sourced | — | annual_report |
| Long-Term Debt | Money borrowed that is repaid over more than a year (bonds, loans). | CAD | Sourced | — | annual_report |
| Cash & Investments | Cash on hand plus investments — the agency's liquidity. | CAD | Sourced | — | annual_report |
| Net Debt | What the agency owes beyond what its financial assets cover (lower is healthier). | CAD | Calculated | total_liabilities - total_financial_assets | derived |
| Debt to Assets | Share of everything the agency owns that is financed by what it owes. | % | Calculated | total_liabilities / total_assets | derived |
| Net Debt per Capita | Net debt divided by the population the agency serves — debt per resident. | CAD | Calculated | net_debt / service_area_population | derived |

## Metric specifications

### Ridership (`ridership`)

- **Is:** The number of unlinked passenger trips (boardings) on the system. One rider counts as one trip each time they board a vehicle, so a journey with one transfer is two boardings. Held at whatever period the source reports — monthly, quarterly, or annual — with the annual figure being the sum of the twelve months when all twelve are present.
- **Is NOT:** NOT the number of distinct people (riders), and NOT linked trips/journeys (a journey with a transfer is one journey but two boardings). NOT fare-paying passengers only — it includes transfers, passes, and free riders unless a source explicitly says otherwise.
- **Unit:** count (count)
- **Period:** Native monthly for most large agencies (StatCan 23-10-0307) and quarterly/annual elsewhere. Period granularity is a DIMENSION of the value, not part of the metric name: the same `ridership` metric holds monthly, quarterly, and annual values. Annual = sum of the twelve calendar/fiscal months; an incomplete year is a partial year-to-date value, never a full year, and a year-to-date value is never ranked against full years.
- **Includes:** All boardings across all modes (bus, rail, ferry, paratransit) unless scoped; Transfers, pass holders, concession and free riders
- **Excludes:** Distinct-rider counts; Linked journeys (a transfer trip counted once); Year-to-date cumulative totals stored as a monthly value
- **Labels (EN):** Ridership; Boardings; Revenue passengers; Unlinked passenger trips; Total passenger trips
- **Labels (FR):** Achalandage; Déplacements; Montées (déplacements non liés); Voyages
- **Where in a report:** Operating/ridership statistics table near the front of the annual report, the CEO/board ridership update, agency open-data feeds, or StatCan table 23-10-0307.
- **Common confusions:**
  - Unlinked (boardings) vs linked (journeys) — TransitIndex wants UNLINKED boardings
  - Boardings vs distinct riders — these are not the same number
  - Calendar year vs fiscal year — Metrolinx and BC Transit report Apr–Mar
  - Revenue-passenger counts that exclude transfers/free riders vs total boardings
  - A single month vs a year-to-date cumulative figure reported mid-year
- **Equations:** `average_fare_def`, `cost_per_rider_def`, `subsidy_per_rider_def`, `trips_per_revenue_hour_def`
- **Source tier:** statcan

### Revenue Service Hours (`revenue_service_hours`)

- **Is:** The total hours vehicles operated in revenue service — i.e. on a published route available to carry passengers. The standard denominator for service-productivity and cost-per-hour measures.
- **Is NOT:** NOT total vehicle hours: it EXCLUDES deadhead (pull-in/pull-out), layover where defined out, training, and maintenance movements. NOT platform hours unless the agency defines them identically.
- **Unit:** hours (time)
- **Period:** Usually annual; a few agencies publish it monthly/quarterly. Annual is the sum of the reported sub-periods.
- **Includes:** In-service revenue operation across all revenue modes
- **Excludes:** Deadhead / non-revenue movements; Garage, training, and maintenance hours
- **Labels (EN):** Revenue service hours; Revenue vehicle hours; In-service hours; Service hours
- **Labels (FR):** Heures de service en ligne; Heures-véhicules en service; Heures de service productives
- **Where in a report:** Operating statistics / service-supplied table in the annual report; sometimes a service-standards or performance appendix.
- **Common confusions:**
  - Revenue (in-service) hours vs total vehicle hours that include deadhead
  - Vehicle hours vs platform/operator hours
- **Equations:** `cost_per_hour_def`, `trips_per_revenue_hour_def`
- **Source tier:** annual_report

### Vehicle Revenue Kilometres (`vehicle_revenue_km`)

- **Is:** The total kilometres vehicles travelled in revenue service (available to carry passengers). A measure of service supplied by distance.
- **Is NOT:** NOT total fleet kilometres: EXCLUDES deadhead and non-revenue travel. NOT passenger-kilometres (distance travelled by passengers).
- **Unit:** km (distance)
- **Period:** Usually annual; annual is the sum of any reported sub-periods.
- **Includes:** In-service revenue distance across revenue modes
- **Excludes:** Deadhead / non-revenue kilometres; Passenger-kilometres travelled
- **Labels (EN):** Vehicle revenue kilometres; Revenue vehicle kilometres; In-service kilometres
- **Labels (FR):** Kilomètres parcourus en service; Véhicules-kilomètres en service
- **Where in a report:** Operating statistics / service-supplied table in the annual report.
- **Common confusions:**
  - Revenue km vs total km including deadhead
  - Vehicle-kilometres vs passenger-kilometres
- **Source tier:** annual_report

### Average Fare (`average_fare`)

- **Is:** Operating (fare) revenue divided by ridership — the average revenue earned per boarding. A calculated figure, not a posted price.
- **Is NOT:** NOT the posted/advertised adult cash fare. Because it blends passes, concessions, free riders and transfers, average fare is typically well BELOW the cash fare.
- **Unit:** CAD (currency)
- **Formula:** `operating_revenue / ridership`
- **Period:** Matches its inputs' period (same agency, same period).
- **Labels (EN):** Average fare; Revenue per boarding; Average fare recovery
- **Labels (FR):** Tarif moyen; Recette moyenne par déplacement
- **Where in a report:** Calculated by TransitIndex; some reports print it in a KPI table as a cross-check.
- **Common confusions:**
  - Average fare (revenue per boarding) vs the posted adult cash fare — very different
- **Equations:** `average_fare_def`
- **Source tier:** derived

### Trips per Revenue Hour (`trips_per_revenue_hour`)

- **Is:** Ridership divided by revenue service hours — boardings carried for each hour of service supplied. Higher means more productive service.
- **Is NOT:** NOT trips per vehicle and NOT a cost figure. Sensitive to the revenue-hours definition (deadhead must be excluded from the denominator).
- **Unit:** trips/hr (ratio)
- **Formula:** `ridership / revenue_service_hours`
- **Period:** Matches its inputs' period (same agency, same period).
- **Labels (EN):** Boardings per revenue hour; Trips per service hour; Service productivity
- **Labels (FR):** Déplacements par heure de service; Productivité du service
- **Where in a report:** Calculated by TransitIndex; sometimes printed in a performance KPI table.
- **Common confusions:**
  - Per revenue hour vs per vehicle/per operator
- **Equations:** `trips_per_revenue_hour_def`
- **Source tier:** derived

### On-Time Performance (`on_time_performance`)

- **Is:** The percentage of trips (or stops/departures) that met the agency's on-time definition. A service-quality measure, reported as a percentage.
- **Is NOT:** NOT a single universal standard — each agency defines its own on-time window (e.g. 0 to +3 min, or ±1 min), and rail vs bus windows differ. NOT a count; it is a ratio.
- **Unit:** % (ratio)
- **Period:** Monthly to quarterly for large agencies; annual otherwise.
- **Includes:** The agency's own on-time definition (record it in notes)
- **Excludes:** Cancelled trips unless the agency counts them as late
- **Labels (EN):** On-time performance; OTP; Schedule adherence; Service reliability
- **Labels (FR):** Ponctualité; Taux de ponctualité; Respect de l'horaire
- **Where in a report:** Customer/service-performance or KPI scorecard section.
- **Common confusions:**
  - On-time window differs by agency and by mode (±1 vs +3 vs +5 minutes)
  - Schedule adherence vs headway adherence (frequent service measures headway gaps)
- **Source tier:** annual_report

### Operating Revenue (`operating_revenue`)

- **Is:** Revenue the agency earns from operations — passenger fares plus ancillary operating income (advertising, charters, fees). The numerator of farebox recovery.
- **Is NOT:** NOT total revenue: it EXCLUDES government operating subsidy/funding and capital contributions. NOT fares only when ancillary income exists, and NOT gross of refunds.
- **Unit:** CAD (currency)
- **Period:** Monthly for the farebox portion at large agencies (StatCan); the full figure is usually annual from the audited statement of operations.
- **Includes:** Passenger fare revenue (cash, passes, concessions); Ancillary operating income (advertising, charter, fees)
- **Excludes:** Government operating subsidy and funding transfers; Capital grants and contributions
- **Labels (EN):** Operating revenue; Revenue from operations; Fare revenue (subset); Passenger revenue (subset)
- **Labels (FR):** Revenus d'exploitation; Produits d'exploitation; Recettes tarifaires (sous-ensemble)
- **Where in a report:** Statement of operations / income statement in the audited financial statements; fare revenue alone appears in StatCan and farebox tables.
- **Common confusions:**
  - Operating revenue (earned) vs total revenue that includes government subsidy
  - Fares-only vs fares + ancillary income — operating revenue is the broader earned figure
- **Equations:** `average_fare_def`, `expense_revenue_subsidy`, `farebox_recovery_def`
- **Source tier:** statcan

### Operating Expenses (`operating_expenses`)

- **Is:** The total cost of operating the service over the period — labour, energy/fuel, materials and contracted services, and other operating costs. The denominator of farebox recovery and the cost-efficiency ratios.
- **Is NOT:** NOT total expenses including capital: typically EXCLUDES capital expenditure. Watch AMORTIZATION/DEPRECIATION — PSAB statements of operations INCLUDE it, while CUTA-style operating cost EXCLUDES it; record which basis the source used.
- **Unit:** CAD (currency)
- **Period:** Annual for most; quarterly for a few (TransLink, OC Transpo, Calgary).
- **Includes:** Labour, energy/fuel, materials and contracted services, other operating costs
- **Excludes:** Capital expenditure; Amortization/depreciation when an operating (CUTA) basis is used
- **Labels (EN):** Operating expenses; Operating costs; Total operating expenditure; Cost of service
- **Labels (FR):** Charges d'exploitation; Dépenses d'exploitation; Coûts d'exploitation
- **Where in a report:** Statement of operations / income statement; operating budget tables.
- **Common confusions:**
  - Operating vs total expenses that fold in capital
  - Amortization included (PSAB) vs excluded (CUTA operating basis) — changes farebox recovery
- **Equations:** `cost_per_hour_def`, `cost_per_rider_def`, `expense_components`, `expense_revenue_subsidy`, `farebox_recovery_def`
- **Source tier:** annual_report

### Total Operating Subsidy (`total_operating_subsidy`)

- **Is:** Total government operating funding that covers the shortfall between operating expenses and operating revenue (municipal + provincial + federal operating contributions).
- **Is NOT:** NOT total government funding: EXCLUDES capital grants. NOT a single level of government — it is the combined operating contribution. Equal to operating expenses minus operating revenue when both are on the same basis.
- **Unit:** CAD (currency)
- **Period:** Annual.
- **Includes:** Municipal, provincial, and federal OPERATING contributions
- **Excludes:** Capital grants and contributions
- **Labels (EN):** Operating subsidy; Net operating funding; Government operating contribution; Municipal/provincial operating funding
- **Labels (FR):** Subvention d'exploitation; Contribution gouvernementale d'exploitation; Financement public d'exploitation
- **Where in a report:** Statement of operations (as funding/contributions) or the funding-sources note; municipal budget transfer line.
- **Common confusions:**
  - Operating subsidy vs total funding that includes capital grants
  - One government's share vs the combined operating contribution
- **Equations:** `expense_revenue_subsidy`, `subsidy_per_rider_def`
- **Source tier:** annual_report

### Labour Cost (`labour_cost`)

- **Is:** Total employee compensation in operating cost — wages and salaries plus benefits (pension, health, payroll taxes). Usually the largest operating-cost line.
- **Is NOT:** NOT wages only when the source includes benefits, and NOT operator wages only — it is all-staff compensation unless scoped. NOT contracted-service labour (that sits in materials & services).
- **Unit:** CAD (currency)
- **Period:** Annual.
- **Includes:** Wages, salaries, overtime; Benefits: pension, health, payroll taxes
- **Excludes:** Contracted-out service labour (in materials & services)
- **Labels (EN):** Labour; Wages, salaries and benefits; Employee compensation; Salaries and benefits
- **Labels (FR):** Coûts de main-d'œuvre; Salaires et avantages sociaux; Rémunération
- **Where in a report:** Expenses-by-object note in the audited financial statements; budget detail.
- **Common confusions:**
  - Wages only vs wages + benefits
  - Operator labour vs all-staff labour
  - In-house labour vs contracted-service labour
- **Equations:** `expense_components`
- **Source tier:** annual_report

### Energy & Fuel Cost (`energy_fuel_cost`)

- **Is:** The cost of traction energy — diesel/CNG fuel and electricity for trolley, rail, and battery-electric vehicles.
- **Is NOT:** NOT facility/building energy unless the source bundles it (note if so). NOT a fuel volume — it is a dollar figure.
- **Unit:** CAD (currency)
- **Period:** Annual.
- **Includes:** Vehicle fuel (diesel, CNG); Traction electricity (rail, trolley, battery-electric)
- **Excludes:** Facility/building heating and power unless bundled by the source
- **Labels (EN):** Energy and fuel; Fuel and energy; Diesel and electricity; Traction power
- **Labels (FR):** Carburant et énergie; Énergie; Carburant
- **Where in a report:** Expenses-by-object note in the audited financial statements.
- **Common confusions:**
  - Vehicle traction energy vs facility energy
  - Dollar cost vs litres/kWh consumed
- **Equations:** `expense_components`
- **Source tier:** annual_report

### Materials & Services Cost (`materials_services_cost`)

- **Is:** Spending on materials/supplies (parts, tyres, lubricants) and purchased/contracted services (contracted operations, professional services, utilities other than traction).
- **Is NOT:** NOT capital purchases (those are capital expenditure). NOT labour or energy — it is the remaining materials-and-services object class.
- **Unit:** CAD (currency)
- **Period:** Annual.
- **Includes:** Parts, supplies, materials; Contracted/purchased services, professional fees
- **Excludes:** Capital asset purchases; Labour and traction energy
- **Labels (EN):** Materials and services; Supplies and services; Goods and services; Materials and supplies
- **Labels (FR):** Matériel et services; Fournitures et services; Biens et services
- **Where in a report:** Expenses-by-object note in the audited financial statements.
- **Common confusions:**
  - Operating materials/services vs capital purchases
  - Contracted-service labour appears here, not under labour cost
- **Equations:** `expense_components`
- **Source tier:** annual_report

### Farebox Recovery Ratio (`farebox_recovery_ratio`)

- **Is:** Operating revenue divided by operating expenses — the fraction of the cost of service paid for by what the service earns.
- **Is NOT:** NOT fares ÷ total cost-including-capital. The result depends on the expense basis (amortization included or not) and on whether the numerator is fares-only or all operating revenue — keep numerator and denominator on consistent bases.
- **Unit:** % (ratio)
- **Formula:** `operating_revenue / operating_expenses`
- **Period:** Matches its inputs' period; annual for most, quarterly for TransLink.
- **Labels (EN):** Farebox recovery ratio; Cost recovery (R/C); Revenue-to-cost ratio; Operating ratio
- **Labels (FR):** Taux de recouvrement (recettes/dépenses); Ratio d'autofinancement
- **Where in a report:** Calculated by TransitIndex; often printed in a KPI table (store the printed value as a cross-check).
- **Common confusions:**
  - Fares-only vs all-operating-revenue numerator
  - Operating expenses with vs without amortization changes the ratio materially
- **Equations:** `farebox_recovery_def`
- **Source tier:** derived

### Cost per Rider (`cost_per_rider`)

- **Is:** Operating expenses divided by ridership — the operating cost of carrying one boarding. Lower is generally better.
- **Is NOT:** NOT cost per distinct rider (it is per boarding), and NOT including capital cost unless the expense input does.
- **Unit:** CAD (currency)
- **Formula:** `operating_expenses / ridership`
- **Period:** Matches its inputs' period (same agency, same period).
- **Labels (EN):** Cost per boarding; Operating cost per trip; Cost per passenger trip
- **Labels (FR):** Coût par déplacement; Coût d'exploitation par déplacement
- **Where in a report:** Calculated by TransitIndex; sometimes printed in a KPI table.
- **Common confusions:**
  - Per boarding vs per distinct rider
  - Operating cost only vs cost including capital
- **Equations:** `cost_per_rider_def`
- **Source tier:** derived

### Cost per Revenue Hour (`cost_per_hour`)

- **Is:** Operating expenses divided by revenue service hours — the operating cost of supplying one hour of service. A standard cost-efficiency benchmark.
- **Is NOT:** NOT cost per total vehicle hour (the denominator excludes deadhead), and NOT a wage rate.
- **Unit:** CAD/hr (currency)
- **Formula:** `operating_expenses / revenue_service_hours`
- **Period:** Matches its inputs' period (same agency, same period).
- **Labels (EN):** Cost per revenue hour; Operating cost per service hour; Cost per hour
- **Labels (FR):** Coût par heure de service; Coût horaire d'exploitation
- **Where in a report:** Calculated by TransitIndex; sometimes printed in a KPI table.
- **Common confusions:**
  - Per revenue hour vs per total vehicle hour
  - Total operating cost per hour vs the operator wage rate
- **Equations:** `cost_per_hour_def`
- **Source tier:** derived

### Subsidy per Rider (`subsidy_per_rider`)

- **Is:** Total operating subsidy divided by ridership — the public funding required per boarding after fares and other operating revenue. Equivalent to (operating expenses − operating revenue) ÷ ridership.
- **Is NOT:** NOT total cost per rider (that ignores fare revenue), and NOT per distinct rider — it is net public subsidy per boarding.
- **Unit:** CAD (currency)
- **Formula:** `total_operating_subsidy / ridership`
- **Period:** Matches its inputs' period (same agency, same period).
- **Labels (EN):** Subsidy per boarding; Net cost per trip; Public subsidy per rider
- **Labels (FR):** Subvention par déplacement; Subvention publique par déplacement
- **Where in a report:** Calculated by TransitIndex from subsidy ÷ ridership.
- **Common confusions:**
  - Subsidy per rider (net of fares) vs cost per rider (gross)
  - Per boarding vs per distinct rider
- **Equations:** `subsidy_per_rider_def`
- **Source tier:** derived

### Fleet Size (`fleet_size`)

- **Is:** The count of active revenue vehicles the agency operates. A bus is one vehicle; for rail, count individual cars unless the agency reports trainsets (record which).
- **Is NOT:** NOT total vehicles including non-revenue (supervisor cars, work vehicles), and NOT stored/retired units. For rail, a metro CAR is not the same unit as a bus — do not mix cars, trainsets, and buses into one undifferentiated count without noting the basis.
- **Unit:** count (count)
- **Period:** Annual (point-in-time, usually fiscal year-end).
- **Includes:** Active revenue vehicles in service
- **Excludes:** Non-revenue vehicles (work/supervisor units); Stored, retired, or not-yet-commissioned vehicles
- **Labels (EN):** Fleet size; Revenue vehicles; Active fleet; Vehicles in service
- **Labels (FR):** Parc de véhicules; Taille du parc; Véhicules en service
- **Where in a report:** Fleet/asset profile section or the capital-assets note.
- **Common confusions:**
  - A metro CAR vs a bus — different units; note whether rail is counted by car or trainset
  - Revenue vehicles vs total including non-revenue
  - Active fleet vs total owned including stored/retired
- **Source tier:** annual_report

### Fleet Average Age (`fleet_average_age`)

- **Is:** The average age (in years) of the active revenue fleet — a state-of-good-repair signal.
- **Is NOT:** NOT the oldest vehicle's age and NOT remaining useful life. Lower is generally better.
- **Unit:** years (time)
- **Period:** Annual (point-in-time).
- **Includes:** Active revenue vehicles
- **Excludes:** Retired/stored vehicles
- **Labels (EN):** Average fleet age; Fleet average age; Average vehicle age
- **Labels (FR):** Âge moyen du parc; Âge moyen des véhicules
- **Where in a report:** Fleet/asset profile or state-of-good-repair section.
- **Common confusions:**
  - Average age vs oldest vehicle vs remaining useful life
  - Mixing modes with very different lifespans (bus ~12y vs rail ~30y)
- **Source tier:** annual_report

### Accessible Fleet % (`accessible_fleet_pct`)

- **Is:** The percentage of the active revenue fleet that is accessible (low-floor or ramp/lift-equipped).
- **Is NOT:** NOT the share of accessible STOPS/STATIONS (that is a different accessibility measure), and NOT a count — it is a percentage of vehicles.
- **Unit:** % (ratio)
- **Period:** Annual (point-in-time).
- **Includes:** Low-floor or ramp/lift-equipped revenue vehicles
- **Excludes:** Stop/station accessibility
- **Labels (EN):** Accessible fleet; Percent accessible vehicles; Low-floor fleet share
- **Labels (FR):** Véhicules accessibles; Part du parc accessible; Pourcentage de véhicules accessibles
- **Where in a report:** Accessibility section or fleet profile of the annual report.
- **Common confusions:**
  - Accessible vehicles vs accessible stops/stations
  - Low-floor only vs fully accessible (ramp/lift) definitions
- **Source tier:** annual_report

### Fleet scale (`fleet_capacity`)

- **Is:** A single fleet-scale figure that weights each mode's fleet_size by a fixed capacity weight (bus=1, streetcar=2, light_rail=3, subway=4, commuter_rail=5; BRT and trolleybus=1) and sums across modes. It corrects raw fleet_size, which would treat a high-capacity metro car and a bus as one unit each. Ferry, paratransit, and on-demand carry no weight and are excluded.
- **Is NOT:** NOT seated passenger capacity and NOT a passenger-count: it is a weighted COUNT of revenue vehicles, not seats or design capacity. NOT raw fleet_size (which is unweighted), and NOT a ridership figure.
- **Unit:** count (count)
- **Period:** Annual (point-in-time); derived from the same period's per-mode fleet_size.
- **Includes:** Per-mode fleet_size weighted by the mode's capacity weight (bus=1 … commuter_rail=5); BRT and trolleybus at weight 1
- **Excludes:** Ferry, paratransit, and on-demand (no capacity weight assigned); Non-revenue vehicles and stored/retired units (inherited from fleet_size)
- **Labels (EN):** Fleet scale; Weighted fleet; Capacity-weighted fleet
- **Labels (FR):** Parc pondéré; Échelle du parc
- **Where in a report:** Computed by TransitIndex from per-mode fleet_size and the mode capacity weights; no agency reports it directly.
- **Common confusions:**
  - Weighted fleet COUNT vs seated passenger capacity (seats) — these are different measures
  - Capacity-weighted fleet vs raw unweighted fleet_size
  - Modes with no weight (ferry, paratransit, on-demand) are excluded, not counted at zero use
- **Source tier:** annual_report

### Capital Expenditure (`capital_expenditure`)

- **Is:** Spending on long-lived assets in the period — new vehicles, facilities, track, and major infrastructure. Distinct from operating cost.
- **Is NOT:** NOT amortization/depreciation (the accounting spread of past capital), and NOT operating expense. NOT the capital budget/plan — it is actual capital spent.
- **Unit:** CAD (currency)
- **Period:** Annual.
- **Includes:** Vehicle purchases, facility and infrastructure construction, major rehabilitation
- **Excludes:** Amortization/depreciation; Operating expenses
- **Labels (EN):** Capital expenditure; Capital spending; Capital additions; Investment in capital assets
- **Labels (FR):** Dépenses en immobilisations; Investissements en immobilisations; Dépenses d'investissement
- **Where in a report:** Capital-assets note (additions) in the audited statements; capital budget/plan for planned (not actual) figures.
- **Common confusions:**
  - Capital expenditure (cash out for assets) vs amortization (non-cash spread)
  - Actual capital spent vs the capital budget/plan
- **Source tier:** annual_report

### Total Financial Assets (`total_financial_assets`)

- **Is:** The PSAB total of financial assets — cash, investments, and receivables — the resources that could be turned into cash to settle liabilities. The left side of the net-debt identity.
- **Is NOT:** NOT total assets (which also includes non-financial/tangible capital assets), and NOT cash alone. A point-in-time figure at fiscal year-end, not a flow.
- **Unit:** CAD (currency)
- **Period:** Annual (point-in-time, at fiscal year-end); TransLink also reports quarterly.
- **Includes:** Cash and cash equivalents, investments, accounts receivable
- **Excludes:** Tangible capital assets and other non-financial assets
- **Labels (EN):** Financial assets; Total financial assets
- **Labels (FR):** Actifs financiers; Total des actifs financiers
- **Where in a report:** Statement of financial position (top section) in the audited financial statements.
- **Common confusions:**
  - Financial assets vs total assets (financial + non-financial)
  - Point-in-time stock vs a flow figure from the statement of operations
- **Equations:** `net_debt_def`, `total_assets_identity`
- **Source tier:** annual_report

### Total Liabilities (`total_liabilities`)

- **Is:** The PSAB total of liabilities — debt, accounts payable, deferred revenue, and employee future benefits. The right side of the net-debt identity.
- **Is NOT:** NOT long-term debt alone (that is a subset), and NOT net debt (liabilities minus financial assets). A point-in-time figure at fiscal year-end.
- **Unit:** CAD (currency)
- **Period:** Annual (point-in-time); TransLink also quarterly.
- **Includes:** Debt, payables, deferred revenue, employee future benefits
- **Excludes:** Net debt (a derived figure, not a liability line)
- **Labels (EN):** Liabilities; Total liabilities
- **Labels (FR):** Passifs; Total des passifs
- **Where in a report:** Statement of financial position in the audited financial statements.
- **Common confusions:**
  - Total liabilities vs long-term debt (a subset)
  - Liabilities vs net debt
- **Equations:** `accumulated_surplus_identity`, `debt_to_assets_def`, `net_debt_def`
- **Source tier:** annual_report

### Total Non-Financial Assets (`total_non_financial_assets`)

- **Is:** The PSAB total of non-financial assets — chiefly tangible capital assets (net book value) plus inventories and prepaid expenses. Assets held for use in service delivery, not to be converted to cash.
- **Is NOT:** NOT financial assets, and NOT only tangible capital assets (it also includes inventories and prepaids). A point-in-time figure.
- **Unit:** CAD (currency)
- **Period:** Annual (point-in-time); TransLink also quarterly.
- **Includes:** Tangible capital assets (net), inventories, prepaid expenses
- **Excludes:** Cash, investments, receivables (those are financial assets)
- **Labels (EN):** Non-financial assets; Total non-financial assets
- **Labels (FR):** Actifs non financiers; Total des actifs non financiers
- **Where in a report:** Statement of financial position (non-financial assets section).
- **Common confusions:**
  - Non-financial assets vs tangible capital assets (TCA is the largest component)
- **Equations:** `total_assets_identity`
- **Source tier:** annual_report

### Total Assets (`total_assets`)

- **Is:** The headline total of all assets — financial assets plus non-financial assets. Equal by identity to total_financial_assets + total_non_financial_assets.
- **Is NOT:** NOT net of liabilities (that is accumulated surplus), and NOT financial assets alone. A point-in-time figure.
- **Unit:** CAD (currency)
- **Period:** Annual (point-in-time); TransLink also quarterly.
- **Includes:** Financial assets + non-financial assets
- **Excludes:** Any netting of liabilities
- **Labels (EN):** Total assets
- **Labels (FR):** Total de l'actif; Total des actifs
- **Where in a report:** Statement of financial position (sum line), or computed from its sections.
- **Common confusions:**
  - Total assets vs accumulated surplus (assets net of liabilities)
- **Equations:** `accumulated_surplus_identity`, `debt_to_assets_def`, `total_assets_identity`
- **Source tier:** annual_report

### Tangible Capital Assets (`tangible_capital_assets`)

- **Is:** The net book value (cost less accumulated amortization) of tangible capital assets — buses, trains, track, facilities, equipment. The largest component of non-financial assets.
- **Is NOT:** NOT gross/historical cost (it is net of accumulated amortization), and NOT capital expenditure (a flow). A point-in-time stock.
- **Unit:** CAD (currency)
- **Period:** Annual (point-in-time); TransLink also quarterly.
- **Includes:** Net book value of vehicles, facilities, track, equipment
- **Excludes:** Gross cost before amortization; Capital expenditure (the period's additions)
- **Labels (EN):** Tangible capital assets; Capital assets (net); TCA
- **Labels (FR):** Immobilisations corporelles; Valeur comptable nette des immobilisations
- **Where in a report:** Tangible capital assets note (net book value) in the audited statements.
- **Common confusions:**
  - Net book value vs gross/historical cost
  - TCA (a stock) vs capital expenditure (the year's additions)
- **Source tier:** annual_report

### Accumulated Surplus (`accumulated_surplus`)

- **Is:** The PSAB accumulated surplus — the agency's net economic position, equal by identity to total assets minus total liabilities (equivalently net financial assets plus non-financial assets). The bottom line of the statement of financial position.
- **Is NOT:** NOT the annual surplus/deficit (a single year's flow), and NOT cash. A cumulative point-in-time figure.
- **Unit:** CAD (currency)
- **Period:** Annual (point-in-time); TransLink also quarterly.
- **Includes:** Cumulative net position to date
- **Excludes:** The single-year surplus/deficit
- **Labels (EN):** Accumulated surplus; Net position
- **Labels (FR):** Excédent accumulé; Surplus accumulé
- **Where in a report:** Statement of financial position (bottom line) in the audited statements.
- **Common confusions:**
  - Accumulated surplus (cumulative) vs annual surplus/deficit (one year)
- **Equations:** `accumulated_surplus_identity`
- **Source tier:** annual_report

### Long-Term Debt (`long_term_debt`)

- **Is:** Borrowing with maturity beyond one year — debentures, bonds, and long-term loans. A subset of total liabilities.
- **Is NOT:** NOT total liabilities (it excludes payables, deferred revenue, employee benefits), and NOT net debt.
- **Unit:** CAD (currency)
- **Period:** Annual (point-in-time); TransLink also quarterly.
- **Includes:** Debentures, bonds, long-term loans
- **Excludes:** Short-term payables and other liabilities
- **Labels (EN):** Long-term debt; Debt
- **Labels (FR):** Dette à long terme; Emprunts à long terme
- **Where in a report:** Long-term debt note in the audited financial statements.
- **Common confusions:**
  - Long-term debt vs total liabilities (the broader figure)
- **Source tier:** annual_report

### Cash & Investments (`cash_and_investments`)

- **Is:** Cash, cash equivalents, and investments — the most liquid portion of financial assets. A liquidity signal.
- **Is NOT:** NOT total financial assets (which also includes receivables), and NOT total assets.
- **Unit:** CAD (currency)
- **Period:** Annual (point-in-time); TransLink also quarterly.
- **Includes:** Cash, cash equivalents, short- and long-term investments
- **Excludes:** Accounts receivable and other financial assets
- **Labels (EN):** Cash and investments; Cash and cash equivalents
- **Labels (FR):** Trésorerie et placements; Encaisse et placements
- **Where in a report:** Statement of financial position / cash and investments note.
- **Common confusions:**
  - Cash and investments vs total financial assets (the broader figure)
- **Source tier:** annual_report

### Net Debt (`net_debt`)

- **Is:** Total liabilities minus total financial assets — the PSAB net debt indicator. Positive net debt means liabilities exceed the financial assets available to settle them. We also store the agency's printed net debt as a cross-check.
- **Is NOT:** NOT long-term debt, and NOT total liabilities. It is a derived net figure; a NEGATIVE result is "net financial assets" (healthier).
- **Unit:** CAD (currency)
- **Formula:** `total_liabilities - total_financial_assets`
- **Period:** Matches its inputs' period (annual; quarterly for TransLink).
- **Labels (EN):** Net debt; Net financial assets (if negative)
- **Labels (FR):** Dette nette; Actifs financiers nets (si négatif)
- **Where in a report:** Computed; the printed net debt rides in the value's cross-check field.
- **Common confusions:**
  - Net debt vs total liabilities or long-term debt
  - A bigger agency has a bigger net debt — it is NOT ranked across agencies
- **Equations:** `net_debt_def`, `net_debt_per_capita_def`
- **Source tier:** derived

### Debt to Assets (`debt_to_assets`)

- **Is:** Total liabilities divided by total assets — a scale-free leverage ratio. One of the two balance-sheet metrics that IS ranked across agencies.
- **Is NOT:** NOT net debt per capita, and NOT a dollar figure. Lower generally indicates lower leverage.
- **Unit:** % (ratio)
- **Formula:** `total_liabilities / total_assets`
- **Period:** Matches its inputs' period (annual; quarterly for TransLink).
- **Labels (EN):** Debt-to-assets ratio; Liabilities-to-assets; Leverage ratio
- **Labels (FR):** Ratio dette/actif; Ratio d'endettement
- **Where in a report:** Computed by TransitIndex from total liabilities ÷ total assets.
- **Common confusions:**
  - Debt-to-assets (uses total liabilities) vs a long-term-debt-only leverage measure
- **Equations:** `debt_to_assets_def`
- **Source tier:** derived

### Net Debt per Capita (`net_debt_per_capita`)

- **Is:** Net debt divided by the agency's service-area population — the civic headline that makes net debt comparable across agencies of different sizes. One of the two ranked balance-sheet metrics. Population is the static service-area population, labelled "per resident served".
- **Is NOT:** NOT net debt itself (a raw dollar that is not ranked), and NOT per rider. The denominator is population served, not ridership.
- **Unit:** CAD (currency)
- **Formula:** `net_debt / service_area_population`
- **Period:** Matches the net-debt period; population is a static agency attribute.
- **Labels (EN):** Net debt per capita; Net debt per resident
- **Labels (FR):** Dette nette par habitant; Dette nette par résident
- **Where in a report:** Computed by TransitIndex from net debt ÷ service-area population.
- **Common confusions:**
  - Per capita (population served) vs per rider (ridership)
  - Uses net debt, not total liabilities or long-term debt
- **Equations:** `net_debt_per_capita_def`
- **Source tier:** derived

## Years & fiscal years

Most agencies report on the **calendar year** (January–December), so a period labelled
"2024" means January to December 2024. Two agencies differ: **Metrolinx / GO Transit** and
**BC Transit** end their financial year in **March**, so their "2024" means the 2024–25 fiscal
year (April 2024 to March 2025), shown as "FY2024-25". Period granularity (monthly / quarterly
/ annual) is a **dimension** of each value, not part of the metric name — one `ridership`
metric holds monthly, quarterly, and annual figures, and the annual figure is the sum of the
twelve months when all twelve are present.

## Data quality & how calculated values stay honest

Every value carries a quality label (**verified** — from an audited/official figure;
**preliminary** — published but not final; **estimated** / **imputed** — a source's own
estimate). A **calculated** value never claims more certainty than its inputs: it inherits the
weakest input's quality. Calculated values are produced by exact arithmetic on same-period
values only — never across years or agencies, never dividing by zero, never fabricated. Each
one records the equation and the exact input values it came from, so it is fully reconstructable.
When a value is both published and calculable, the two are cross-checked; a disagreement is
flagged for review rather than silently resolved.
