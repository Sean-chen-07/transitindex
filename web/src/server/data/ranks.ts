import "server-only";
import { eq, and } from "drizzle-orm";
import { db } from "@/server/db";
import { metricRanks, metrics, reportingPeriods } from "@/db/schema";
import { FREE_COMPARISON_SET, MIN_DENOMINATOR_ALL } from "./constants";
import { getAgencyBySlug } from "./agencies";
import type { AgencyRank, RankStatus } from "./types";

interface CohortPeriod {
  periodId: number;
  endDate: string;
  label: string;
}

/**
 * Per metric, the LATEST period (by end_date) that has any rank row in the free
 * cohort (comparison_set='all'). This is the cohort-latest fact used to detect a
 * period miss: an agency lacking a row in this period is "not ranked — latest <label>",
 * never silently dropped and never ranked across years.
 */
export async function getLatestRankedPeriodPerMetric(): Promise<Map<number, CohortPeriod>> {
  const rows = await db
    .select({
      metricId: metricRanks.metricId,
      periodId: metricRanks.reportingPeriodId,
      endDate: reportingPeriods.endDate,
      label: reportingPeriods.label,
    })
    .from(metricRanks)
    .innerJoin(reportingPeriods, eq(metricRanks.reportingPeriodId, reportingPeriods.id))
    .where(eq(metricRanks.comparisonSet, FREE_COMPARISON_SET));

  const latest = new Map<number, CohortPeriod>();
  for (const r of rows) {
    const cur = latest.get(r.metricId);
    if (!cur || r.endDate > cur.endDate) {
      latest.set(r.metricId, { periodId: r.periodId, endDate: r.endDate, label: r.label });
    }
  }
  return latest;
}

/**
 * Free-safe ranks for an agency: ordinals from core.metric_ranks only, reconciled
 * against the cohort's latest period per metric. Returns [] when no ranks exist yet
 * (the seed-only DB) — the card/detail then shows "fundamentals pending".
 */
export async function getAgencyRanks(slug: string): Promise<AgencyRank[]> {
  const agency = await getAgencyBySlug(slug);
  if (!agency) return [];

  const latestByMetric = await getLatestRankedPeriodPerMetric();
  if (latestByMetric.size === 0) return [];

  // The agency's own rank rows (free cohort), with metric + period metadata.
  const agencyRows = await db
    .select({
      metricId: metricRanks.metricId,
      periodId: metricRanks.reportingPeriodId,
      rank: metricRanks.rank,
      denominator: metricRanks.denominator,
      computedAt: metricRanks.computedAt,
      metricCode: metrics.code,
      metricDisplayName: metrics.displayName,
      unitType: metrics.unitType,
      higherIsBetter: metrics.higherIsBetter,
      periodLabel: reportingPeriods.label,
      periodEnd: reportingPeriods.endDate,
    })
    .from(metricRanks)
    .innerJoin(metrics, eq(metricRanks.metricId, metrics.id))
    .innerJoin(reportingPeriods, eq(metricRanks.reportingPeriodId, reportingPeriods.id))
    .where(
      and(
        eq(metricRanks.agencyId, agency.id),
        eq(metricRanks.comparisonSet, FREE_COMPARISON_SET),
      ),
    );

  // Index the agency's rows by metric, keeping the row in the cohort-latest period.
  const byMetric = new Map<number, (typeof agencyRows)[number]>();
  for (const row of agencyRows) {
    const cohort = latestByMetric.get(row.metricId);
    if (cohort && row.periodId === cohort.periodId) byMetric.set(row.metricId, row);
  }

  // Metric metadata for period-miss rows (agency has no row in the latest period).
  const metricMeta = await db
    .select({
      id: metrics.id,
      code: metrics.code,
      displayName: metrics.displayName,
      unitType: metrics.unitType,
      higherIsBetter: metrics.higherIsBetter,
    })
    .from(metrics);
  const metaById = new Map(metricMeta.map((m) => [m.id, m]));

  const result: AgencyRank[] = [];
  for (const [metricId, cohort] of latestByMetric) {
    const have = byMetric.get(metricId);
    const meta = metaById.get(metricId);
    if (have) {
      const denominator = have.denominator;
      const rank = have.rank;
      const suppressed =
        rank == null ||
        denominator == null ||
        denominator < MIN_DENOMINATOR_ALL ||
        rank < 1 ||
        rank > denominator;
      result.push({
        metricCode: have.metricCode,
        metricDisplayName: have.metricDisplayName,
        unitType: have.unitType,
        higherIsBetter: have.higherIsBetter,
        comparisonSet: "all",
        status: (suppressed ? "not_yet_ranked" : "ranked") as RankStatus,
        rank,
        denominator,
        periodLabel: have.periodLabel,
        periodEnd: have.periodEnd,
        computedAt: have.computedAt?.toISOString() ?? null,
      });
    } else if (meta) {
      // Cohort has a latest period for this metric, but the agency is missing from it.
      result.push({
        metricCode: meta.code,
        metricDisplayName: meta.displayName,
        unitType: meta.unitType,
        higherIsBetter: meta.higherIsBetter,
        comparisonSet: "all",
        status: "not_ranked_period_miss",
        rank: null,
        denominator: null,
        periodLabel: cohort.label,
        periodEnd: cohort.endDate,
        computedAt: null,
      });
    }
  }

  return result.sort((a, b) => a.metricDisplayName.localeCompare(b.metricDisplayName));
}
