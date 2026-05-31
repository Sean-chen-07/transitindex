import "server-only";
import { and, eq, asc, inArray } from "drizzle-orm";
import { db } from "@/server/db";
import {
  metricValues,
  metrics,
  reportingPeriods,
  metricValueSources,
  sourceDocuments,
  metricRanks,
} from "@/db/schema";
import { getAgencyBySlug } from "@/server/data/agencies";
import { getLatestRankedPeriodPerMetric } from "@/server/data/ranks";
import { FREE_COMPARISON_SET } from "@/server/data/constants";
import type { RawMetricRow } from "./transform";
import type { MetricProvenance } from "./types";

/**
 * THE ONLY module permitted to read raw value-bearing tables (metric_values,
 * metric_value_sources). Guarded by the ESLint no-restricted-imports rule: nothing
 * but access.ts may import this module. It returns raw rows; the choke point decides
 * whether they become a Free (value-stripped) or Paid view.
 *
 * At the seed-only DB there are no metric_values, so this returns [] and every detail
 * page renders "fundamentals pending".
 */
export async function getRawMetricSeries(slug: string): Promise<RawMetricRow[]> {
  const agency = await getAgencyBySlug(slug);
  if (!agency) return [];

  const currents = await db
    .select({
      valueId: metricValues.id,
      metricId: metricValues.metricId,
      metricCode: metrics.code,
      displayName: metrics.displayName,
      unit: metricValues.unit,
      higherIsBetter: metrics.higherIsBetter,
      serviceScope: metricValues.serviceScope,
      value: metricValues.value,
      currency: metricValues.currency,
      periodId: metricValues.reportingPeriodId,
      periodLabel: reportingPeriods.label,
    })
    .from(metricValues)
    .innerJoin(metrics, eq(metricValues.metricId, metrics.id))
    .innerJoin(reportingPeriods, eq(metricValues.reportingPeriodId, reportingPeriods.id))
    .where(and(eq(metricValues.agencyId, agency.id), eq(metricValues.isCurrent, true)));
  if (currents.length === 0) return [];

  // Full history for trends (ordered chronologically).
  const history = await db
    .select({
      metricId: metricValues.metricId,
      serviceScope: metricValues.serviceScope,
      value: metricValues.value,
      periodLabel: reportingPeriods.label,
    })
    .from(metricValues)
    .innerJoin(reportingPeriods, eq(metricValues.reportingPeriodId, reportingPeriods.id))
    .where(eq(metricValues.agencyId, agency.id))
    .orderBy(asc(reportingPeriods.endDate));
  const trendByKey = new Map<string, { periodLabel: string; value: number }[]>();
  for (const h of history) {
    const key = `${h.metricId}:${h.serviceScope}`;
    const arr = trendByKey.get(key) ?? [];
    arr.push({ periodLabel: h.periodLabel, value: Number(h.value) });
    trendByKey.set(key, arr);
  }

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

  // Page-level provenance for the current value ids.
  const valueIds = currents.map((c) => c.valueId);
  const provRows = valueIds.length
    ? await db
        .select({
          metricValueId: metricValueSources.metricValueId,
          sourceTitle: sourceDocuments.title,
          sourceUrl: sourceDocuments.sourceUrl,
          pageNumber: metricValueSources.pageNumber,
          tableReference: metricValueSources.tableReference,
          license: sourceDocuments.license,
        })
        .from(metricValueSources)
        .innerJoin(sourceDocuments, eq(metricValueSources.sourceDocumentId, sourceDocuments.id))
        .where(inArray(metricValueSources.metricValueId, valueIds))
    : [];
  const provByValueId = new Map<number, MetricProvenance[]>();
  for (const p of provRows) {
    const arr = provByValueId.get(p.metricValueId) ?? [];
    arr.push({
      sourceTitle: p.sourceTitle,
      sourceUrl: p.sourceUrl,
      pageNumber: p.pageNumber,
      tableReference: p.tableReference,
      license: p.license,
    });
    provByValueId.set(p.metricValueId, arr);
  }

  return currents.map((c) => {
    const cohort = latestByMetric.get(c.metricId);
    const rankInfo = cohort ? rankByKey.get(`${c.metricId}:${cohort.periodId}`) : undefined;
    return {
      metricCode: c.metricCode,
      displayName: c.displayName,
      unit: c.unit,
      higherIsBetter: c.higherIsBetter,
      serviceScope: c.serviceScope,
      rank: rankInfo?.rank ?? null,
      denominator: rankInfo?.denominator ?? null,
      value: Number(c.value),
      currency: c.currency,
      periodLabel: c.periodLabel,
      trend: trendByKey.get(`${c.metricId}:${c.serviceScope}`) ?? [],
      provenance: provByValueId.get(c.valueId) ?? [],
      hasComparablePeriod: cohort ? c.periodId === cohort.periodId : false,
    };
  });
}
