# TransitIndex — Data Sourcing & FOI Plan
**Created:** 2026-05-31 (via /autoplan, two research subagents) · companion to `source-registry.md`

Target fundamentals throughout: **operating expenses, total revenue, farebox recovery,
annual ridership / unlinked passenger trips, fleet size, revenue service hours.**

## Verdict: FOI is a narrow fallback, not a primary channel

For *these* fields, FOI is the worst-fit instrument available, for four reasons:

1. **"Already published → we redirect you" is fatal, by design.** Every Canadian access
   statute lets a body decline a request for records that are already public (Quebec s.13,
   Ontario FIPPA/MFIPPA s.15(a), Alberta FOIP, BC FIPPA). Operating expenses, revenue,
   ridership, fleet, service hours are exactly what agencies put in annual reports, budgets,
   and the CUTA Canadian Transit Statistics dataset. A coordinator will lawfully bounce
   these back with a link.
2. **Speed is incompatible with an annual cadence.** Nominal 20–30 days, soft everywhere
   except Quebec. BC meets its 30-day target ~half the time; Alberta/BC extensions run +30
   days or more. Across 100+ agencies yearly, a meaningful share lands in extension limbo.
3. **Fees scale badly, no ceiling.** Per-request floor is modest ($5 ON, $10 BC, $25 AB,
   $0 QC) but processing fees are uncapped. Multiply across 100+ agencies × yearly = a
   recurring four-to-five-figure line item, for data you could otherwise get free.
4. **Commercial scrutiny is real (esp. BC).** BC FIPPA s.75(6) carves out a "commercial
   applicant" (request "for use in connection with a trade, business… for profit"); a paid
   data product is squarely that → TransLink and BC Transit can charge actual copying cost
   on top, and public-interest fee waivers are realistically unavailable to a for-profit.

**Primary channel instead:** already-public sources (annual reports, municipal budgets, the
CUTA statistics program, and agency open-data portals), parsed/scraped, **plus a friendly
informal email** to each agency's open-data/finance team for the spreadsheet behind the
report. Reserve FOI for a *specific unpublished metric* at a *specific agency*, filed one-off
— preferably in Quebec/Ontario where it's cheapest.

## Per-agency plan

| Agency | File FOI with… | FOI statute / app fee | Already-public source | Structured-data likelihood | Recommended route |
|---|---|---|---|---|---|
| **TTC** | TTC's own FOI office ($5) | Ontario MFIPPA | 2024 Operating Statistics (HTML tables); ridership Excel on Toronto open data | **Med** | Read the stats page; one email for the Excel |
| **STM** | Acces.Information@stm.info (free) | Quebec ATI / $0 | 2024 annual/activity report + budget | **Med** | Informal email (FR/EN) |
| **TransLink** | TransLink Info Access ($10) | BC FIPPA (commercial penalty) | 2024 Year-End Financial & Performance Report | **Med** | Read reports; optional email for sheet |
| **Metrolinx/GO** | FOI@metrolinx.com ($5) | Ontario FIPPA | Annual reports + open-data (GTFS) | **Low** (signalled it may *sell* ridership) | GTFS from portal; **FIPPA** for ridership/financial detail |
| **OC Transpo** | City of Ottawa ATIP ($5) | Ontario MFIPPA | Performance scorecards + City budget | **Med** | Email City open-data; MFIPPA fallback |
| **Calgary Transit** | City of Calgary Access ($25) | Alberta FOIP/ATIA | Open Calgary ridership; budget PDFs | **High** | Read open-data; short email for hours/fleet |
| **Edmonton ETS** | City of Edmonton Access ($25) | Alberta ATIA | Socrata portal: ridership **and** budget expenses as CSV/API | **High** | Just read the portal; no request needed |
| **MiWay** | City of Mississauga Clerk ($5) | Ontario MFIPPA | Open data + business plan/budget | **Med→High** | Email City open-data; MFIPPA fallback |
| **BC Transit** | FOI_Request@bctransit.com ($10) | BC FIPPA (commercial penalty) | 2024/25 Annual Service Plan Report; GTFS | **Med** | Read ASP report; email for Victoria-only split |
| **Burlington** | City of Burlington Clerk ($5) | Ontario MFIPPA | City budget book; GTFS only on portal | **Low→Med** | Informal email (small, likely responsive) |

