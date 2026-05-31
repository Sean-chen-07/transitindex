# web/ — rules for any agent editing this directory

Inherit the repo-root CLAUDE.md. These are the `web/`-specific invariants. They are
load-bearing — violating them ships a scrapeable paywall or a misleading rank.

## NEVER

- **Never define or migrate tables here.** No `drizzle-kit push/generate/migrate`, no
  `CREATE/ALTER TABLE`. All schema lives in `../db/migrations` (Lane 0). New tables
  (e.g. Auth.js) are a Lane-0 migration that this app only *introspects*.
- **Never select a raw `value` outside `src/server/metrics/queries.ts`.** That module is
  the only place permitted to read `core.metric_values` / `metric_value_sources`. It is
  imported ONLY by `src/server/metrics/access.ts` (the ESLint rule enforces this).
- **Never put a raw number, full-resolution trend, or page-level provenance into a
  payload that an unauthenticated client can receive** — including RSC→client props,
  API responses, `generateMetadata`, JSON-LD, sitemap, or OpenGraph. The free path uses
  `FreeMetricView` (no `value` field) by construction.
- **Never reintroduce a cookie "free view" meter or any anonymous tracking.** Numbers are
  account-gated server-side. The killed meter is why.
- **Never format a rank without the suppression gate** (`rankLabel`/`srRankLabel`):
  `metric_ranks.rank`/`denominator` are nullable and unbounded, and the rank job does
  not suppress small pools — N<5 → "not yet ranked", period miss → "not ranked — latest
  <label>".

## ALWAYS

- Mark any module that touches the DB or secrets with `import "server-only"`.
- Add the reveal decision (paid OR demo) inside `access.ts` using non-forgeable inputs
  (the real session + the real route slug) — never a caller-supplied `isPaid` boolean.
- Keep detail routes `force-dynamic` so a paid render can't poison an anon cache.
- Run `npm run typecheck && npm run test && npm run lint && npm run build` before
  declaring a change done. The paywall tests (`transform.test.ts`, `shape.test.ts`,
  `access.a1.test.ts`) are the contract.
