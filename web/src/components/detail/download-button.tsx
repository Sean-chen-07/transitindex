import { Download } from "lucide-react";
import { SubscribeDialog } from "./subscribe-dialog";
import { PendingActivationNotice } from "./checkout-notice";

/**
 * The download slot on the Financials header. `subscribed` is decided server-side in
 * the page (live getSession + isPaid) and is PRESENTATION ONLY — the real money gate is
 * /api/agency/[slug]/download, which re-checks the session + isPaid on every request.
 *
 * `pendingActivation` is true only right after a checkout=success return when the webhook
 * hasn't flipped subscription_status yet; in that window we show an "activating" notice
 * instead of the Subscribe button so a just-paid user isn't asked to pay again.
 */
export function DownloadButton({
  subscribed,
  slug,
  agencyId,
  pendingActivation = false,
}: {
  subscribed: boolean;
  slug: string;
  agencyId?: number | null;
  pendingActivation?: boolean;
}) {
  if (!subscribed) {
    if (pendingActivation) return <PendingActivationNotice />;
    return <SubscribeDialog returnTo={`/agency/${slug}`} agencyId={agencyId} />;
  }
  return (
    <a
      href={`/api/agency/${slug}/download`}
      className="inline-flex min-h-[44px] items-center gap-2 rounded-full bg-coral px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-coral/90"
    >
      <Download aria-hidden className="h-4 w-4" />
      Download CSV
    </a>
  );
}
