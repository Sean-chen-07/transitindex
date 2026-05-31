"use client";

import * as React from "react";
import { Search } from "lucide-react";
import { AgencyCard } from "./agency-card";
import { EmptySearch } from "@/components/common/states";
import type { AgencyListGroup, AgencyRank } from "@/server/data/types";

/**
 * The free directory: a search hero + province-grouped expandable cards. Search filters
 * the ALREADY-SHIPPED, rank-only payload client-side (no raw numbers are ever sent —
 * `ranksBySlug` carries ordinals only). Province groups stay crawlable in the initial
 * server HTML; the client filter is progressive enhancement.
 */
export function Directory({
  groups,
  ranksBySlug,
}: {
  groups: AgencyListGroup[];
  ranksBySlug: Record<string, AgencyRank[]>;
}) {
  const [q, setQ] = React.useState("");
  const query = q.trim().toLowerCase();

  const filtered = groups
    .map((g) => ({
      ...g,
      agencies: g.agencies.filter(
        (a) =>
          !query ||
          a.legalName.toLowerCase().includes(query) ||
          (a.shortName?.toLowerCase().includes(query) ?? false) ||
          a.slug.includes(query),
      ),
    }))
    .filter((g) => g.agencies.length > 0);

  const empty = query.length > 0 && filtered.length === 0;

  return (
    <div>
      <div className="relative mb-8">
        <Search
          aria-hidden
          className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-3"
        />
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search agencies…"
          aria-label="Search transit agencies"
          className="min-h-[44px] w-full rounded-full border border-line bg-card py-3 pl-12 pr-4 text-base text-ink shadow-soft placeholder:text-ink-3"
        />
      </div>

      {empty ? (
        <EmptySearch query={q} />
      ) : (
        <div className="space-y-10">
          {filtered.map((g) => (
            <section key={g.subdivision} aria-labelledby={`prov-${g.subdivision}`}>
              <h2
                id={`prov-${g.subdivision}`}
                className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-2"
              >
                {g.provinceName}
              </h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                {g.agencies.map((a) => (
                  <AgencyCard key={a.slug} item={a} ranks={ranksBySlug[a.slug] ?? []} />
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
