# TransitIndex — Milestone 1 Build Plan

> **Status:** APPROVED for steps 1–5 (2026-05-31). Produced by a multi-agent design workflow
> (5 design slices → 3 adversarial stress-tests → synthesis). Two invariants (paywall integrity,
> empty-DB rank safety) failed the first design pass; every adversarial fix is folded in below.
>
> **User decisions (2026-05-31):**
> 1. **Auth** — DB sessions + Lane-0 migration `008` (steps 6–8, not in this first build).
> 2. **Scope caveat** — **NONE.** BC Transit and Metrolinx are ranked as normal agencies for now
>    (matches schema DECISION 3). The slug→caveat map and same-scope suppression in §4 are **dropped**.
> 3. **Demo un-gate** — **INCLUDE** a one-agency demo: a `DEMO_AGENCY_SLUG` constant whose detail page
>    serves the full paid shape (numbers + provenance) to anonymous users/crawlers. The other 9 stay
>    account-gated.
> 4. **Scope of first build** — steps 1–5 (free app + gate boundary against the empty DB), then pause
>    before auth/Stripe (steps 6–8) and the StatCan rank load (step 9).
>
> **Build status (2026-05-31):** steps 1–5 BUILT on branch `feat/m1-web` (not yet committed).
> `web/` scaffolded; schema mirrored from `db/schema.sql` (drizzle-kit `pull` hit a
> drizzle-kit/orm version mismatch — wired for later refresh; hand-mirror is the committed
> contract); free read layer + directory + detail + gate boundary done. **Verified:** `typecheck`
> clean, `lint` clean (choke-point rule active), `build` green (sitemap generated → live DB read OK),
> 21 unit tests pass (1 Postgres A1 skipped pending a test DB), runtime smoke against the empty DB
> renders pending states with no `Invalid Date`/`nullth`/`as of null`. Steps 6–9 not started.

The thinnest revenue-capable web app: a free, crawlable directory of 10 Canadian transit agencies
(ranks only), agency detail pages, and a $20/year Stripe gate that unlocks raw numbers. This plan is
the single source of truth for the `web/` build.

> **⚠️ Monetization superseded 2026-06-09.** The "$20/year Stripe gate that unlocks raw numbers" no longer
> describes the product: **all viewing is now free** (numbers, charts, statements — no gate), and the paid
> product is **per-agency dataset download by subscription** (pricing TBD). The read-layer and paywall
> *integrity* machinery below (server-only choke point, disjoint free/paid types) still stands as built,
> but the line it enforces moves from "numbers" to "download". Detail-page presentation also redesigned to
> two tabs. See [../design/detail-view-metrics.md §6](../design/detail-view-metrics.md) and
> [../../TODOS.md](../../TODOS.md).

---

## 1. Goal & guardrails

Build `web/` as a Next.js 15 App Router app that reads the existing Postgres schema **read-only**
(Drizzle introspect, never migrate), renders sensible "fundamentals pending" states against the
seed-only DB, and lights up ranks unchanged when the Lane A StatCan CLI populates
`core.metric_ranks`. Three invariants are non-negotiable and each has a mechanical enforcement
point, not just prose:

- **(a) READ-ONLY + INTROSPECT** — web never defines or migrates tables; the one new table set
  (Auth.js) is a Lane-0 migration (`008`), and the runtime DB role is locked to least-privilege so
  Postgres itself refuses any DDL.
- **(b) PAYWALL INTEGRITY** — raw numbers and recoverable proxies never reach an unauthenticated
  client, enforced at a single server-only choke point drawn around every value-bearing **table**
  (not one column), because the `web_reader` grant does *not* enforce it (verified:
  `db/schema.sql:1098,1084,1091,1119`).
- **(c) RANK SAFETY** — no "1st of 2", no cross-year/cross-scope ranks, no bare province codes,
  driven entirely by read-layer logic on the nullable, unsuppressed `metric_ranks` rows.

---

## 2. Route / file tree

