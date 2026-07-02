import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAgencySummary } from "@/server/data/agencies";
import { getAttribution } from "@/server/data/attribution";
import { getDetailMetrics, getFleetComposition } from "@/server/metrics/access";
import { buildDetailModel } from "@/server/metrics/detail-model";
import { getSession, isPaid } from "@/server/entitlement";
import { PendingNotice } from "@/components/common/states";
import { DetailTabs } from "@/components/detail/detail-tabs";
import { HeroGrid } from "@/components/detail/hero-grid";
import { ValueTables } from "@/components/detail/value-tables";
import { Financials } from "@/components/detail/financials";
import { DownloadButton } from "@/components/detail/download-button";
import { CheckoutBanner, checkoutStateFrom } from "@/components/detail/checkout-notice";
import { RequestAgencyForm } from "@/components/detail/request-agency-form";
import { SourceFootnote } from "@/components/common/source-footnote";

// force-dynamic: detail data is read live per request, and the paid download
// entitlement (the only gate left) must never be inferred from a shared cache.
export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const summary = await getAgencySummary(slug);
  if (!summary) return { title: "Agency not found" };
  return {
    title: `${summary.shortName ?? summary.legalName} — transit fundamentals`,
    description: `${summary.legalName} (${summary.provinceName}): ridership, costs, and financial fundamentals for Canadian transit agencies — every number free to view.`,
  };
}

export default async function AgencyDetailPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ checkout?: string }>;
}) {
  const { slug } = await params;
  const summary = await getAgencySummary(slug);
  if (!summary) notFound();

  const [attributions, metrics, fleetComposition, session, { checkout }] = await Promise.all([
    getAttribution(slug),
    getDetailMetrics(slug),
    getFleetComposition(slug),
    getSession(),
    searchParams,
  ]);
  const model = buildDetailModel(metrics, fleetComposition);
  // Presentation only — the download route re-checks the live session + isPaid itself.
  const subscribed = await isPaid(session);
  // Acknowledge a Stripe checkout return. On success the webhook may lag, so a just-paid
  // user can be back here before subscription_status flips — show "activating" instead of
  // a stale Subscribe button (both top banner and download slot).
  const checkoutState = checkoutStateFrom(checkout, subscribed);
  const pendingActivation = checkoutState === "success-pending";

  return (
    <main>
      <nav className="mb-4 text-sm">
        <Link href="/" className="text-teal underline-offset-2 hover:underline">
          ← All agencies
        </Link>
      </nav>

      {checkoutState && <CheckoutBanner state={checkoutState} />}

      <header className="mb-6">
        <h1 className="text-3xl font-extrabold text-ink">
          {summary.shortName ?? summary.legalName}
        </h1>
        <p className="mt-1 text-ink-2">
          {summary.shortName && summary.shortName !== summary.legalName
            ? `${summary.legalName} · ${summary.provinceName}`
            : summary.provinceName}
        </p>
        <div className="mt-2 flex flex-wrap gap-1">
          {summary.modes.map((m) => (
            <span
              key={m.code}
              className="rounded-full border border-line-2 bg-card-2 px-2 py-0.5 text-xs text-ink-2"
            >
              {m.displayName}
            </span>
          ))}
        </div>
      </header>

      {metrics.length === 0 ? (
        <PendingNotice slug={slug} />
      ) : (
        <DetailTabs
          highlights={
            <>
              <HeroGrid heroes={model.heroes} />
              <ValueTables
                ratios={model.ratios}
                serviceFleet={model.serviceFleet}
                fleetComposition={model.fleetComposition}
              />
            </>
          }
          financials={
            <Financials
              financials={model.financials}
              downloadSlot={
                <DownloadButton
                  subscribed={subscribed}
                  slug={slug}
                  agencyId={summary.id}
                  pendingActivation={pendingActivation}
                />
              }
            />
          }
        />
      )}

      <section className="mt-10 rounded-card border border-line bg-card-2 p-5">
        <h2 className="text-sm font-semibold text-ink">Missing something?</h2>
        <p className="mb-3 mt-1 text-sm text-ink-2">
          Tell us to prioritize sourcing {summary.shortName ?? summary.legalName}.
        </p>
        <RequestAgencyForm agencyId={summary.id} />
      </section>

      <SourceFootnote attributions={attributions} />
    </main>
  );
}
