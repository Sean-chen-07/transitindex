import type Stripe from "stripe";
import { eq } from "drizzle-orm";
import { db } from "@/server/db";
import { users } from "@/db/schema";
import { stripe } from "@/lib/stripe";
import { recordPaidConversionOnce } from "@/server/billing/conversions";

// Node runtime: the Edge runtime can't give us the exact raw bytes Stripe signed, and the
// SDK's signature verification needs the unparsed body.
export const runtime = "nodejs";

// THE ONLY writer of app.users.subscription_status anywhere in the app. Map a Stripe
// subscription status onto our CHECK domain ('active'|'inactive'|'trialing'|'past_due').
// ANY status we don't explicitly handle (paused, incomplete, unknown future values) →
// 'inactive': a safe default that the CHECK always accepts, so a surprise status can never
// make the UPDATE throw and trigger a Stripe webhook retry storm.
function mapStatus(status: Stripe.Subscription.Status): string {
  switch (status) {
    case "active":
    case "trialing":
      // Locked status map: a Stripe trial counts as a paid membership ('active'), so
      // isPaid() and the /account page agree on a single definition of "entitled".
      return "active";
    case "past_due":
      return "past_due";
    default:
      // canceled | unpaid | incomplete | incomplete_expired | paused | anything new
      return "inactive";
  }
}

export async function POST(req: Request): Promise<Response> {
  const body = await req.text();
  const sig = req.headers.get("stripe-signature");
  const secret = process.env.STRIPE_WEBHOOK_SECRET;

  let event: Stripe.Event;
  try {
    if (!sig || !secret) throw new Error("missing signature or webhook secret");
    event = stripe.webhooks.constructEvent(body, sig, secret);
  } catch {
    // Bad/missing signature, or the body didn't match — reject so Stripe doesn't treat it
    // as delivered. We deliberately don't echo the reason.
    return new Response("invalid signature", { status: 400 });
  }

  switch (event.type) {
    case "checkout.session.completed": {
      const checkout = event.data.object;
      // Only our $20/yr membership flow — ignore any other future checkout on this account.
      if (checkout.mode !== "subscription") break;
      const userId = Number(checkout.client_reference_id);
      const customer =
        typeof checkout.customer === "string" ? checkout.customer : checkout.customer?.id;
      if (Number.isFinite(userId) && customer) {
        // For mode:subscription, this event fires even when the subscription is still
        // `incomplete`/unpaid (SCA/3DS pending or card declined). So we NEVER grant access
        // on this event alone: we record the Stripe customer id (so the billing portal and
        // the customer.subscription.* events can reconcile) and only set 'active' when the
        // session is genuinely paid. customer.subscription.* is the real source of truth.
        const paid =
          checkout.payment_status === "paid" ||
          checkout.payment_status === "no_payment_required";
        await db
          .update(users)
          .set({
            subscriptionSource: customer,
            ...(paid ? { subscriptionStatus: "active" } : {}),
          })
          .where(eq(users.id, userId));
        // Idempotent on redelivery (Stripe re-sends events); see recordPaidConversionOnce.
        if (paid) await recordPaidConversionOnce(userId);
      }
      break;
    }

    case "customer.subscription.created":
    case "customer.subscription.updated":
    case "customer.subscription.deleted": {
      const subscription = event.data.object;
      const customer =
        typeof subscription.customer === "string"
          ? subscription.customer
          : subscription.customer.id;
      const status = mapStatus(subscription.status);
      // Prefer the bigint userId we stamped on the subscription at checkout: this is robust
      // to event ordering (no dependency on checkout.session.completed landing first). Fall
      // back to the stored Stripe customer id if the metadata is somehow absent.
      const metaUserId = Number(subscription.metadata?.userId);
      if (Number.isFinite(metaUserId)) {
        await db
          .update(users)
          .set({ subscriptionStatus: status, subscriptionSource: customer })
          .where(eq(users.id, metaUserId));
      } else {
        await db
          .update(users)
          .set({ subscriptionStatus: status })
          .where(eq(users.subscriptionSource, customer));
      }
      break;
    }

    default:
      // Acknowledge every other event type so Stripe stops retrying it.
      break;
  }

  return Response.json({ received: true });
}