```
db/migrations/
  008_auth_tables.sql          # LANE-0 (NOT web). Auth.js adapter tables + app.users ALTER +
                               # EXPLICIT grants for the 3 new tables + (optional) REVOKE on
                               # pending_values/metric_value_audit. Applied with the dbmate
                               # OWNER role, never web_reader. Must land before web auth runs.

web/
  package.json                 # next@15, react@19, drizzle-orm, drizzle-kit, postgres, next-auth@beta,
                               #   @auth/drizzle-adapter, @auth/core, stripe, recharts, tailwind, shadcn deps, zod.
                               #   Scripts: dev/build/start/lint + db:pull ONLY. NO push/generate/migrate.
  tsconfig.json                # strict, @/* -> web root, noUncheckedIndexedAccess on.
  next.config.ts               # typedRoutes; serverExternalPackages: ['postgres','stripe'].
  tailwind.config.ts           # DESIGN.md tokens -> theme; Outfit; .tnum tabular-nums; soft radius/shadow.
  postcss.config.mjs
  components.json              # shadcn config (RSC=true).
  drizzle.config.ts            # introspect-only: schemaFilter ['core','app'], out ./src/db/schema,
                               #   dbCredentials.url = DATABASE_URL (web_reader, least-priv). Comment: pull only.
  .env.example                 # all secrets (see §5). Note: DATABASE_URL is web_reader-equivalent;
                               #   paywall is CODE-enforced (web_reader CAN select metric_values).
  middleware.ts                # protect /account only. Everything else public + crawlable.
  README.md / CLAUDE.md        # introspect-only + server-only-paywall + "raw-value modules" rules.
  eslint.config.mjs            # no-restricted-imports: forbid importing the value-bearing schema
                               #   objects + raw query module ANYWHERE except src/server/metrics/access.ts.

  src/db/schema/
    core.ts                    # GENERATED by db:pull, committed, do-not-edit banner. core.* read types.
    app.ts                     # GENERATED by db:pull. app.* (incl. 008 auth tables after they land).
    index.ts                   # re-export.

  src/server/
    db.ts                      # import 'server-only'; the ONE postgres pool (sslmode=require,
                               #   session pooler 5432). Singleton. Never imported client-side.
    auth.ts                    # NextAuth v5: DrizzleAdapter bound to auth_id, Google + Resend(magic-link),
                               #   session.strategy = 'database'. callbacks.session injects bigint users.id.
    entitlement.ts             # import 'server-only'; getEntitlement(session) -> {paid} reading
                               #   app.users.subscription_status LIVE per request (React cache()). NO JWT claim.
    data/
      agencies.ts              # listAgencies() (province-grouped, full names), getAgencySummary(slug). Free-safe.
      ranks.ts                 # getAgencyRanks(slug) + getLatestRankedPeriodPerMetric(). Free-safe, no value.
      attribution.ts           # getAttribution(slug): source_documents license/title/url/date. Both tiers.
      freshness.ts             # getFeedFreshness() (global banner), getAgencyAsOf(slug). Tolerates zero rows.
      constants.ts             # MIN_DENOMINATOR_ALL = 5; SUBDIVISION deferred (see §4); scope-caveat map.
      types.ts                 # Free-path return types — NONE has a `value` field by construction.
    metrics/
      access.ts                # THE CHOKE POINT. import 'server-only'. ONLY importer of queries.ts.
                               #   getFreeMetrics(agencyId) + getPaidMetrics(agencyId, session).
      queries.ts               # import 'server-only'. ONLY module that touches metric_values /
                               #   pending_values / metric_value_audit / metric_value_sources.
      types.ts                 # FreeMetricView (no value) + PaidMetricView (value lives ONLY here).
      shape.ts                 # toShape(): bucketed, non-invertible 0..1 trend; suppress < 2 points.
      attribution.ts           # licenseToAttribution(license, meta) -> required notice. Both tiers.
      access.a1.test.ts        # IRON A1 (Postgres fixture). MANDATORY.
      noLeak.test.ts           # page-level anon-render scan incl. <head>. MANDATORY.
      shape.test.ts            # non-invertibility + bucket assertions.

  src/lib/
    format.ts                  # toOrdinal, rankLabel (null/zero/N<5 short-circuit), provinceName(code),
                               #   periodLabel passthrough. Pure, unit-tested.
    stripe.ts                  # import 'server-only'; configured Stripe SDK.

  src/server/billing/
    checkout.ts                # server action createCheckoutSession(): auth-required, $20/yr price,
                               #   logs conversion_events('checkout_start'). NEVER sets 'active'.

  src/app/
    layout.tsx                 # RSC root: Outfit, cream bg, header/footer. No tracking scripts.
    globals.css                # token CSS vars (DESIGN.md), body >=16px, .tnum, focus ring.
    page.tsx                   # Directory home (RSC). Search hero + province groups + AgencyCard.
    robots.ts                  # allow / and /agency/*; disallow /account,/api,/sign-in; sitemap link.
    sitemap.ts                 # home + /agency/[slug] per agency. Reads slugs via free data layer ONLY.
    sign-in/page.tsx           # RSC shell + small client form (magic-link + Google).
    account/page.tsx           # auth-required; subscription state; Subscribe / Manage (billing portal).
    agency/[slug]/page.tsx     # Detail (RSC). force-dynamic. Free shape always; paid subtree behind gate.
    api/auth/[...nextauth]/route.ts   # re-exports handlers from src/server/auth.ts.
    api/stripe/webhook/route.ts       # runtime='nodejs', raw body, signature verify, idempotent.
    actions/request-agency.ts  # 'use server': zod-validate, INSERT app.agency_requests. Returns {ok}.
    actions/log-conversion.ts  # 'use server': INSERT app.conversion_events (wall_hit|gate_view). Returns {ok}.

  src/components/
    directory/agency-card.tsx        # RSC: mode bar + icon+label, name/city, pills, rank grid, chevron.
    directory/agency-card-expand.tsx # 'use client': Radix Collapsible expand-in-place. Children only.
    directory/rank-grid.tsx          # RSC: ordinals + SR label; 'not yet ranked' / 'not ranked — latest X'.
    directory/search-box.tsx         # 'use client': filters already-shipped rank-only payload. 0-results.
    detail/gated-metric.tsx          # 'numbers gated (anon)': real rank + blurred SERVER placeholder + CTA.
    detail/upgrade-dialog.tsx        # shadcn Dialog, focus-trapped. NO meter. Coral CTA + sign-in.
    detail/spreadsheet.tsx           # PAID ONLY. dynamic import behind server isPaid gate. Real <table>.
    detail/checkout-button.tsx       # 'use client': POSTs checkout action; fires log-conversion(gate_view).
    common/source-footnote.tsx       # text-only attribution, both tiers.
    common/states.tsx                # skeleton / pending / stale / 0-results / error-feed-down primitives.
    ui/.gitkeep                      # shadcn generated primitives land here.
```

