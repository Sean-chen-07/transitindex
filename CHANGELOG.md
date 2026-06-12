# Changelog

All notable changes to TransitIndex.

## [0.0.6.0] - 2026-06-11

A reliability-and-trust release from a full-workbase audit: fixes that prevent wrong
numbers and data loss, plus accessibility, a clearer payment experience, and the first
automated tests that run on every change.

### Fixed

#### Numbers you can trust
- **A figure printed in a "$000s" table can no longer be quietly shrunk 1000×.** The PDF
  reader's double-check pass was re-reading a corrected number without re-applying the
  table's stated units; it now keeps the scale, so 2,240 in a thousands table stays
  2,240,000 — not 2,240.
- **"Start a source over" no longer deletes data it shouldn't.** The `--reset` option used
  to wipe everything for a source's agencies — including numbers typed by hand or approved
  from a PDF. It now removes only that source's own numbers, prints exactly what it will
  delete agency by agency, and requires a confirmation (`--yes`) first.
- **Re-importing the data workbook no longer overwrites better data.** Exporting and then
  re-importing the spreadsheet used to republish every cell as a hand-entry, clobbering
  fresher official figures. Import now skips unchanged cells and warns before a typed value
  would replace an official one.

#### Payments
- **A clear confirmation after subscribing.** Returning from checkout now shows "You're a
  member" (or, while the payment is still processing, "activating — refresh in a few
  seconds") instead of silently re-showing the Subscribe button.
- **The "members who paid" counter can't be faked.** The events that signal a payment are
  now recorded only on the server, never accepted from the browser.

#### Accessibility & resilience
- **Keyboard focus is visible again on every button** (effectively required for civic/
  government use).
- **Friendly error, "page not found", and loading screens** instead of a raw crash page
  when something hiccups.
- Added standard browser security headers.

### Behind the scenes
- **Automated tests now run on every change** — the website, the data pipeline, and a
  from-scratch database rebuild — so regressions are caught automatically.
- Repaired two database migrations that broke a from-scratch rebuild, and added a
  one-click backup of the data that can't be re-fetched.
- A bulk data load no longer gets re-published a second time by a later workbook import.

## [0.0.5.0] - 2026-06-10

### Added

#### A redesigned agency page: two tabs, charts, full statements
- **Every agency now opens to a two-tab page.** *Highlights* shows six headline numbers
  (ridership, operating revenue, on-time performance, cost per rider, subsidy per rider,
  fleet scale), each with its rank, a neutral up/down arrow versus the prior year, and a
  click-to-open history chart — over compact tables of the efficiency ratios and the
  service/fleet figures. *Financials* lays the numbers out like the agency's audited
  statements (Statement of Operations, then Statement of Financial Position) with every
  year as its own column.
- **Charts for the numbers people track over time** (Recharts): a smooth monthly line for
  ridership and revenue (with a Yearly/Monthly toggle), bars for sparse yearly figures.
  A missing year shows as a gap, never an invented zero.

#### Download an agency's data
- **Members can download a single agency's full financial grid as a CSV** from the
  Financials tab — every line, every year, opens straight in Excel. One agency at a time,
  from its own page.

### Changed

#### Viewing every number is now free
- **The paywall is gone from viewing.** Every number, chart, and statement is visible to
  everyone with no login — previously raw numbers were members-only. A membership now buys
  one thing: downloading an agency's dataset. (Pricing is still being decided.)

### Fixed
- **Fiscal-year figures land in the right year.** Corrected an off-by-one in PDF
  extraction and the data-entry workbook so a fiscal year ending in March 2024 is recorded
  as 2024, not 2023.

#### Behind the scenes — more trustworthy extraction
- The PDF reader now finds financial statements in French as well as English reports,
  records the printed label and table each figure came from, and runs accounting cross-checks
  (assets, liabilities, expense components) as figures are staged — so a wrong number is
  flagged for review before it could ever be published.

## [0.0.4.0] - 2026-06-08

### Added

#### Source PDFs now live in the cloud, with a scan queue
- **The 64 annual-report PDFs moved off the laptop into Supabase Storage** (private bucket
  `annual-reports`, one file per agency/year). The raw files are backed up in the cloud and
  the local copies are no longer needed.
- **A documents catalog tracks every PDF** — agency, year, document type, transit-authored
  `[T]` vs city `[C]`, where it is stored, and whether it has been scanned yet
  (`unscanned` → `scanned` / `failed`). The unscanned list is your work queue. (new
  `core.documents` table, migration 016)
