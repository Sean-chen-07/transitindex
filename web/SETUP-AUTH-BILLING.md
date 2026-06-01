# Setting up sign-in + payments (one-time)

This is the step-by-step for the three outside services the app uses. You only do this
once. None of it needs coding — it's all clicking around in three dashboards and copying
values into one file.

**Where the values go:** a file called `web/.env.local`. Copy `web/.env.example` to
`web/.env.local` first (it's already git-ignored, so your secrets never get committed):

```powershell
Copy-Item web\.env.example web\.env.local
```

Then open `web/.env.local` and fill in the blanks as you go below. Use **test mode** for
Stripe until you're ready to charge real money. Restart `npm run dev` after editing the file.

> Quick mental model: **Google + Resend** let people sign in. **Stripe** takes the $20/year.
> The app reads the membership status live from the database — the Stripe *webhook* is the
> only thing that ever marks someone "paid".

---

## 0. AUTH_SECRET (30 seconds)

This is a random string that signs the login cookie. Generate one:

```powershell
npx auth secret
```

That command writes `AUTH_SECRET=...` into `web/.env.local` for you. (If it asks to install
a package, say yes.) Also set:

```
AUTH_URL=http://localhost:3000
```

(When you deploy, `AUTH_URL` becomes your real site, e.g. `https://transitindex.ca`.)

---

## 1. Google sign-in → `AUTH_GOOGLE_ID`, `AUTH_GOOGLE_SECRET`

1. Go to **https://console.cloud.google.com/** and sign in. Top-left, create a new project
   (call it "TransitIndex"). Wait for it to finish, then select it.
2. Left menu → **APIs & Services → OAuth consent screen**.
   - User type: **External** → Create.
   - App name: "TransitIndex". User support email: your email. Developer contact: your email.
   - Save and continue through the screens (you can leave Scopes and Test users empty for now).
3. Left menu → **APIs & Services → Credentials → Create credentials → OAuth client ID**.
   - Application type: **Web application**.
   - Name: "TransitIndex web".
   - Under **Authorized redirect URIs**, click *Add URI* and paste exactly:
     ```
     http://localhost:3000/api/auth/callback/google
     ```
     (Later, add your live one too: `https://YOURDOMAIN/api/auth/callback/google`.)
   - Click **Create**. A popup shows your **Client ID** and **Client secret**.
4. Copy them into `web/.env.local`:
   ```
   AUTH_GOOGLE_ID=<the Client ID>
   AUTH_GOOGLE_SECRET=<the Client secret>
   ```

> While the consent screen is in "Testing" status, only Google accounts you add as **Test
> users** (OAuth consent screen → Audience → Test users) can sign in. Add your own email.
> Publishing the app removes that restriction (no Google review needed for basic email/profile).

---

## 2. Magic-link email → `AUTH_RESEND_KEY`, `AUTH_EMAIL_FROM`

Resend sends the "click here to sign in" emails.

1. Go to **https://resend.com/** and sign up (free tier is plenty to start).
2. Left menu → **API Keys → Create API Key**. Name it "TransitIndex". Copy the key (starts
   with `re_`).
   ```
   AUTH_RESEND_KEY=re_...
   ```
3. The "from" address:
   - **For first tests:** leave `AUTH_EMAIL_FROM=onboarding@resend.dev`. Resend's shared test
     sender works immediately, but it only delivers to **your own** Resend account email —
     fine for testing your own sign-in.
   - **For real users:** Resend → **Domains → Add Domain**, enter your domain, and add the DNS
     records Resend shows you (at your domain registrar). Once it's verified, set e.g.
     `AUTH_EMAIL_FROM=hello@yourdomain.ca`.

---

## 3. Payments → `STRIPE_SECRET_KEY`, `STRIPE_PRICE_ID`, `STRIPE_WEBHOOK_SECRET`

Make sure the **Test mode** toggle (top-right of the Stripe dashboard) is **ON** for all of this.

### 3a. The product + price → `STRIPE_PRICE_ID`
1. **https://dashboard.stripe.com/** → **Product catalog → Add product**.
2. Name: "TransitIndex membership". Pricing: **Recurring**, **Yearly**, amount **20.00**
   (CAD). Save.
3. On the product page, find the price you just made and copy its **Price ID** (starts with
   `price_`).
   ```
   STRIPE_PRICE_ID=price_...
   ```

### 3b. The secret key → `STRIPE_SECRET_KEY`
1. **Developers → API keys** (or top search "API keys").
2. Copy the **Secret key** (starts with `sk_test_` in test mode).
   ```
   STRIPE_SECRET_KEY=sk_test_...
   ```

### 3c. The webhook secret → `STRIPE_WEBHOOK_SECRET`
The webhook is how Stripe tells our app "this person paid". Two cases:

**Local testing (recommended first):** install the Stripe CLI
(https://docs.stripe.com/stripe-cli — `scoop install stripe`), then:
```powershell
stripe login
stripe listen --forward-to localhost:3000/api/stripe/webhook
```
The `listen` command prints a line like `Ready! ... webhook signing secret is whsec_...`.
Copy that:
```
STRIPE_WEBHOOK_SECRET=whsec_...
```
Leave `stripe listen` running in its own terminal while you test.

**Production (when deployed):** Stripe **Developers → Webhooks → Add endpoint**.
- Endpoint URL: `https://YOURDOMAIN/api/stripe/webhook`
- Events to send: `checkout.session.completed`, `customer.subscription.created`,
  `customer.subscription.updated`, `customer.subscription.deleted`.
- After creating it, click the endpoint → **Signing secret → Reveal** → copy the `whsec_...`
  into your production environment's `STRIPE_WEBHOOK_SECRET`.

---

## 4. Try it end to end

With `web/.env.local` filled in and (if testing payments) `stripe listen` running:

```powershell
npm --prefix web run dev
```

1. **Sign in:** open http://localhost:3000/account → it bounces you to **/sign-in**. Try the
   magic-link (check your email) and/or "Continue with Google". You should land back on
   /account showing "Open the full data — $20/year".
2. **Pay (test mode):** click **Subscribe — $20/year**. On Stripe's page use the test card
   **4242 4242 4242 4242**, any future expiry, any CVC/postal code. After paying you return
   to /account showing **"Membership active"**.
3. **Confirm the unlock:** open any agency detail page (other than the demo `ttc`) — the raw
   numbers are now visible instead of the locked "••••".
4. **Confirm live de-provisioning:** in /account click **Manage billing → cancel**, or in the
   Stripe dashboard cancel the subscription. On your next page load the numbers re-lock — the
   app reads status live, it never trusts a stale token.

> If sign-in or payment doesn't work, the most common cause is a missing/typo'd value in
> `web/.env.local` or forgetting to restart `npm run dev` after editing it. The app prints a
> clear error (e.g. "STRIPE_SECRET_KEY is not set") the first time it needs a missing value.

---

## What each variable is, in one line

| Variable | What it is | Where from |
|---|---|---|
| `AUTH_SECRET` | signs the login cookie | `npx auth secret` |
| `AUTH_URL` | your site's base URL | `http://localhost:3000` locally |
| `AUTH_GOOGLE_ID` / `AUTH_GOOGLE_SECRET` | Google sign-in | Google Cloud → Credentials |
| `AUTH_RESEND_KEY` | sends magic-link emails | Resend → API Keys |
| `AUTH_EMAIL_FROM` | the "from" of those emails | `onboarding@resend.dev`, then your domain |
| `STRIPE_SECRET_KEY` | lets the server talk to Stripe | Stripe → Developers → API keys |
| `STRIPE_PRICE_ID` | your $20/year price | Stripe → Product catalog |
| `STRIPE_WEBHOOK_SECRET` | verifies "they paid" messages | `stripe listen` locally / Webhooks in prod |
| `DATABASE_URL` | the database (already set) | Supabase → Connect → Session pooler |