> **Note on `src/`:** the design slices disagreed on `web/app` vs `web/src/...`. This plan
> standardizes on **`web/src/`** throughout (keeps server/data modules out of the route tree).

---

## 3. The read-data layer

**Introspect setup.** `drizzle.config.ts` exposes exactly one db command — `db:pull`
(`drizzle-kit pull`) — with `schemaFilter: ['core','app']` and `dbCredentials.url =
process.env.DATABASE_URL` (the least-privilege `web_reader` login). `generate`/`push`/`migrate` are
deliberately absent from `package.json`. Generated schema is **committed** with a do-not-edit banner
so Vercel builds never need live-DB access. After Lane-0 migration `008` lands, re-run `db:pull` and
review the diff.

**Single pool.** `src/server/db.ts` (`import 'server-only'`) opens the only DB connection (Supabase
session pooler, port 5432, `sslmode=require`), asserts env present, and is never imported by a
client component.

**Free-safe query functions** (all `import 'server-only'`, none selects any raw value column):

| Function | Reads | Returns |
|---|---|---|
| `listAgencies()` | `core.agencies` | `AgencyListGroup[]` grouped by subdivision, **full province name** via `provinceName()`; `hasAnyRank` flag. Empty-DB: all 10 agencies, `hasAnyRank=false`. |
| `getAgencySummary(slug)` | `core.agencies`, `agency_modes`, `modes` | identity + modes only |
| `getAgencyRanks(slug)` | `metric_ranks` ⋈ `metrics` ⋈ `reporting_periods`, `comparison_set='all'` | `AgencyRank[]` — **reconciled against the cohort latest period** (below). No `value`. |
| `getLatestRankedPeriodPerMetric()` | `metric_ranks` (`comparison_set='all'`) ⋈ `reporting_periods` | per `metric_id`: `max(end_date)` + that period's `label`. The cohort-latest fact. |
| `getAttribution(slug)` | `source_documents` | `Attribution[]` (license/title/url/date). Both tiers. No page-level provenance. |
| `getFeedFreshness()` | latest `feed_runs` per feed | `FeedFreshness[]`. Returns `[]` when no runs — banner shows neutral "Data being sourced", never "Invalid Date". |
| `getAgencyAsOf(slug)` | `max(reporting_periods.end_date)` of ranked periods | `string \| null` → renders "" when null, never "as of null". |

