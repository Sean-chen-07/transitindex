# Candidate gold review — 2026-08-25

Offline review of the three auto-derived candidate fixtures in `candidates/`.
No PDF was re-read and no API was called: the only evidence used is each row's
recorded `evidence` block (page / confidence / quote / note) plus cross-checks
against the frozen smoke recording
(`tests/fixtures/smoke/smoke10_2026-06-12.json`) and internal accounting
identities. **No value was invented or edited** — a promoted row is the
candidate row verbatim.

Every candidate row was confirmed to appear in the frozen smoke fixture with the
same metric, value and quote (16 / 13 / 12 rows, all matched).

## Rules applied

A row was **promoted** only when all four held:

1. **Digits**: the value's printed digits appear in the quote, after applying the
   scale the quote itself states (`525.5` under a "(Millions)" header supports
   525,500,000; `106,485` under "(000s)" supports 106,485,000).
2. **Column**: the quote's layout unambiguously identifies the reporting year's
   figure. A single number, or a two-number current/prior comparative (universal
   statement convention, current year first), passes. An **unlabelled
   three-number row** (budget / actual / prior) does not — nothing in the
   recorded quote says which column was taken.
3. **Scope**: the figure is the agency's, not a consolidated city-wide figure.
4. **Mapping**: the quote's wording plausibly *is* the metric, not a component or
   a near neighbour of it.

Cross-check used for TTC: the four balance-sheet rows close the PSAB identity
exactly — 1,292,103 (financial assets) − 1,543,369 (liabilities) + 12,311,927
(non-financial assets) = 12,060,661 (accumulated surplus). That mutually
confirms all four first-column readings.

## Result

| fixture | promoted | held |
|---|---|---|
| `ttc_annual_2019_doc59.json` | 11 | 5 |
| `calgary-transit_annual_2019_doc13.json` | 1 | 12 |
| `edmonton-ets_annual_2019_doc19.json` | 0 | 12 |

Promoted rows now live in `gold/ttc_annual_2019.json` and
`gold/calgary-transit_annual_2019.json`. **The candidate files were left
untouched** — a held row is still there, with its evidence, for a later human
pass. No `edmonton-ets` gold file was created.

`should_flag` is `false` on every promoted row: none of these figures is
ambiguous in its source, so the two new fixtures guard **precision** only. Flag
recall still has no real-document coverage.

---

## TTC 2019 (doc 59) — annual report, the agency's own statements

### Promoted (11)

| metric | value | why |
|---|---|---|
| `accumulated_surplus` | 12,060,661,000 | Quote `Accumulated surplus \| 12,060,661 \| 11,568,749` — current/prior pair, first column. Closes the balance-sheet identity. The recorded conflict (12,059,032,000) is a competing chunk reading the quote does not support. |
| `total_financial_assets` | 1,292,103,000 | Quote `Total financial assets \| 1,292,103 \| 1,323,084`, conf 0.95. Identity closes. |
| `total_liabilities` | 1,543,369,000 | Quote `Total liabilities \| 1,543,369 \| 1,589,410`. Identity closes; the conflicting 597,000,000 chunk reading is unsupported by the quote. |
| `total_non_financial_assets` | 12,311,927,000 | Quote `Total non-financial assets \| 12,311,927 \| 11,835,075`, conf 0.95. Identity closes. |
| `tangible_capital_assets` | 12,130,417,000 | Quote `Tangible capital assets (note 11) \| 12,130,417 \| 11,647,678`, conf 0.95; ≤ total non-financial assets, as it must be. |
| `cash_and_investments` | 141,716,000 | Quote `Cash and cash equivalents (note 4) \| 141,716`, conf 0.9. *Caveat below.* |
| `capital_expenditure` | 1,354,966,000 | Quote `Tangible capital asset acquisitions (1,354,966) (1,455,261)` — cash-flow current/prior pair, current first. |
| `labour_cost` | 1,459,106,000 | Quote `Wages, salaries and benefits 1,459,106 1,397,379`, conf 0.9. Current/prior pair. |
| `materials_services_cost` | 329,664,000 | Quote `Materials, services and supplies 329,664 292,110`, conf 0.85. Current/prior pair. |
| `ridership` | 525,500,000 | Quote `Revenue Passenger Trips (Millions) 525.5` — scale stated in the quote; matches TTC's published 2019 ridership. The conflicting 530,000,000 chunk reading is unsupported by the quote. |
| `fleet_size` | 3,436 | Quote `Total Vehicle Fleet 3,436`, conf 0.85, single number. |

**Caveat on `cash_and_investments`**: the quote covers *cash and cash
equivalents* only. For the Calgary and Edmonton documents the extractor
explicitly noted a separate investments line; for TTC it did not, so on the
recorded evidence there is nothing to add. If TTC's 2019 balance sheet does
carry a separate investments line, this row understates the metric and should be
corrected.

### Held (5)

