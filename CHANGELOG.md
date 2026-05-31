# Changelog

All notable changes to TransitIndex.

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