**Period-miss reconciliation (RANK SAFETY).** `getAgencyRanks` does **not** simply return the rows
that exist. For each metric applicable to the agency it joins the agency's row (if any) against
`getLatestRankedPeriodPerMetric()`:
- agency has a row in the cohort's latest period → `status:'ranked'`;
- cohort has a latest period but agency has **no** row in it → `status:'not_ranked_period_miss'`,
  `periodLabel` = the **cohort's** label (renders **"not ranked — latest Mar 2026"** — driven off
  `reporting_periods.label`, never a hard-coded "FYxxxx");
- cohort has no ranks at all → `status:'pending'`.

This is required **at launch**: StatCan `monthly_ridership` covers only ~7 of the 10 agencies, so
TTC/STM/Metrolinx/MiWay/Burlington would otherwise *silently vanish* from the metric instead of
showing the period-miss copy.

**Defensive suppression types:**

```ts
type RankStatus = 'ranked' | 'not_yet_ranked' | 'not_ranked_period_miss' | 'pending';
interface AgencyRank {
  metricCode: string; metricDisplayName: string; unitType: string|null;
  higherIsBetter: boolean|null; comparisonSet: 'all'; status: RankStatus;
  rank: number|null; denominator: number|null; ordinal: string|null;
  serviceScope: string|null;     // surfaced so the page can prove same-scope comparison
  scopeCaveat: string|null;      // from the slug→caveat constant (BC Transit / Metrolinx)
  periodLabel: string; periodEnd: string; computedAt: string;   // NO `value`
}
```

`getAgencyRanks` defensively drops/relabels rows where `rank IS NULL OR denominator IS NULL OR
denominator < MIN_DENOMINATOR_ALL (5)` → `not_yet_ranked`. **This is the PRIMARY N<5 guard, not a
"mirror"** — verified: migration `005:34` says *"no minimum pool needed"*, so the merged Lane A rank
job does **not** suppress small pools. The read layer is the only thing standing between the user
and "1st of 2".

---

## 4. The rank / gate boundary (paywall integrity)

**The grant trap, verified.** `web_reader` has `GRANT SELECT` on **four** value-bearing tables
(`db/schema.sql`): `metric_values` (`:1098` — and its `value`, `crosscheck_value:330`, free-text
`notes:334`), `pending_values` (`:1119` — `value` + `reviewer_notes`), `metric_value_audit` (`:1084`
— `old_value`/`new_value`), and `metric_value_sources` (`:1091`). The DB does **not** enforce the
paywall. Enforcement is code-only.

**Single choke point, drawn around TABLES not columns.** `src/server/metrics/queries.ts` is the
**only** module in the repo permitted to import the Drizzle objects for *all four* value-bearing
tables. An ESLint `no-restricted-imports` rule forbids importing those schema objects — and
`queries.ts` itself — anywhere except `src/server/metrics/access.ts`. Free-path selects explicitly
exclude `crosscheck_value`, `notes`, and `reviewer_notes`.

**Two disjoint types make leakage a compile error:**

```ts
type FreeMetricView = {
  metricCode: string; displayName: string; unit: string;        // unit LABEL, e.g. 'trips/month' — not a value
  rank: number|null; denominator: number|null;
  direction: 'higher_is_better'|'lower_is_better'|'neutral';
  serviceScope: string|null; scopeCaveat: string|null;
  asOfLabel: string; attribution: string; shape: number[];      // bucketed, <=12 pts, >=2 pts or empty
  suppressedReason?: 'below_min_denominator'|'no_comparable_period'|'pending';
};   // NO `value` — structurally un-serializable into a free payload
type PaidMetricView = FreeMetricView & {
  value: number; currency: string|null; periodLabel: string; serviceScope: string;
  provenance: { sourceTitle:string; sourceUrl:string|null; pageNumber:number|null; tableReference:string|null; license:string }[];
  trend: { periodLabel:string; value:number }[];
};   // raw `value` lives ONLY here
```

