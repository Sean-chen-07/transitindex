import "server-only";
import Stripe from "stripe";

// The ONE Stripe client for the whole server. The secret key is the live/test SECRET key
// (sk_…) — never the publishable key, and never shipped to a client bundle (this module is
// server-only). apiVersion is PINNED so a future SDK bump can't silently change request or
// webhook payloads under us; update it deliberately when we test a new version.
//
// Constructed LAZILY: `next build` collects route page-data by importing every route module,
// so a throw at import time would break builds in any environment without the key (CI). We
// throw the clear error on FIRST USE instead — a request that actually needs Stripe.
let client: Stripe | null = null;

function getStripe(): Stripe {
  if (client) return client;
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) {
    throw new Error(
      "STRIPE_SECRET_KEY is not set. Copy web/.env.example to web/.env.local and set your Stripe secret key (sk_…).",
    );
  }
  client = new Stripe(key, { apiVersion: "2026-05-27.dahlia" });
  return client;
}

// A thin proxy so call sites stay `stripe.checkout.sessions.create(...)` etc. — the real
// client (and the missing-key check) is created on the first property access. Functions are
// bound to the real client so `this` is correct for any method that lives on the instance.
export const stripe = new Proxy({} as Stripe, {
  get(_target, prop) {
    const real = getStripe();
    const value = Reflect.get(real, prop);
    return typeof value === "function" ? value.bind(real) : value;
  },
});
