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

  // Keep the latest run per feed (by finishedAt; nulls treated as oldest).
  const latest = new Map<string, FeedFreshness>();
  for (const r of rows) {
    if (!r.enabled) continue;
    const prev = latest.get(r.code);
    const ts = r.finishedAt ? r.finishedAt.getTime() : -1;
    const prevTs = prev?.lastGoodAt ? new Date(prev.lastGoodAt).getTime() : -1;
    if (!prev || ts > prevTs) {
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