`getFreeMetrics(agencyId)` reads ranks + attribution + freshness only. `getPaidMetrics(agencyId,
session)` calls `isPaid(session)` **internally as its first statement** — there is **no
caller-supplied `{isPaid:true}` boolean** (a forgeable capability; removed). If not paid it returns
the **free shape** (not a throw — anonymous/crawler detail pages must still render ranks for SEO).
`isPaid` reads `app.users.subscription_status === 'active'` **live from the DB per request**, wrapped
in React `cache()` for one lookup per render — **never** a JWT claim (so a cancelled subscriber loses
access on the next request, not at token refresh).

**Trend shape, non-invertible.** `toShape()` min-max normalizes **and quantizes to ≤10 coarse
buckets** so float inter-period ratios are not recoverable, and **suppresses the chart entirely below
2 historical points**. `shape.test.ts` asserts two series differing by <1% produce identical bucketed
output.

**Cache safety.** `agency/[slug]/page.tsx` sets `export const dynamic = 'force-dynamic'`. The
cacheable render contains **only** the free shape; `isPaid()` never influences a cacheable output, so
a paid render can never poison a shared cache served to an anonymous hit.

**Module-graph unreachability.** The paid `detail/spreadsheet.tsx` (carrying
`trend`/`value`/`provenance`) is **dynamically imported only after a server-side `isPaid()` gate**,
so the paid component's code *and* data never enter the anonymous module graph. (TypeScript types
alone are erased at runtime and do not stop RSC→client serialization — the component must be
*unreachable*, not merely *unrendered*.)

**Metadata/SEO.** `generateMetadata`, JSON-LD, `sitemap.ts`, and OpenGraph call **only**
`getFreeMetrics`. JSON-LD emits rank facts, never quantitative metric values.

**Scope correctness (user decision: no caveats in M1).** Ranks still compare a single matching
`service_scope` (the read layer filters on it), but BC Transit and Metrolinx are ranked as **normal
agencies** — no slug→caveat text, no same-scope suppression. This matches schema DECISION 3 (the
scope-caveat guard was dropped). The `scopeCaveat` field is removed from `AgencyRank`. Revisit only
if a buyer disputes a cross-scope rank.

**Demo un-gate (user decision: include one demo agency).** A single `DEMO_AGENCY_SLUG` constant
(`src/server/data/constants.ts`, default `'ttc'`) marks one agency whose detail page renders the full
**paid shape** (numbers + page-level provenance + full trend) to **everyone**, including crawlers — a
deliberate SEO/trust taste. Mechanically: the detail page computes `showNumbers = slug ===
DEMO_AGENCY_SLUG || isPaid(session)` and only then dynamically imports the paid `spreadsheet`. The
choke point is unchanged — `getPaidMetrics` is still the only path to raw values; the demo branch just
satisfies the gate for that one slug. The other 9 agencies remain fully account-gated, and the IRON A1
/ noLeak tests assert leakage only against a **non-demo** agency.

**Subdivision (paid province re-rank) — DEFERRED out of M1.** Verified province counts: ON=5, QC=1,
BC=2, AB=2 — and post-StatCan the ranked pool is smaller still, so *every* `comparison_set='subdivision'`
cohort is N<5. Shipping it would mean "not yet ranked" for 100% of provinces. M1 ships
`comparison_set='all'` only; the free path **hard-filters `comparison_set='all'`** so a subdivision
row can never leak into a free payload.

**`rankLabel` / `toOrdinal`.** Short-circuits to "not yet ranked" when `rank IS NULL || denominator
IS NULL || denominator === 0 || denominator < 5` **before** formatting. Unit-tested for every
null/zero combination (no "nullth", no "rank of ").

**The IRON A1 test** (`access.a1.test.ts`, MANDATORY, against a real Postgres test DB with
`db/migrations` applied so it exercises the real `web_reader` grant):
1. Seed one agency with a known `value` (1234567), a `crosscheck_value`, a `notes` string containing
   a number, plus its rank.
2. `JSON.stringify(getFreeMetrics(...))` contains the ordinal but **none** of: the raw number, the
   crosscheck, the notes number, nor any value within 0.1%.
3. `getPaidMetrics(id, anonymousSession)` === free shape (no `value` key on any item).
4. `getPaidMetrics(id, paidSession)` **does** include `value`.

