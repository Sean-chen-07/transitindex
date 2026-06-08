import "server-only";
import { eq } from "drizzle-orm";
import { db } from "@/server/db";
import { sourceFeeds, feedRuns } from "@/db/schema";
import type { FeedFreshness } from "./types";

/**
 * Per-feed freshness for the global banner / stale "as of" treatment. Reduces to the
 * latest run per feed. Tolerates ZERO feed_runs (the seed-only DB): a feed with no run
 * yet reports status=null / lastGoodAt=null, which the UI renders as a neutral
 * "Data being sourced" — never "Invalid Date".
 */
export async function getFeedFreshness(): Promise<FeedFreshness[]> {
  const rows = await db
    .select({
      code: sourceFeeds.code,
      displayName: sourceFeeds.displayName,
      expectedCadence: sourceFeeds.expectedCadence,
      enabled: sourceFeeds.enabled,
      status: feedRuns.status,
      lastGoodAt: feedRuns.lastGoodAt,
      finishedAt: feedRuns.finishedAt,
    })
    .from(sourceFeeds)
    .leftJoin(feedRuns, eq(feedRuns.feedId, sourceFeeds.id));

  return reduceLatestFreshness(rows);
}

/** One row of the source_feeds ⟕ feed_runs join (feed_runs columns are nullable). */
export interface FeedRunRow {
  code: string;
  displayName: string;
  expectedCadence: string | null;
  enabled: boolean;
  status: string | null;
  lastGoodAt: Date | null;
  finishedAt: Date | null;
}

/**
 * Keep the latest run per feed by finishedAt (nulls treated as oldest), then sort by name.
 * Compares each candidate's finishedAt against the KEPT run's own finishedAt — not against a
 * different column — so the newest run wins regardless of success/failure. (The previous code
 * compared finishedAt against the kept run's lastGoodAt; since the ingester never sets
 * lastGoodAt, that collapsed to "keep whichever row came last".)
 */
export function reduceLatestFreshness(rows: FeedRunRow[]): FeedFreshness[] {
  const latest = new Map<string, FeedFreshness>();
  const bestFinishedAt = new Map<string, number>();
  for (const r of rows) {
    if (!r.enabled) continue;
    const ts = r.finishedAt ? r.finishedAt.getTime() : -1;
    const prevTs = bestFinishedAt.get(r.code) ?? -1;
    if (!latest.has(r.code) || ts > prevTs) {
      bestFinishedAt.set(r.code, ts);
      latest.set(r.code, {
        code: r.code,
        displayName: r.displayName,
        status: r.status,
        lastGoodAt: r.lastGoodAt ? r.lastGoodAt.toISOString() : null,
        expectedCadence: r.expectedCadence,
      });
    }
  }
  return [...latest.values()].sort((a, b) => a.displayName.localeCompare(b.displayName));
}
