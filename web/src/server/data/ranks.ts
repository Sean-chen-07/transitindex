import "server-only";
import { eq, and } from "drizzle-orm";
import { db } from "@/server/db";
import { agencies, metricRanks, metrics, reportingPeriods } from "@/db/schema";
import { FREE_COMPARISON_SET, MIN_DENOMINATOR_ALL } from "./constants";
import { getAgencyBySlug } from "./agencies";
import type { AgencyRank, RankStatus } from "./types";

interface CohortPeriod {
  periodId: number;
  endDate: string;
  label: string;
}

// One agency's joined rank row (free cohort) — the input the reconciliation works on.
interface RankRow {
  metricId: number;
  periodId: number;
  rank: number | null;
  denominator: number | null;
  computedAt: Date | null;
  metricCode: string;
  metricDisplayName: string;
  unitType: string | null;
  higherIsBetter: boolean | null;
  periodLabel: string;
  periodEnd: string;
}

interface MetricMeta {
  id: number;
  code: string;
  displayName: string;
  unitType: string | null;
  higherIsBetter: boolean | null;
}

// The joined-row column shape, shared by the single-agency and all-agency queries.
const RANK_ROW_COLUMNS = {
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
} as const;

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

async function getMetricMeta(): Promise<Map<number, MetricMeta>> {
  const rows = await db
    .select({
      id: metrics.id,
      code: metrics.code,
      displayName: metrics.displayName,
      unitType: metrics.unitType,
      higherIsBetter: metrics.higherIsBetter,
    })
    .from(metrics);
  return new Map(rows.map((m) => [m.id, m]));
}

/**
 * Pure reconciliation: turn one agency's rank rows into the committed period-miss / N<5
 * states. Shared verbatim by `getAgencyRanks` (one agency) and `getAllAgencyRanks` (the
 * batch home read) so the two paths can never diverge on the rank-safety logic. This is
 * the PRIMARY N<5 guard (the rank job does not suppress small pools).
 */
function reconcileRanks(
  rows: RankRow[],
  latestByMetric: Map<number, CohortPeriod>,
  metaById: Map<number, MetricMeta>,
): AgencyRank[] {
  // Keep only the agency's row in the cohort-latest period, indexed by metric.
  const byMetric = new Map<number, RankRow>();
  for (const row of rows) {
    const cohort = latestByMetric.get(row.metricId);
    if (cohort && row.periodId === cohort.periodId) byMetric.set(row.metricId, row);
  }

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

/**
 * Free-safe ranks for one agency: ordinals from core.metric_ranks only, reconciled
 * against the cohort's latest period per metric. Returns [] when no ranks exist yet
 * (the seed-only DB) — the card/detail then shows "fundamentals pending".
 */
export async function getAgencyRanks(slug: string): Promise<AgencyRank[]> {
  const agency = await getAgencyBySlug(slug);
  if (!agency) return [];

  const latestByMetric = await getLatestRankedPeriodPerMetric();
  if (latestByMetric.size === 0) return [];

  const rows = await db
    .select(RANK_ROW_COLUMNS)
    .from(metricRanks)
    .innerJoin(metrics, eq(metricRanks.metricId, metrics.id))
    .innerJoin(reportingPeriods, eq(metricRanks.reportingPeriodId, reportingPeriods.id))
    .where(
      and(
        eq(metricRanks.agencyId, agency.id),
        eq(metricRanks.comparisonSet, FREE_COMPARISON_SET),
      ),
    );

  const metaById = await getMetricMeta();
  return reconcileRanks(rows, latestByMetric, metaById);
}

/**
 * Free-safe ranks for EVERY agency in one constant set of queries — the home directory
 * (now ~100+ agencies) reads ranks once here instead of N+1 per-agency calls. Output is
 * byte-for-byte the per-slug `getAgencyRanks` result (same reconciliation), so the rank
 * safety guarantees are identical. Returns {} on the seed-only DB.
 */
export async function getAllAgencyRanks(): Promise<Record<string, AgencyRank[]>> {
  const latestByMetric = await getLatestRankedPeriodPerMetric();
  if (latestByMetric.size === 0) return {};

  const idSlug = await db
    .select({ id: agencies.id, slug: agencies.slug })
    .from(agencies);

  const rows = await db
    .select({ agencyId: metricRanks.agencyId, ...RANK_ROW_COLUMNS })
    .from(metricRanks)
    .innerJoin(metrics, eq(metricRanks.metricId, metrics.id))
    .innerJoin(reportingPeriods, eq(metricRanks.reportingPeriodId, reportingPeriods.id))
    .where(eq(metricRanks.comparisonSet, FREE_COMPARISON_SET));

  const rowsByAgency = new Map<number, RankRow[]>();
  for (const { agencyId, ...row } of rows) {
    const list = rowsByAgency.get(agencyId) ?? [];
    list.push(row);
    rowsByAgency.set(agencyId, list);
  }

  const metaById = await getMetricMeta();
  const out: Record<string, AgencyRank[]> = {};
  for (const { id, slug } of idSlug) {
    out[slug] = reconcileRanks(rowsByAgency.get(id) ?? [], latestByMetric, metaById);
  }
  return out;
}