**`noLeak.test.ts`** (MANDATORY): render `agency/[slug]/page.tsx` with an **anonymous** session
against a **populated** agency; serialize the full RSC/HTML output **including `<head>`** (title,
description, OpenGraph, JSON-LD) and assert the ordinal appears but no `value`/`trend`/`provenance`
key and no raw-number signature.

---

## 5. Auth + Stripe

**Resolved table strategy: database sessions + a Lane-0 migration `008` (NOT JWT, NOT web-defined
tables).** Magic-link sign-in requires persisted verification tokens, and a DB session lets
`getEntitlement` read `subscription_status` live (no stale "paid" after a webhook flips status).
Auth.js adapter tables therefore exist, but are authored in **`db/migrations/008_auth_tables.sql`
(Lane 0)** and only *introspected* by web — never Drizzle-defined.

**`db/migrations/008_auth_tables.sql`** (dbmate up/down, applied with the schema-OWNER role, never
`web_reader`):
- `ALTER TABLE app.users ADD COLUMN auth_id uuid NOT NULL UNIQUE DEFAULT gen_random_uuid(), ADD COLUMN name text, ADD COLUMN image text, ADD COLUMN email_verified timestamptz;`
- `CREATE TABLE app.accounts (... user_id uuid REFERENCES app.users(auth_id) ON DELETE CASCADE, PRIMARY KEY (provider, provider_account_id));`
- `CREATE TABLE app.sessions (session_token text PRIMARY KEY, user_id uuid REFERENCES app.users(auth_id) ON DELETE CASCADE, expires timestamptz NOT NULL);`
- `CREATE TABLE app.verification_token (identifier text, token text, expires timestamptz NOT NULL, PRIMARY KEY (identifier, token));`
- **Explicit grant:** `GRANT SELECT,INSERT,UPDATE,DELETE ON app.accounts, app.sessions, app.verification_token TO web_reader;` — verified necessary: `007` uses `GRANT ... ON ALL TABLES` which does **not** retro-cover new tables, and there is no `ALTER DEFAULT PRIVILEGES` in the repo. Omitting this = silent login failure.
- **Defense-in-depth:** `REVOKE SELECT ON core.pending_values, core.metric_value_audit FROM web_reader;` — web has no free *or* paid use for either, so close the grant trap for them at the DB layer.
- **id-type reconciliation:** keep the existing `app.users.id` bigint identity (still the FK target
  for `conversion_events`/`watchlists`); the adapter binds only to the new `auth_id uuid`.
  Down-migration fully reverses (drop 3 tables + drop the 4 added columns) — safe pre-launch with
  zero real users. (Verify `gen_random_uuid()` / pgcrypto availability on Supabase at build.)

**Runtime role lock (READ-ONLY enforcement).** `DATABASE_URL` must be a **LOGIN role that is a
MEMBER of `web_reader`** (or has identical privileges): USAGE-not-CREATE on `app`/`core`, SELECT-only
on `core`, DML-only on `app`, owns no tables. With this, an accidental `drizzle-kit push`, the
adapter, or any DDL attempt is **refused by Postgres**, not merely by a missing npm script.
`.env.example` states this explicitly; the dbmate/owner credential is **never** placed in `web/.env`.
Extend `db/tests/04_grants.sql` (Lane 0) to assert the login role lacks CREATE on `app`/`core` and
lacks DDL on `app.users`, and that DML on the 3 new auth tables is present.

**Providers & flow.** NextAuth v5 with Google + Resend (magic-link, single `AUTH_RESEND_KEY`, no SMTP
creds). `createCheckoutSession()` (server action, auth-required) creates a Stripe Checkout
(`mode:'subscription'`, the $20/yr price, `client_reference_id = users.id`, `metadata.userId`) and
logs `conversion_events('checkout_start')` — it **never** sets `active` optimistically. The
**webhook is the only writer of `subscription_status`**: `runtime='nodejs'`, raw body,
signature-verified, idempotent on `event.id`, status map `active|trialing→active`, `past_due→past_due`,
`canceled|unpaid|incomplete_expired→inactive` (any unmapped Stripe status coerces to a safe default
so the `CHECK` constraint never 500s into a retry storm). Account page includes a Stripe Billing
Portal link for self-serve cancel.

