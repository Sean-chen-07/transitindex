import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getAgencySummary } from "@/server/data/agencies";
import { getAgencyRanks } from "@/server/data/ranks";
import { getAttribution } from "@/server/data/attribution";
import { getDetailMetrics } from "@/server/metrics/access";
import { getSession } from "@/server/entitlement";
import { RankGrid } from "@/components/directory/rank-grid";
import { GatedTable } from "@/components/detail/gated-metric";
import { Spreadsheet } from "@/components/detail/spreadsheet";
import { PendingNotice } from "@/components/common/states";
import { RequestAgencyForm } from "@/components/detail/request-agency-form";
import { SourceFootnote } from "@/components/common/source-footnote";
import type { FreeMetricView, PaidMetricView } from "@/server/metrics/types";

// force-dynamic: the cacheable render contains ONLY free shape; the reveal decision
// never influences a shared/cached output served to an anonymous hit.
export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const summary = await getAgencySummary(slug);
  if (!summary) return { title: "Agency not found" };
  // Rank/identity only — generateMetadata never emits a quantitative value.
  return {
    title: `${summary.shortName ?? summary.legalName} — transit fundamentals`,
    description: `${summary.legalName} (${summary.provinceName}): where it ranks among Canadian transit agencies. Ranks free; raw numbers membership-only.`,
  };
}

export default async function AgencyDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const summary = await getAgencySummary(slug);
  if (!summary) notFound();

  const session = await getSession();
  const [ranks, attributions, detail] = await Promise.all([
    getAgencyRanks(slug),
    getAttribution(slug),
    getDetailMetrics(slug, session),
  ]);

  return (
    <main>
      <nav className="mb-4 text-sm">
        <Link href="/" className="text-teal underline-offset-2 hover:underline">
          ← All agencies
        </Link>
      </nav>

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

      {ranks.length > 0 ? <RankGrid ranks={ranks} /> : <PendingNotice slug={slug} />}

      {detail.metrics.length > 0 &&
        (detail.reveal ? (
          <Spreadsheet metrics={detail.metrics as PaidMetricView[]} />
        ) : (
          <GatedTable
            metrics={detail.metrics as FreeMetricView[]}
            agencyId={summary.id}
          />
        ))}

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
