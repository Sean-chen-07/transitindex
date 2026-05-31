# `web/` — TransitIndex web app (Milestone 1)

Next.js 15 (App Router) + TypeScript + Tailwind. A **pure reader** of the Postgres
schema owned by `db/` (Lane 0): a free, crawlable directory of Canadian transit agencies
(ranks only) with agency detail pages whose raw numbers are account-gated.

> Status: **steps 1–5** of `../M1-WEB-PLAN.md` (free app + gate boundary against the
> empty schema). Auth + Stripe (steps 6–8) and the StatCan rank load (step 9) are not
> built yet.

## Run it

```bash
cp .env.example .env.local   # set DATABASE_URL (a least-privilege web_reader login)
npm install
npm run dev                  # http://localhost:3000
npm run typecheck            # tsc --noEmit
npm run test                 # vitest (paywall + rank-safety unit tests)
npm run lint
npm run build
```

## The three invariants (and where each is enforced)

1. **Read-only / introspect.** The app never defines or migrates tables. `package.json`
   has **only** `db:pull` — no `push`/`generate`/`migrate`. The runtime `DATABASE_URL`
   must be a least-privilege `web_reader` login so Postgres itself refuses DDL. Read
   types live in `src/db/schema/` (currently hand-mirrored from `db/schema.sql`; refresh
   with `npm run db:pull` once the drizzle-kit/orm versions align).
2. **Paywall integrity.** Raw numbers never reach an unauthenticated client. The ONLY
   module allowed to read value-bearing tables is `src/server/metrics/queries.ts`,
   imported ONLY by the choke point `src/server/metrics/access.ts` (ESLint-enforced).
   Free and paid views are disjoint types (`FreeMetricView` has no `value` field), trend
   shapes are quantized non-invertibly, and metadata/sitemap call only the free path.
3. **Rank safety.** `metric_ranks` is nullable with no minimum-pool guard, so the read
   layer (`@/lib/format` + `src/server/data/ranks.ts`) suppresses N<5 ("not yet ranked"),
   renders period misses ("not ranked — latest <label>"), and short-circuits null/zero.

## Layout

- `src/db/schema/` — generated/mirrored read types (do not hand-edit beyond the mirror).
- `src/server/db.ts` — the one server-only DB pool.
- `src/server/data/` — free-safe queries (agencies, ranks, attribution, freshness).
- `src/server/metrics/` — the paywall choke point (`access.ts`), the only raw reader
  (`queries.ts`), pure transforms (`transform.ts`), and the trend shape (`shape.ts`).
- `src/server/entitlement.ts` — paid check (stubbed until step 7's Auth.js wiring).
- `src/components/` — directory, detail, common, and shadcn-style ui primitives.
- `src/app/` — routes, robots/sitemap, server actions.