| metric | value | why held |
|---|---|---|
| `operating_expenses` | 2,921,698,000 | Quote `Total expenses (note 15) 2,717,370 2,921,698 2,502,656` — three unlabelled columns; the middle one was taken. Also inconsistent with the other promoted rows: operating revenue 1,264,087 + subsidies 804,880 = 2,068,967, far from 2,921,698, so the scope of this "total expenses" is unclear. **Ambiguous — needs a human.** |
| `total_revenue_excluding_subsidy` | 1,264,087,000 | Quote `Total operating revenue 1,270,862 1,264,087 1,234,789` — three unlabelled columns. **Ambiguous — needs a human.** |
| `subsidy` | 804,880,000 | Quote `Operating subsidies (note 13) 825,329 804,880 710,767` — three unlabelled columns. **Ambiguous — needs a human.** |
| `energy_fuel_cost` | 84,063,000 | Quote `Vehicle fuel 84,063 79,502`, but the note records electric traction power of 58,761 reported separately. Whether the metric means vehicle fuel alone or all traction energy is a metric-definition question, not an extraction one. **Ambiguous — needs a human.** |
| `vehicle_revenue_km` | 254,000,000 | Quote `Total Kilometres Operated 254.0` states no scale (the millions multiplier came from the unit field, not the quote), and "kilometres operated" is not necessarily *revenue* km (deadheading). Two independent doubts. |

## Calgary Transit 2019 (doc 13) — City of Calgary consolidated annual report

### Promoted (1)

| metric | value | why |
|---|---|---|
| `ridership` | 106,485,000 | Quote `Transit passenger trips, annual (000s) 106,485` — transit-specific, scale stated in the quote, conf 0.9, no conflict. |

### Held (12)

Ten of the twelve are **city-wide consolidated** figures from the City of Calgary's
statements, not Calgary Transit figures, so they would be wrong as gold for the
`calgary-transit` agency. The extractor's own notes say so on several rows
("City-wide consolidated …; not transit-specific", "Consolidated City of
Calgary"). Held: `accumulated_surplus` (21,025,406,000), `capital_expenditure`
(1,160,353,000), `cash_and_investments` (263,209,000), `labour_cost`
(1,980,167,000), `long_term_debt` (2,883,447,000), `materials_services_cost`
(368,262,000), `tangible_capital_assets` (18,481,951,000),
`total_financial_assets` (7,579,593,000), `total_liabilities` (5,122,000,000),
`total_non_financial_assets` (18,568,000,000).

Two are transit-specific but ambiguous rather than city-wide:

| metric | value | why held |
|---|---|---|
| `operating_expenses` | 607,382,000 | Quote `Public transit 470,760 607,382 567,655` — three unlabelled columns (the note claims the middle is 2019 Actual, but the quote does not say so). **Ambiguous — needs a human.** |
| `total_revenue_excluding_subsidy` | 181,450,000 | Quote `Public transit 181,450 – 181,450` from a "Revenue by Source" schedule: this is *sales of goods and services* for transit, which may or may not be the agency's whole non-subsidy revenue. **Ambiguous — needs a human.** |

Note the city-wide rows are internally consistent (7,579,593 − 5,122,483 +
18,568,296 = 21,025,406), which is a good sign about the *extraction* and says
nothing good about the *scope*.

## Edmonton ETS 2019 (doc 19) — City of Edmonton consolidated annual report

### Promoted (0) — all 12 held

Same problem as Calgary, more completely: every row is a City of Edmonton
consolidated figure (`Operating Expenses $ 3,189.7`, `Salaries, wages and
benefits $ 1,636.5`, `Financial Assets $ 7,284.0`, …), and several quotes are
five-number budget/actual/variance/prior/variance rows with no column labels
(e.g. `Operating Revenues $ 3,210.0 $ 3,120.0 $ (90.0) $ 3,050.3 $ 69.7`).
Nothing here is an ETS figure, so nothing was promoted and no
`edmonton-ets_annual_2019.json` was created.

Held: `accumulated_surplus`, `capital_expenditure`, `cash_and_investments`,
`labour_cost`, `long_term_debt`, `materials_services_cost`,
`operating_expenses`, `total_revenue_excluding_subsidy`,
`tangible_capital_assets`, `total_financial_assets`, `total_liabilities`,
`total_non_financial_assets`.

## Caveat: partly circular against the frozen recording

These rows were promoted from the frozen smoke recording, so scoring *that*
recording against them will read precision 1.00 by construction (it does). They
are a fixed target for future runs and for offline changes that alter which
reading survives a merge — not evidence that today's extractor is accurate.
Genuinely independent gold needs a human keying figures straight from a PDF.

## What this says about the extractor (free finding)

Two of the three candidate documents are city annual reports, and on both the
extractor happily returned **city-wide consolidated financials labelled as the
transit agency's**. That is not a rounding problem; it is a scope problem, and
it is the single largest source of wrong values in this sample (22 of 41
candidate rows). Any accuracy work should treat "did we take an agency figure or
a city figure?" as a first-class check.
