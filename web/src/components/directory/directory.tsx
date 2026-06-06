"use client";

import * as React from "react";
import { Search } from "lucide-react";
import { AgencyRow } from "./agency-row";
import { EmptySearch } from "@/components/common/states";
import { provinceName } from "@/lib/format";
import type { AgencyListItem, AgencyRank } from "@/server/data/types";

/**
 * The free directory: a search hero + ONE unified, table-like list of every Canadian
 * agency (no per-province grids — province is a column/search term). Each agency is a
 * full-width row that expands in place to its ranks (wireframes-v5). Search filters the
 * ALREADY-SHIPPED, rank-only payload client-side — `ranksBySlug` carries ordinals only,
 * never a raw number. The agency names + links render in the server HTML (crawlable);
 * the client filter is progressive enhancement.
 */
export function Directory({
  agencies,
  ranksBySlug,
}: {
  agencies: AgencyListItem[];
  ranksBySlug: Record<string, AgencyRank[]>;
}) {
  const [q, setQ] = React.useState("");
  const query = q.trim().toLowerCase();

  const filtered = query
    ? agencies.filter(
        (a) =>
          a.legalName.toLowerCase().includes(query) ||
          (a.shortName?.toLowerCase().includes(query) ?? false) ||
          a.slug.includes(query) ||
          provinceName(a.subdivision).toLowerCase().includes(query),
      )
    : agencies;

  return (
    <div>
      <div className="relative mb-6">
        <Search
          aria-hidden
          className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-3"
        />
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search agencies or provinces…"
          aria-label="Search transit agencies"
          className="min-h-[44px] w-full rounded-full border border-line bg-card py-3 pl-12 pr-4 text-base text-ink shadow-soft placeholder:text-ink-3"
        />
      </div>

      {query && filtered.length === 0 ? (
        <EmptySearch query={q} />
      ) : (
        <div className="overflow-hidden rounded-card border border-line bg-card shadow-soft md:flex md:flex-col md:gap-3 md:overflow-visible md:rounded-none md:border-0 md:bg-transparent md:shadow-none">
          <div className="flex items-center gap-3 border-b border-line bg-card-2 px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide text-ink-3 md:hidden">
            <span className="flex-1">
              Agency
              <span className="ml-2 font-normal normal-case tracking-normal text-ink-3">
                · ranked vs all Canadian agencies
              </span>
            </span>
            <span className="hidden w-32 shrink-0 md:block">Province</span>
            <span className="hidden w-[152px] shrink-0 sm:block">Top ranks</span>
            <span className="w-5 shrink-0" aria-hidden />
          </div>

          {filtered.map((a) => (
            <AgencyRow key={a.slug} item={a} ranks={ranksBySlug[a.slug] ?? []} />
          ))}
        </div>
      )}
    </div>
  );
}
