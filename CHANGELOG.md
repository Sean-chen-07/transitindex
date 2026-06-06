# Changelog

All notable changes to TransitIndex.

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
