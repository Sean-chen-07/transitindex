"use client";

import * as React from "react";
import { Search } from "lucide-react";
import { AgencyCard } from "./agency-card";
import { AgencyListRow } from "./agency-list-row";
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
        <div>
          <p className="mb-3 text-xs text-ink-3">
            {filtered.length} agencies · ranked vs all Canadian agencies
          </p>
          {/* Phones: one compact, dense list. */}
          <div className="divide-y divide-line-2 overflow-hidden rounded-card border border-line bg-card shadow-soft sm:hidden">
            {filtered.map((a) => (
              <AgencyListRow key={a.slug} item={a} ranks={ranksBySlug[a.slug] ?? []} />
            ))}
          </div>
          {/* sm and up: grid of mini-page cards. 3-up at lg (matches the max-w-5xl container). */}
          <div className="hidden gap-4 sm:grid sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((a) => (
              <AgencyCard key={a.slug} item={a} ranks={ranksBySlug[a.slug] ?? []} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