**Env vars (`.env.example`):** `DATABASE_URL` (web_reader login, pooler 5432, sslmode=require),
`AUTH_SECRET`, `AUTH_URL`, `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`, `AUTH_RESEND_KEY`,
`STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID`, `NEXT_PUBLIC_SITE_URL`.

---

## 6. DESIGN.md reconciliation + component map

**Surgical edits to `DESIGN.md`** (touch only the meter lines + states table + wireframe label):
- **Line 65–66 (component #5):** replace the `"1 free / used"` metered dialog with: *"Upgrade dialog
  (account-gate): what-you-unlock list, one coral CTA, sign-in (magic-link + Google), reassurance. NO
  meter, NO free-view count — numbers are account-gated, never metered. Focus-trapped, ESC closes,
  dimmed background `aria-hidden`."*
- **Line 71 (states table #8):** append three first-class states:
  - **numbers gated (anonymous)** | detail page | ranks shown; raw value blurred + lock glyph +
    "Open full data — $20/yr" CTA (NOT a metered wall).
  - **not yet ranked (N<5)** | card + detail | "not yet ranked" when denominator < 5; "not ranked —
    latest Mar 2026" on period miss.
  - **error / feed down** | card + detail | honest "Data temporarily unavailable" fallback.
- **Line 102 (+17–18):** change wireframe annotation "→ gate" to "→ upgrade dialog"; add a one-line
  banner that the v3/v4/v5 wireframes' cookie-meter is **superseded** by the account-gate.
- Add a "Status update 2026-05-31" note recording the reconciliation.
- **Leave untouched** the legitimate free→paid tier language (lines 17–18, 25, 50, 52, 55–57, 97) —
  that is tier vocabulary, not meter strings.

**Component map (two moods, one token layer).** A single set of CSS variables in `globals.css` drives
both surfaces (`--bg #F4F0E7`, `--card`, `--ink/-2/-3`, `--line`, `--grid`, `--coral`/`--coral-soft`,
`--teal`/`--teal-soft`, mode accents `--blue/--sage/--yellow`); the "mood" difference is radius +
density, not two themes. Outfit is the sole font; `.tnum` (tabular-nums) on every figure surface.
Mode-group color is **always paired with an icon + label** (color never the sole signal). Coral is
reserved for action/upsell, teal for interactive-positive — **never** green/red editorial on a rank
(`higher_is_better` is nullable/neutral). Key components: `agency-card` (Card + Collapsible),
`rank-grid` (ordinals + SR label "ranked Nth of M" + period-miss/N<5 states), `gated-metric` (real
rank + blurred **server placeholder** — the real value never enters the anon payload; blur is
affordance, not enforcement), `upgrade-dialog` (Radix Dialog, focus-trap + ESC + `aria-hidden`
background, no meter), `spreadsheet` (paid, real `<table>` + caption/scope th, sparkline with text
alternative), `source-footnote` (text-only, both tiers). WCAG 2.1 AA: 44px targets, body ≥16px,
contrast ≥4.5:1.

---

## 7. Build sequence

Ordered so the app works against the **empty** DB first, then auth/billing, then ranks light up.
**The Lane-0 `008` migration must land and be applied before Step 7 (web auth).**

1. **Scaffold `web/`** — Next 15 + TS + Tailwind + shadcn, token layer, layout/globals. → *verify:*
   `npm run dev` serves a styled empty home.
2. **Introspect** — `drizzle.config.ts` (pull-only), `src/server/db.ts` pool, `npm run db:pull`
   against the live seed DB, commit generated schema with banner. → *verify:* `core.*` + `app.*` read
   types compile; no `push`/`generate` script exists.
3. **Free read layer** — `data/*` (+ `getLatestRankedPeriodPerMetric`), `format.ts` (province names,
   `rankLabel` null/zero short-circuit). → *verify:* `ranks.test.ts` passes incl. a fixture row
   `rank=1/denominator=2` rendering "not yet ranked", and null/zero/period-miss cases.
4. **Directory + detail (free only)** — home with search + province groups (full names),
   `agency-card`, `rank-grid`, detail page `force-dynamic` rendering `getFreeMetrics`, `states.tsx`,
   `robots.ts`, `sitemap.ts`. → *verify:* against the seed-only DB every agency shows "Fundamentals
   pending"; home + every detail page render with **zero** ranks/values/feed_runs and no "as of
   null"/"Invalid Date"/"nullth" (empty-DB integration test).
5. **Gate boundary** — `metrics/{types,queries,access,shape}.ts`, ESLint import restriction,
   `gated-metric` + `upgrade-dialog`, paid `spreadsheet` behind a dynamic-import server gate. →
   *verify:* IRON A1 + `noLeak.test.ts` (incl. `<head>`) + `shape.test.ts` pass; ESLint fails if any
   module other than `access.ts` imports `queries.ts` or a value-bearing schema object.
6. **Lane-0 `008`** — author + `dbmate up` with the owner role; regenerate `db/schema.sql`; extend
   `db/tests/04_grants.sql`; re-run `db:pull` and review diff. → *verify:* grants test passes (login
   role: no CREATE on `app`/`core`, DML on the 3 auth tables, no SELECT on
   `pending_values`/`metric_value_audit`).
7. **Auth** — `src/server/auth.ts` (DrizzleAdapter→`auth_id`, Google + Resend, database sessions),
   route handler, `middleware.ts` (protect `/account`), sign-in page, `entitlement.ts` (live read +
   `cache()`). → *verify:* a magic-link round-trip against a throwaway DB completes and writes a
   session; `getEntitlement` reflects live `subscription_status`.
8. **Stripe** — `lib/stripe.ts`, `billing/checkout.ts`, webhook route
   (nodejs/raw/idempotent/status-map), account page + billing portal, `checkout-button` +
   `log-conversion(gate_view)`. → *verify:* test-mode checkout flips `subscription_status` to
   `active` via webhook; a paid session then unlocks `value` on a detail page; lapsing the sub
   re-locks it on the next request (live read, not JWT).
9. **Ranks light up** — run the Lane A StatCan CLI (`python -m transitindex_ingest statcan <csv>`) to
   populate `core.metric_ranks`. → *verify:* ranked agencies show ordinals; non-StatCan agencies show
   "not ranked — latest <period>" (not vanished); no N<5 "1st of 2"; no cross-scope rank for
   bc-transit/metrolinx.

---

## 8. Open decisions for the user

1. **Auth.js table strategy** — *Recommendation:* DB sessions + Lane-0 `008` migration (magic-link
   needs token persistence; live `subscription_status` reads avoid stale-paid). Alternative
   (Google-only, defer magic-link) only if you want to skip `008` for the first cut. **Decide:**
   confirm `008`, or ship Google-only first.
2. **Scope caveat: now vs defer** — *Recommendation:* hard-code the two known caveats (BC Transit =
   Victoria, Metrolinx = GO+UP) keyed by slug for M1, and suppress any metric that can't be shown
   same-scope. Alternative: petition Lane 0 for an `agencies.coverage_note` column later. **Decide:**
   hard-code now (recommended) vs suppress those two agencies' ranks until a column exists.
3. **SEO trust-builder (un-gate one demo agency)** — *Recommendation:* **keep out of M1** — it
   reopens the scrape surface and pre-judges a locked decision; the clean account-gate doesn't block
   adding a `demo` flag later. **Decide:** keep out (recommended) vs add a one-prop demo un-gate.
4. **Multi-provider account linking** — *Recommendation:* key the account on email for M1 (single $20
   sub per email; `app.users.email` is already UNIQUE); defer a true `accounts`-based multi-provider
   link. **Decide:** confirm email-keying.
5. **Wireframes** — v3/v4/v5 still render the killed meter. *Recommendation:* **annotate-only**
   (superseded banner in DESIGN.md); the build follows DESIGN.md, not the HTML. **Decide:** annotate
   (recommended) vs re-export.

---

## 9. Explicitly out of scope (M1)

- **Compare view** (multi-agency side-by-side) — Phase 2+.
- **Watchlists / saved dashboards / per-user accounts beyond billing** — `app.watchlists` exists in
  schema but is **Phase 3**, untouched here.
- **PDF ingest pipeline (Lane M2)** — frozen; M1 ranks come only from the Lane A StatCan CLI.
- **Paid subdivision / province re-rank** — deferred: no province has ≥5 launch agencies (see §4).
- **Anonymous metering / cookie "1 free view" meter / any device tracking** — killed; numbers are
  account-gated server-side, full stop.
- **Demo-agency un-gate trust-builder** — out unless the user reverses it (§8.3).
