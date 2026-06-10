"use server";

import "server-only";
import { redirect } from "next/navigation";
import { eq } from "drizzle-orm";
import { db } from "@/server/db";
import { users, conversionEvents } from "@/db/schema";
import { getSession } from "@/server/entitlement";
import { stripe } from "@/lib/stripe";

// The site origin Stripe redirects back to. NEXT_PUBLIC_SITE_URL is the canonical origin
// (e.g. https://transitindex.ca); we only read it server-side here.
const siteUrl = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

/**
 * Start a subscription checkout. The price comes from the STRIPE_PRICE_ID env price
 * object; TODO(pricing): update copy sites when pricing is decided. Auth-required: an
 * anonymous caller is sent to sign-in first (callbackUrl=returnTo so they land back where
 * they started). returnTo is read from the posted form when it is a same-site path
 * (starts with "/", not "//" — never a caller-supplied scheme/host); calls without a form
 * (the account page) default to /account. We pass the bigint app.users.id as
 * client_reference_id so the webhook can map the completed session back to our user —
 * subscription_status is NEVER written here, only by the webhook.
 */
export async function createCheckoutSession(formData?: FormData): Promise<void> {
  const rawReturnTo = formData?.get("returnTo");
  const returnTo =
    typeof rawReturnTo === "string" &&
    rawReturnTo.startsWith("/") &&
    !rawReturnTo.startsWith("//")
      ? rawReturnTo
      : "/account";

  const session = await getSession();
  if (!session?.userId) {
    redirect(`/sign-in?callbackUrl=${encodeURIComponent(returnTo)}`);
  }

  const [user] = await db
    .select({ email: users.email })
    .from(users)
    .where(eq(users.id, session.userId));

  const checkoutSession = await stripe.checkout.sessions.create({
    mode: "subscription",
    line_items: [{ price: process.env.STRIPE_PRICE_ID, quantity: 1 }],
    client_reference_id: String(session.userId),
    customer_email: user?.email,
    // Stamp the bigint user id on the subscription so customer.subscription.* webhooks can
    // map back to the user without depending on checkout.session.completed arriving first.
    subscription_data: { metadata: { userId: String(session.userId) } },
    success_url: `${siteUrl}${returnTo}?checkout=success`,
    cancel_url: `${siteUrl}${returnTo}?checkout=cancel`,
  });

  // Funnel instrumentation — the user reached Stripe. Same INSERT shape as
  // app/actions/log-conversion.ts; never touches subscription_status.
  await db.insert(conversionEvents).values({
    eventType: "checkout_start",
    userId: session.userId,
  });

  if (!checkoutSession.url) {
    throw new Error("Stripe did not return a checkout URL.");
  }
  redirect(checkoutSession.url);
}

/**
 * Open the Stripe billing portal so an active member can update or cancel their card/plan.
 * Auth-required. The Stripe customer id lives in app.users.subscription_source (written by
 * the webhook on checkout.session.completed); without it there is nothing to manage, so we
 * fall back to a fresh checkout.
 */
export async function createBillingPortalSession(): Promise<void> {
  const session = await getSession();
  if (!session?.userId) {
    redirect("/sign-in?callbackUrl=/account");
  }

  const [user] = await db
    .select({ customer: users.subscriptionSource })
    .from(users)
    .where(eq(users.id, session.userId));

  if (!user?.customer) {
    redirect("/account?checkout=cancel");
  }

  const portalSession = await stripe.billingPortal.sessions.create({
    customer: user.customer,
    return_url: `${siteUrl}/account`,
  });

  redirect(portalSession.url);
}
