import "server-only";
import { eq, asc } from "drizzle-orm";
import { db } from "@/server/db";
import { agencies, agencyModes, modes, metricRanks } from "@/db/schema";
import { provinceName } from "@/lib/format";
import type { AgencyListGroup, AgencyListItem, AgencySummary } from "./types";

/**
 * All agencies grouped by province (full name), each flagged with whether it has any
 * rank yet. Free-safe: reads only core.agencies (+ a distinct agency_id list from
 * metric_ranks). At the seed-only DB this returns all 10 agencies with hasAnyRank=false.
 */
export async function listAgencies(): Promise<AgencyListGroup[]> {
  const rows = await db
    .select({
      slug: agencies.slug,
      shortName: agencies.shortName,
      legalName: agencies.legalName,
      subdivision: agencies.subdivision,
      primaryModes: agencies.primaryModes,
    })
    .from(agencies)
    .orderBy(asc(agencies.subdivision), asc(agencies.legalName));

  const ranked = await db
    .selectDistinct({ agencyId: metricRanks.agencyId })
    .from(metricRanks);
  // metric_ranks keys on agency_id; map to slugs via a second lookup is overkill —
  // instead flag by agency id resolved alongside. Re-query ids cheaply:
  const idBySlug = await db
    .select({ id: agencies.id, slug: agencies.slug })
    .from(agencies);
  const slugById = new Map(idBySlug.map((r) => [r.id, r.slug]));
  const rankedSlugs = new Set(
    ranked.map((r) => slugById.get(r.agencyId)).filter(Boolean) as string[],
  );

  const byProvince = new Map<string, AgencyListItem[]>();
  for (const r of rows) {
    const item: AgencyListItem = {
      slug: r.slug,
      shortName: r.shortName,
      legalName: r.legalName,
      subdivision: r.subdivision,
      primaryModes: r.primaryModes ?? [],
      hasAnyRank: rankedSlugs.has(r.slug),
    };
    const list = byProvince.get(r.subdivision) ?? [];
    list.push(item);
    byProvince.set(r.subdivision, list);
  }

  return [...byProvince.entries()]
    .map(([subdivision, list]) => ({
      subdivision,
      provinceName: provinceName(subdivision),
      agencies: list,
    }))
    .sort((a, b) => a.provinceName.localeCompare(b.provinceName));
}

/**
 * All agencies as ONE flat list, sorted by display name — the source for the unified
 * directory table (no province grouping). Free-safe: identity + modes + a hasAnyRank
 * flag only, never a raw value. At the seed-only DB every agency has hasAnyRank=false.
 */
export async function listAllAgencies(): Promise<AgencyListItem[]> {
  const rows = await db
    .select({
      id: agencies.id,
      slug: agencies.slug,
      shortName: agencies.shortName,
      legalName: agencies.legalName,
      subdivision: agencies.subdivision,
      primaryModes: agencies.primaryModes,
    })
    .from(agencies);

  const ranked = await db
    .selectDistinct({ agencyId: metricRanks.agencyId })
    .from(metricRanks);
  const rankedIds = new Set(ranked.map((r) => r.agencyId));

  return rows
    .map((r) => ({
      slug: r.slug,
      shortName: r.shortName,
      legalName: r.legalName,
      subdivision: r.subdivision,
      primaryModes: r.primaryModes ?? [],
      hasAnyRank: rankedIds.has(r.id),
    }))
    .sort((a, b) =>
      (a.shortName ?? a.legalName).localeCompare(b.shortName ?? b.legalName),
    );
}

export async function getAgencyBySlug(slug: string) {
  const [row] = await db
    .select({
      id: agencies.id,
      slug: agencies.slug,
      shortName: agencies.shortName,
      legalName: agencies.legalName,
      subdivision: agencies.subdivision,
      primaryModes: agencies.primaryModes,
    })
    .from(agencies)
    .where(eq(agencies.slug, slug))
    .limit(1);
  return row ?? null;
}

/** Identity + modes for an agency detail page header. Free-safe. */
export async function getAgencySummary(slug: string): Promise<AgencySummary | null> {
  const agency = await getAgencyBySlug(slug);
  if (!agency) return null;

  const modeRows = await db
    .select({ code: modes.code, displayName: modes.displayName })
    .from(agencyModes)
    .innerJoin(modes, eq(agencyModes.modeId, modes.id))
    .where(eq(agencyModes.agencyId, agency.id))
    .orderBy(asc(modes.displayName));

  return {
    id: agency.id,
    slug: agency.slug,
    shortName: agency.shortName,
    legalName: agency.legalName,
    subdivision: agency.subdivision,
    provinceName: provinceName(agency.subdivision),
    primaryModes: agency.primaryModes ?? [],
    modes: modeRows,
  };
}