- **A Scan button** on the review console (`python -m transitindex_ingest review`, then open
  the page) fetches a PDF from the cloud, runs the existing extractor, and stages the numbers
  into the review queue. Scanning feeds the existing human-review step — it never publishes a
  number directly.
- **New commands to manage the collection:** `docs-sync` (upload a folder and build the
  catalog), `docs-upload` (add one PDF going forward), `docs-list` (see the queue),
  `docs-scan` (scan from the command line), and `docs-verify` (confirm cloud copies match the
  originals before deleting local files).

### Changed
- Scanning fetches each PDF from cloud storage into a temporary file and deletes it afterward —
  no PDF is kept permanently on local disk.

## [0.0.3.0] - 2026-06-06

### Added

#### Metrics are now a linked equation graph
- **The system back-solves missing numbers from the ones you have.** Metrics are linked by
  equations (farebox recovery = revenue ÷ expenses, total subsidy = expenses − revenue,
  expenses = labour + energy + materials, and the balance-sheet identities). Give it any two
  and it computes the third — e.g. farebox + revenue fills in expenses. It propagates to a
  fixpoint, so one solved value unlocks the next.
- **Every back-solved number stays dispute-proof.** Each derived value is exact arithmetic on
  same-period figures only — never estimated, never mixed across years — and records the exact
  equation and the exact source rows it came from (`metric_value_derivations`), so any number
  can be traced back to cited inputs. A derived value never claims more certainty than its
  weakest input.
- **When a number is both published and computable, the two are cross-checked.** Agreement is
  silent; a disagreement beyond 2% is flagged for review (`sum_mismatch` /
  `cross_source_disagreement`) instead of silently picking one. The solver also guards against
  "verifying" a value against the equation that produced it.

#### One ridership metric; period is a dimension
- **`monthly_ridership` and `annual_ridership` merged into one `ridership` metric.** Monthly vs
  annual is now the reporting period's granularity, not a separate metric code. Annual ridership
  is the sum of the twelve months when all twelve are present; an incomplete year is shown as a
  partial year-to-date figure that never ranks against full years. Fiscal-year agencies
  (Metrolinx, BC Transit) roll up April–March correctly.

#### Financial-position (balance-sheet) metrics
- **11 new balance-sheet metrics** (total assets, liabilities, net debt, accumulated surplus,
  tangible capital assets, and more), following Canadian public-sector accounting (PSAB). The
  raw dollar figures measure size, not performance, so they are never ranked; only the two
  scale-free ratios (debt-to-assets, net-debt-per-capita) rank across agencies.

#### A precise per-metric data dictionary
- **One spec per metric** — what it is, what it is NOT, the English and French labels it appears
  under in annual reports, where in a report it lives, and the common confusions to avoid
  (unlinked vs linked trips, operating vs total revenue, a metro car vs a bus in "fleet"). This
  single source now drives the human documentation, the PDF-extraction prompts, and FOI request
  templates, so extraction and records requests ask for exactly the right figure.

#### More accurate PDF extraction
- **The model reports a number as printed and declares its scale and sign; the code applies
  them.** "(in thousands)" and accounting parentheses like `(1,234)` are handled deterministically
  in code rather than trusted to the model's arithmetic, and every scaling decision is auditable.

### Changed
- The metric catalog grew from 21 to 31 (the ridership merge −1, plus 11 balance-sheet metrics).
  Migrations `012`–`014` apply the merge, the equation/derivation tables, and the balance-sheet
  family; seeds and the Python reference data are kept in parity (`db/tests/00_seed_assertions`
  now expects 31 metrics, 9 derived, 13 equations).

## [0.0.2.0] - 2026-06-06

### Added

#### Accounts & billing
- **Sign in and subscribe.** You can now create an account (Auth.js / NextAuth) and pay for
  access through Stripe. Migration `008` adds the auth tables; the Stripe webhook is the only
  writer of `subscription_status`, and `web/src/server/entitlement.ts` reads it live on every
  request — so a cancelled subscription loses access on the very next page load, never a stale
  token. Setup steps live in `web/SETUP-AUTH-BILLING.md`.
- **The paywall is now real end-to-end** — raw agency numbers gate behind an active paid
  account, enforced server-side; the free rank directory stays login-free and crawlable. This
  wires the account check into the choke point that shipped structurally in 0.0.1.0.
