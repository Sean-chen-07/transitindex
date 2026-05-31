import { listAgencies } from "@/server/data/agencies";
import { getAgencyRanks } from "@/server/data/ranks";
import { getFeedFreshness } from "@/server/data/freshness";
import { Directory } from "@/components/directory/directory";
import { FreshnessBanner } from "@/components/common/states";
import type { AgencyRank } from "@/server/data/types";

// Server-rendered each request (SEO-crawlable HTML, no per-user caching). The payload
// shipped to the client Directory is rank-only — never a raw number.
export const dynamic = "force-dynamic";

export default async function HomePage() {
  const groups = await listAgencies();
  const feeds = await getFeedFreshness();

  // Ranks per agency (ordinals only — safe to serialize to the client). 10 agencies;
  // each call short-circuits to [] until metric_ranks is populated.
  const ranksBySlug: Record<string, AgencyRank[]> = {};
  for (const g of groups) {
    for (const a of g.agencies) {
      ranksBySlug[a.slug] = await getAgencyRanks(a.slug);
    }
  }

  return (
    <main>
      <section className="mb-10 text-center">
        <h1 className="text-balance text-3xl font-extrabold leading-tight text-ink sm:text-4xl">
          Every Canadian transit agency, ranked on the fundamentals.
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-ink-2">
          Search an agency to see where it ranks. Ranks are free; the raw numbers are
          membership-only.
        </p>
        <div className="mt-3">
          <FreshnessBanner feeds={feeds} />
        </div>
      </section>
      <Directory groups={groups} ranksBySlug={ranksBySlug} />
    </main>
  );
}
