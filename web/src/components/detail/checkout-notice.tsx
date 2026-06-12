// Acknowledgment of a Stripe checkout return on the agency detail page. Pure markup
// (server-safe), tokens match the account page success/cancel banners and states.tsx.
// The detail download lives behind the Financials tab, so the user who just paid lands
// on Highlights and needs this top banner to see ANY acknowledgment.

// Shared copy: the webhook-lag message appears both at the top (banner) and in the
// download slot (replacing the stale Subscribe button), so keep it in one place.
const ACTIVATING =
  "Payment received — activating your membership. Refresh in a few seconds.";

export type CheckoutState = "success-active" | "success-pending" | "cancel";

/** Resolve the ?checkout= param + live entitlement into a banner state, or null. */
export function checkoutStateFrom(
  checkout: string | undefined,
  subscribed: boolean,
): CheckoutState | null {
  if (checkout === "success") return subscribed ? "success-active" : "success-pending";
  if (checkout === "cancel") return "cancel";
  return null;
}

export function CheckoutBanner({ state }: { state: CheckoutState }) {
  if (state === "success-active") {
    return (
      <div
        className="mb-6 rounded-card border border-teal/40 bg-teal-soft p-4 text-sm text-ink"
        role="status"
      >
        You&apos;re a member — the CSV download is unlocked below.
      </div>
    );
  }
  const text = state === "success-pending" ? ACTIVATING : "No charge was made. You can subscribe whenever you're ready.";
  return (
    <div
      className="mb-6 rounded-card border border-line bg-card-2 p-4 text-sm text-ink-2"
      role="status"
    >
      {text}
    </div>
  );
}

/** Download-slot replacement for the Subscribe button while a just-paid membership
 * is still activating (webhook lag) — shows the same message, no stale CTA. */
export function PendingActivationNotice() {
  return (
    <div
      className="rounded-card border border-line bg-card-2 p-4 text-sm text-ink-2"
      role="status"
    >
      {ACTIVATING}
    </div>
  );
}
