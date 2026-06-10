import "server-only";
import { and, eq, asc, isNull } from "drizzle-orm";
import { db } from "@/server/db";
import { metricValues, metrics, reportingPeriods, metricRanks } from "@/db/schema";
import { getAgencyBySlug } from "@/server/data/agencies";
import { getLatestRankedPeriodPerMetric } from "@/server/data/ranks";
import { FREE_COMPARISON_SET } from "@/server/data/constants";
import type { RawMetricSeries } from "./transform";

/**
 * THE ONLY module permitted to read the raw value-bearing table (core.metric_values).
 * Guarded by the ESLint no-restricted-imports rule: nothing but access.ts may import
 * this module, so every value read stays on one audited path.
 *
 * One entry per metric: the is_current=true, system-wide (mode_id IS NULL) rows across
 * all periods ARE the series, ordered chronologically. Per-mode rows are a future
 * surface. At the seed-only DB there are no metric_values, so this returns [] and the
 * detail page renders "fundamentals pending".
 */
export async function getRawMetricSeries(slug: string): Promise<RawMetricSeries[]> {
  const agency = await getAgencyBySlug(slug);
  if (!agency) return [];

  const rows = await db
    .select({
      metricId: metricValues.metricId,
      metricCode: metrics.code,
      displayName: metrics.displayName,
      unit: metricValues.unit,
      higherIsBetter: metrics.higherIsBetter,
      serviceScope: metricValues.serviceScope,
      value: metricValues.value,
      currency: metricValues.currency,
      periodId: metricValues.reportingPeriodId,
      periodType: reportingPeriods.periodType,
      periodLabel: reportingPeriods.label,
      endDate: reportingPeriods.endDate,
    })
    .from(metricValues)
    .innerJoin(metrics, eq(metricValues.metricId, metrics.id))
    .innerJoin(reportingPeriods, eq(metricValues.reportingPeriodId, reportingPeriods.id))
    .where(
      and(
        eq(metricValues.agencyId, agency.id),
        eq(metricValues.isCurrent, true),
        isNull(metricValues.modeId),
      ),
    )
    .orderBy(asc(reportingPeriods.endDate));
  if (rows.length === 0) return [];

  // Free-cohort ranks for the agency, indexed by metric+period.
  const ranks = await db
    .select({
      metricId: metricRanks.metricId,
      periodId: metricRanks.reportingPeriodId,
      rank: metricRanks.rank,
      denominator: metricRanks.denominator,
    })
    .from(metricRanks)
    .where(
      and(
        eq(metricRanks.agencyId, agency.id),
        eq(metricRanks.comparisonSet, FREE_COMPARISON_SET),
      ),
    );
  const rankByKey = new Map<string, { rank: number | null; denominator: number | null }>();
  for (const r of ranks) rankByKey.set(`${r.metricId}:${r.periodId}`, { rank: r.rank, denominator: r.denominator });

  const latestByMetric = await getLatestRankedPeriodPerMetric();

  // Group the chronologically-ordered rows per metric.
  const byMetric = new Map<number, typeof rows>();
  for (const row of rows) {
    const list = byMetric.get(row.metricId) ?? [];
    list.push(row);
    byMetric.set(row.metricId, list);
  }

  const out: RawMetricSeries[] = [];
  for (const [metricId, metricRows] of byMetric) {
    // Scope preference: 'total' when present, else the lexically-first scope (deterministic).
    const scopes = [...new Set(metricRows.map((r) => r.serviceScope))];
    const scope = scopes.includes("total") ? "total" : scopes.reduce((a, b) => (a < b ? a : b));
    const kept = metricRows.filter((r) => r.serviceScope === scope);
    const head = kept[0];
    if (!head) continue; // unreachable: scope comes from the rows themselves
    const latest = kept[kept.length - 1] ?? head;

    const cohort = latestByMetric.get(metricId);
    const rankInfo = cohort ? rankByKey.get(`${metricId}:${cohort.periodId}`) : undefined;
    const points = kept.map((r) => ({
      periodId: r.periodId,
      periodType: r.periodType,
      periodLabel: r.periodLabel,
      endDate: r.endDate,
      value: Number(r.value), // drizzle numeric comes back as a string
    }));

    out.push({
      metricCode: head.metricCode,
      displayName: head.displayName,
      unit: latest.unit,
      higherIsBetter: head.higherIsBetter,
      serviceScope: scope,
      currency: latest.currency,
      rank: rankInfo?.rank ?? null,
      denominator: rankInfo?.denominator ?? null,
      hasComparablePeriod: cohort ? points.some((p) => p.periodId === cohort.periodId) : false,
      points,
    });
  }
  return out;
}
