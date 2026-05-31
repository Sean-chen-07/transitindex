import "server-only";
import { eq } from "drizzle-orm";
import { db } from "@/server/db";
import { sourceDocuments } from "@/db/schema";
import { getAgencyBySlug } from "./agencies";
import type { Attribution } from "./types";

/**
 * Source attribution for an agency (shown on BOTH tiers — license compliance,
 * invariant #8). Free-safe: source title / url / license / dates only. Page-level
 * provenance (metric_value_sources) is paid and lives behind the choke point.
 * Empty at the seed-only DB (source_documents is written at ingest promote time).
 */
export async function getAttribution(slug: string): Promise<Attribution[]> {
  const agency = await getAgencyBySlug(slug);
  if (!agency) return [];

  const rows = await db
    .select({
      title: sourceDocuments.title,
      sourceUrl: sourceDocuments.sourceUrl,
      license: sourceDocuments.license,
      publicationDate: sourceDocuments.publicationDate,
      retrievedAt: sourceDocuments.retrievedAt,
    })
    .from(sourceDocuments)
    .where(eq(sourceDocuments.agencyId, agency.id));

  return rows.map((r) => ({
    title: r.title,
    sourceUrl: r.sourceUrl,
    license: r.license,
    publicationDate: r.publicationDate,
    retrievedAt: r.retrievedAt ? r.retrievedAt.toISOString() : null,
  }));
}
