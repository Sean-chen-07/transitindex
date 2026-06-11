# web/ — rules for any agent editing this directory

Inherit the repo-root CLAUDE.md. These are the `web/`-specific invariants. They are
load-bearing — violating them ships a bypassable download gate or a misleading rank.

## NEVER

- **Never define or migrate tables here.** No `drizzle-kit push/generate/migrate`, no
  `CREATE/ALTER TABLE`. All schema lives in `../db/migrations` (Lane 0). New tables
  (e.g. Auth.js) are a Lane-0 migration that this app only *introspects*.
- **Never select a raw `value` outside `src/server/metrics/queries.ts`.** That module is
  the only place permitted to read `core.metric_values`. It is imported ONLY by
  `src/server/metrics/access.ts` (the ESLint rule enforces this).
- **Never re-gate VIEWING.** Viewing is free by decision
  (docs/design/detail-view-metrics.md §6): every detail number ships to anonymous
  users. The paid artifact is the per-agency download — `/api/agency/[slug]/download`
  must check the LIVE session + `isPaid` server-side on every request. Never add a
  bulk / multi-agency export (deferred deliberately).
- **Never reintroduce a cookie "free view" meter or any anonymous tracking.** The
  download is account-gated server-side. The killed meter is why.
- **Never format a rank without the suppression gate** (`rankLabel`/`srRankLabel`):
  `metric_ranks.rank`/`denominator` are nullable and unbounded, and the rank job does
  not suppress small pools — N<5 → "not yet ranked", period miss → "not ranked — latest
  <label>".

## ALWAYS

- Mark any module that touches the DB or secrets with `import "server-only"`.
- Decide the download entitlement inside the route handler from non-forgeable inputs
  (the real session via `getSession()` + a live `isPaid()` check per request) — never a
  caller-supplied boolean and never a cached entitlement.
- Keep detail routes `force-dynamic` so a per-request decision can't poison a shared
  cache.
- Run `npm run typecheck && npm run test && npm run lint && npm run build` before
  declaring a change done. The contract tests (`transform.test.ts`,
  `detail-model.test.ts`, `csv.test.ts`, `access.a1.test.ts`) are the contract.
