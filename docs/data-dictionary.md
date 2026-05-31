# TransitIndex — Data Dictionary

**What this is:** a plain-language guide to exactly what the data table holds, written for non-technical readers (city staff, council, anyone reviewing the numbers). For the database design behind it, see `data-model.md`; for where each number comes from, see `source-registry.md`; for how often each number changes, see `update-frequency.md`.

## Overview

The data is one big table with **one row per agency per year** (for example, "TTC, 2024" is one row; "TTC, 2023" is another). Each row has **20 columns of numbers**. You only ever fill in **14** of them by hand from published sources (annual reports, open-data downloads, Statistics Canada). The other **6 are calculated automatically** by the system from columns you already filled in — they are ratios like "cost per rider" that the spreadsheet works out for you so the math is always consistent.

Every value also carries some hidden bookkeeping (where it came from, how trustworthy it is, what period it covers). Those are explained in the last two sections.

## The 20 columns

The 14 **Sourced** columns are numbers you copy from a published document or dataset. The 6 **Calculated** columns are filled in for you. "Where it comes from" and "Typical update frequency" describe the most common case across the 10 launch agencies; the exact source per agency lives in `source-registry.md` and `update-frequency.md`.

| Column name | Plain meaning | Unit | Sourced / Calculated | Formula (if calculated) | Where it comes from | Typical update frequency |
|---|---|---|---|---|---|---|
| Annual Ridership | Total trips taken on the system in the year (boardings) | count | Sourced | — | Statistics Canada monthly table (7 of 10 agencies), agency open data, or annual report | Monthly for most big agencies (~2-month lag); annual for OC Transpo, MiWay, Burlington |
| Revenue Service Hours | Hours the vehicles spent in service carrying passengers | hours | Sourced | — | Agency annual report; some agencies' open data (Edmonton, Calgary) | Mostly annual; monthly for a few |
| Vehicle Revenue Kilometres | Distance vehicles travelled while in passenger service | km | Sourced | — | Agency annual report | Annual |
| On-Time Performance | Share of scheduled service that ran on time | % | Sourced | — | Agency reports (monthly board decks for TTC/STM; quarterly for TransLink/Metrolinx) | Monthly to quarterly for big agencies; annual otherwise |
| Operating Revenue | Money the service earned (mostly fares, plus other operating income) | CAD | Sourced | — | Statistics Canada (farebox only) or annual report (full figure) | Monthly for big agencies; quarterly/annual otherwise |
| Operating Expenses | Total cost to run the service for the year | CAD | Sourced | — | Agency annual report (or city annual report / budget) | Annual (quarterly for TransLink, OC Transpo, Calgary) |
| Total Operating Subsidy | Government funding that covers the gap between cost and revenue | CAD | Sourced | — | Agency annual report / government budget | Annual |
| Labour Cost | Employee wages and benefits (usually the biggest cost line) | CAD | Sourced | — | Agency annual report | Annual |
| Energy & Fuel Cost | Spending on fuel and electricity to move the vehicles | CAD | Sourced | — | Agency annual report | Annual |
| Materials & Services Cost | Maintenance materials plus contracted-out services | CAD | Sourced | — | Agency annual report | Annual |
| Fleet Size | Number of active revenue vehicles in the fleet | count | Sourced | — | Agency annual report | Annual |
| Fleet Average Age | Average age of the active vehicles | years | Sourced | — | Agency annual report | Annual |
| Accessible Fleet % | Share of the active fleet that is accessible | % | Sourced | — | Agency annual report | Annual |
| Capital Expenditure | Spending on new vehicles and infrastructure | CAD | Sourced | — | Agency annual report / capital budget | Annual |
| Average Fare | Revenue earned per rider | CAD | Calculated | Operating Revenue ÷ Annual Ridership | Computed from the two columns above | Matches its inputs (usually annual) |
| Trips per Revenue Hour | Riders carried for each hour of service | trips/hr | Calculated | Annual Ridership ÷ Revenue Service Hours | Computed from the two columns above | Matches its inputs |
| Farebox Recovery Ratio | Share of operating cost paid for by fares/revenue | % | Calculated | Operating Revenue ÷ Operating Expenses | Computed from the two columns above | Annual (quarterly for TransLink) |
| Cost per Rider | Operating cost for each trip taken | CAD | Calculated | Operating Expenses ÷ Annual Ridership | Computed from the two columns above | Annual |
| Cost per Revenue Hour | Operating cost for each hour of service | CAD | Calculated | Operating Expenses ÷ Revenue Service Hours | Computed from the two columns above | Annual |
| Subsidy per Rider | Public subsidy needed for each trip taken | CAD | Calculated | (Operating Expenses − Operating Revenue) ÷ Annual Ridership | Computed from the columns above | Annual |

## The 6 calculated columns

These six are never typed in by hand — the system works them out. If a published source happens to print the ratio directly, we may store that printed figure too as a cross-check, but the column shown is the one calculated from the underlying numbers, so it always stays consistent with them.

- **Average Fare (revenue per rider) = Operating Revenue ÷ Annual Ridership.** How much fare income the system earns for each trip.
- **Trips per Revenue Hour = Annual Ridership ÷ Revenue Service Hours.** How many riders each hour of service carries — a productivity measure.
- **Farebox Recovery Ratio = Operating Revenue ÷ Operating Expenses.** What fraction of the running cost is covered by what the service earns.
- **Cost per Rider = Operating Expenses ÷ Annual Ridership.** What it costs to run the service per trip.
- **Cost per Revenue Hour = Operating Expenses ÷ Revenue Service Hours.** What it costs to run one hour of service.
- **Subsidy per Rider = (Operating Expenses − Operating Revenue) ÷ Annual Ridership.** How much public money tops up each trip after fares.

**The rule for when a calculated column gets filled in:** a calculated value is only produced when **both** of its input numbers exist for the **same agency** and the **same year**. The system never mixes years or agencies (it will not, for example, divide one year's expenses by another year's ridership). And it **never divides by zero** — if the bottom number is missing or zero, the calculated column is simply left blank rather than showing a wrong or infinite value. So if an agency has no ridership figure for a year, every ratio that divides by ridership stays empty for that year.

## Years & fiscal years

Most agencies report on the **calendar year** (January–December), so a row labelled "2024" means January to December 2024.

Two agencies are different: **Metrolinx / GO Transit** and **BC Transit** end their financial year in **March**. For them, a year label means the fiscal year that *begins* in that calendar year — so "2023" means their **2023–24 fiscal year** (April 2023 to March 2024), and it is shown as "FY2023-24". The "Year" column always refers to the calendar year the reporting year begins, so these two agencies line up with everyone else by start date even though their years run on a different cycle.

## Data quality

Every value carries a quality label so readers know how solid it is:

- **Verified** — taken from an audited or official published figure.
- **Preliminary** — published but not yet final (may be revised).
- **Estimated** — our best estimate where a clean figure was not published.

Values also carry a "comparable across agencies" flag. Agencies count and report things slightly differently, and some serve very different populations and mix of services, so two numbers that look alike are not always strictly comparable. Where we are confident a value is safe to compare side by side, it is flagged as comparable; where there is a known caveat, that flag is off and the difference should be read with care. When a number is later corrected, the table keeps the history but shows the latest figure as the current one.
