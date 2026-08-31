# Deploying the website to Vercel

The web app lives in `web/` inside this repo, so Vercel needs to be told that — it is
the one setting people get wrong. Everything else is filling in the same values that
already sit in `web/.env.local`, plus three things that must point at the real domain
instead of `localhost`.

Repo: `Sean-chen-07/transitindex` · branch `master`.

---

## 1. Create the project

1. Go to <https://vercel.com/new> and pick **Import Git Repository → transitindex**.
2. **Root Directory: `web`** ← click *Edit* next to Root Directory and choose the `web`
   folder. Without this the build fails immediately ("no package.json").
3. Framework Preset: **Next.js** (auto-detected). Leave build/install commands alone.
4. Add the environment variables below *before* clicking Deploy — the build reads the
   database at build time, so a deploy with no `DATABASE_URL` will fail.

## 2. Environment variables

Add these under **Settings → Environment Variables** (Production + Preview). The values
for most of them are the ones already in your local `web/.env.local`.

| Variable | Value for production |
|---|---|
| `DATABASE_URL` | The `web_reader` connection string. **Use Supabase's Transaction pooler (port 6543)**, not the session pooler you use locally — serverless functions open and drop connections constantly. Keep `?sslmode=require`. |
| `NEXT_PUBLIC_SITE_URL` | `https://<your-vercel-domain>` — **not** localhost |
| `AUTH_URL` | `https://<your-vercel-domain>` — **not** localhost |
| `AUTH_SECRET` | Same as local, or generate a fresh one with `npx auth secret` |
| `AUTH_GOOGLE_ID` | Same as local |
| `AUTH_GOOGLE_SECRET` | Same as local |
| `AUTH_RESEND_KEY` | Same as local |
| `AUTH_EMAIL_FROM` | Same as local (a Resend-verified sender once you launch properly) |
| `STRIPE_SECRET_KEY` | Test key is fine until you actually charge people |
| `STRIPE_PRICE_ID` | Same as local |
| `STRIPE_WEBHOOK_SECRET` | **Different in production** — see step 4 |

## 3. Point Google sign-in at the new domain

Google Cloud Console → Credentials → your OAuth client → **Authorized redirect URIs**,
add:

```
https://<your-vercel-domain>/api/auth/callback/google
```

Until this is added, Google sign-in returns a redirect-mismatch error. The magic-link
email sign-in works without it.

## 4. Point Stripe at the new domain

Stripe Dashboard → Developers → Webhooks → **Add endpoint**:

- URL: `https://<your-vercel-domain>/api/stripe/webhook`
- Events: `checkout.session.completed`, `customer.subscription.created`,
  `customer.subscription.updated`, `customer.subscription.deleted`

Stripe then shows a **signing secret** (`whsec_…`) for that endpoint. Put that value in
`STRIPE_WEBHOOK_SECRET` on Vercel and redeploy. This is not the same secret as the one
your local `stripe listen` prints — memberships will silently never activate if you
reuse the local one.

## 5. After it's live

- Every push to `master` redeploys automatically.
- If you attach a custom domain later, update `AUTH_URL`, `NEXT_PUBLIC_SITE_URL`, the
  Google redirect URI, and the Stripe endpoint URL to match.

## Known issues to fix before you tell anyone about the site

From the 2026-08-31 audit — none block deploying, all are visible to a visitor:

- The homepage banner says "Data is being sourced…" permanently, because nothing in the
  ingest pipeline ever writes the `last_good_at` field it reads.
- Roughly 521 of 657 agency cards show "—" in most slots: the card asks for metrics US
  agencies don't report, while the ones they *do* report sit unused in the database.
- Ranks can compare the wrong periods across the US/Canada mix, so an agency can show a
  rank from a different year than the figure printed beside it.

See `TODOS.md` and the audit notes for the fixes.