- **Shared reporting periods** (migration `009`) so a rank compares the same period across
  every agency — never a 2024 figure against a 2023 one.

#### Data population
- **One-click bulk loaders for StatCan and Hamilton.** Double-click `load-statcan.bat` or
  `load-hamilton.bat` (or run `python -m transitindex_ingest statcan-load <csv>` /
  `hamilton-load <csv>`) to load a whole agency's monthly history at once. The load is
  diff-aware and idempotent — re-running supersedes only the months that changed; add
  `--reset` to force a full reload. Roughly 84 round-trips instead of ~12,000.
- **Hamilton HSR adapter** (`adapters/hamilton_hsr.py`) reads Hamilton's ArcGIS JSON API —
  144 months (Jan 2014–Apr 2025) staged for review.
- **+11 agencies.** The StatCan map and seeds now cover Winnipeg, Hamilton, Brampton, Grand
  River, STL Laval, RTL Longueuil, York Region, Halifax, Durham Region, Saskatoon, and Regina
  (migration `010`). The Excel workbook tracks all 21 agencies (105 rows × 5 years).
- **OGL Hamilton licence** added to the source-licence allow-list (`contract.py` + migration
  `011`), so Hamilton's open data renders with its required attribution.

### Changed
- Seed assertions track the growing census: `db/tests/00_seed_assertions` now expects ≥10
  agencies (a growing set, not a fixed 10), 21 metrics, and 9 source feeds.
- The review API's mutating endpoints (approve/reject/edit) now require an
  `Authorization: Bearer <token>` header matching `REVIEW_API_TOKEN`; read endpoints stay
  open and the `review` CLI fails closed without a token.

### Fixed
- The Excel workbook no longer offers `monthly_ridership` as a hand-entry column — monthly
  ridership is fed by the StatCan loader, so the annual grid (one row per agency-year) stays
  annual-only and can never import a monthly figure under an annual period.

## [0.0.1.0] - 2026-05-31

### Added
- **Free web directory** — every Canadian transit agency listed in one unified,
  searchable table; ranks are free and crawlable; raw numbers are account-gated.
  Runs against the existing Postgres schema read-only (Drizzle introspect, no
  migrations from `web/`).
- **126-agency full Canadian census** (`db/seeds/06_agencies_full.sql`) — verified
  from open/public sources (Wikipedia, municipal sites, transit.land GTFS registry).
  Up from 10 launch agencies to 136 total. `service_area_population` left NULL;
  fiscal year defaults to calendar year. Re-runnable (`ON CONFLICT DO NOTHING`).
- **Expand-in-place directory rows** — each agency is a full-width table row
  (mode-group colour bar → name link → province → peek ranks → chevron). Expands
  inline to mode pills, rank grid, "Fundamentals pending" notice, and "Open full
  data →" link (wireframes-v5 interaction). No per-province grids; province is a
  column and a search term.
- **Paywall gate boundary** — raw metric values are structurally prevented from
  reaching unauthenticated clients: disjoint `FreeMetricView`/`PaidMetricView`
  types, a single server-only choke point (`access.ts`), ESLint import restriction,
  non-invertible 10-bucket trend shapes, and `force-dynamic` on detail routes so a
  paid render can't poison an anon cache.
- **Rank safety guards** — `reconcileRanks()` (server-side primary N<5 guard, 13
  unit tests) + `rankLabel`/`srRankLabel` (renderer-side short-circuit). Period-miss
  agencies (in the cohort but missing a row) show "not ranked — latest \<period\>"
  rather than vanishing; unsourced agencies show "Fundamentals pending".
- **Batch rank reads** — `getAllAgencyRanks()` reads all agency ranks in 3 constant
  DB queries instead of N+1 per agency. Home page load ~1.7s against a full 136-
  agency directory.
- **DEMO_AGENCY_SLUG = 'ttc'** — TTC detail page serves the full paid shape
  (numbers + provenance) to everyone including crawlers for SEO trust.
- **`manual_entry` source feed** documented in `db/seeds/05_source_feeds.sql`
  (previously live-only).

### Changed
- Home directory layout: one continuous alphabetical table of all agencies (not
  separate per-province card grids). Province is a column and search filter.
  Recorded in `DESIGN.md` as the canonical layout decision.
- `db/tests/00_seed_assertions.sql`: agency count relaxed to `>= 10` (census is
  growing); source-feed count bumped to 9.
