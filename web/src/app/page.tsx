import { listAllAgencies } from "@/server/data/agencies";
import { getAllAgencyRanks } from "@/server/data/ranks";
import { getFeedFreshness } from "@/server/data/freshness";
import { getDirectoryCardValues } from "@/server/metrics/access";
import { Directory } from "@/components/directory/directory";
import { FreshnessBanner } from "@/components/common/states";

// Server-rendered each request (SEO-crawlable HTML, no per-user caching). Since
// 2026-08-05 the payload carries FIGURES as well as ordinals — viewing is free by
// decision, so there is nothing here that an anonymous user may not see.
export const dynamic = "force-dynamic";

export default async function HomePage() {
  // One flat list of every agency + batched rank and value reads. All constant-query —
  // no N+1 across the full directory.
  const [agencies, ranksBySlug, valuesBySlug, feeds] = await Promise.all([
    listAllAgencies(),
    getAllAgencyRanks(),
    getDirectoryCardValues(),
    getFeedFreshness(),
  ]);

  return (
    <main>
      <section className="mb-10 text-center">
        <h1 className="text-balance text-3xl font-extrabold leading-tight text-ink sm:text-4xl">
          Every Canadian and U.S. transit agency, ranked on the fundamentals.
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-ink-2">
          Search an agency to see where it ranks — every rank and every number is free to
          view.
        </p>
        <div className="mt-3">
          <FreshnessBanner feeds={feeds} />
        </div>
      </section>
      <Directory
        agencies={agencies}
        ranksBySlug={ranksBySlug}
        valuesBySlug={valuesBySlug}
      />
    </main>
  );
}
