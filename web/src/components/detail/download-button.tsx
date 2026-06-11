import { Download } from "lucide-react";
import { SubscribeDialog } from "./subscribe-dialog";

/**
 * The download slot on the Financials header. `subscribed` is decided server-side in
 * the page (live getSession + isPaid) and is PRESENTATION ONLY — the real money gate is
 * /api/agency/[slug]/download, which re-checks the session + isPaid on every request.
 */
export function DownloadButton({
  subscribed,
  slug,
  agencyId,
}: {
  subscribed: boolean;
  slug: string;
  agencyId?: number | null;
}) {
  if (!subscribed) return <SubscribeDialog returnTo={`/agency/${slug}`} agencyId={agencyId} />;
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