**Filing pattern:** TTC, Metrolinx, TransLink, BC Transit, STM run their **own** access offices.
OC Transpo, Calgary, Edmonton, MiWay, Burlington are **city departments** — file with the
municipal Clerk / Access office, not a transit-branded address.

**Cheapest/fastest:** Quebec/STM (no fee, hard 20+10-day cap). **Worst:** BC (fee + commercial
penalty + weakest on-time), then Alberta (highest $25 upfront, mid-migration to ATIA).

## Start here (to seed REAL ground truth and kill the synthetic gold fixture)

1. **TTC — primary.** The fixture is already TTC 2024 and TTC publishes nearly all of it on
   its 2024 Operating Statistics pages. Hand-verify the fixture from that page today; email
   TTC only for the Excel. (Subagent surfaced candidate 2024 figures — ridership ~419.9M,
   fare revenue ~$1,019.3M, operating expenses ~$2.37B, fleet 2,038 bus / 233 streetcar /
   848 subway — **but these came from search summaries, not a fetched page; verify each
   against the live TTC page before locking them into `ttc_annual_2024.json`.**)
2. **Edmonton ETS — fastest structured second source.** Socrata returns ridership + budget
   expenses as CSV/API right now → a same-week, no-request second data point to validate the
   fixture *schema* against a second real agency.

Skip Metrolinx for ground-truth seeding — its ridership data is least likely to come back fast or free.

## Request templates

### (a) Informal data-request email
> **Subject:** Quick data request — [AGENCY] annual operating & ridership figures (spreadsheet)
>
> Hi [Open Data / Finance / Planning] team,
>
> I'm building a public, plain-language directory of Canadian transit-agency fundamentals so
> residents and councils can compare systems like-for-like. I'd love to include [AGENCY] using
> your own published numbers. If there's a **spreadsheet (Excel/CSV) behind the figures**, that
> saves me re-keying from PDFs. For **fiscal years [2022, 2023, 2024]** I'm after: total
> operating expenses; total revenue (fare + total separately if possible); annual ridership /
> unlinked passenger trips; revenue service hours; fleet size; farebox/cost-recovery ratio if
> you report one. I'll publish with **clear attribution to [AGENCY]** and a link back — so I
> get it right, **are there any licence or redistribution terms** I should follow? Whatever
> format is easiest on your side works. Thank you for making this public.
>
> Best, [Name] · [email] · [project URL]

### (b) Formal FOI/ATIP request (fallback)
> To the Access/Privacy Coordinator — I request access under [MFIPPA / Ontario FIPPA / BC FIPPA
> / Alberta ATIA / Quebec ATI] to the following records held by [AGENCY] for **FY [2022–2024]**:
> (1) total operating expenses; (2) total revenue split fare vs total; (3) annual ridership /
> unlinked passenger trips, by mode if available; (4) revenue service hours; (5) year-end fleet
> size; (6) farebox/cost-recovery ratio as reported internally. **Format:** electronic,
> machine-readable (Excel/CSV) where such files exist, not scanned PDFs. **Fees:** this confirms
> the $[5/10/25] application fee; please send a **written estimate before** any further charges
> and do not exceed $25 without my approval; advise if a public-interest waiver applies.
> [Name, date, contact]

[UNVERIFIED] flags from research: exact BC Schedule-1 commercial copying cents; current Alberta
per-15-min processing rate; post-ATIA (June 2025) Edmonton fee mechanics. All dollar 2024 TTC
figures need one-click human verification (WebFetch was disabled during research).
