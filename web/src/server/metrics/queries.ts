import "server-only";
import { and, eq, asc, inArray, isNull, isNotNull } from "drizzle-orm";
import { db } from "@/server/db";
import {
  agencies,
  metricValues,
  metrics,
  modes,
  reportingPeriods,
  metricRanks,
} from "@/db/schema";
import { getAgencyBySlug } from "@/server/data/agencies";
import { getLatestRankedPeriodPerMetric } from "@/server/data/ranks";
import { FREE_COMPARISON_SET } from "@/server/data/constants";
import {
  pickDirectoryValues,
  type RawMetricSeries,
  type DirectoryValue,
} from "./transform";
import type { FleetClassCount } from "./types";

// Mode -> fleet display class (metric-set-build-plan.md Phase 6), mirroring
// ingest/transitindex_ingest/refdata.py FLEET_CLASS. Ferry, paratransit, and
// on_demand are excluded from the composition.
const FLEET_CLASS: Record<string, string> = {
  bus: "bus",
  brt: "bus",
  trolleybus: "bus",
  light_rail: "light_rail",
  streetcar: "light_rail",
  subway: "heavy_rail",
  commuter_rail: "commuter_rail",
};

// The six metrics the directory card prints a figure for. `fleet_size` is read the same
// system-wide way as the rest: it has NO per-mode rows in the loaded data (checked
// 2026-08-05 — 0 rows with mode_id set), so summing a composition would always yield
// nothing. It is also unranked, so the card shows its figure with no ordinal.
const CARD_METRIC_CODES = [
  "ridership",
  "total_revenue_excluding_subsidy",
  "on_time_performance",
  "cost_per_rider",
  "subsidy_per_rider",
  "fleet_size",
];

// The card prints an ANNUAL figure. Restricting the period type here is what keeps this
// query small — ridership alone has ~134k monthly rows that the card must never pull.
const ANNUAL_PERIOD_TYPES = ["annual_calendar", "annual_fiscal"];

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

/**
 * Every directory card's figures in ONE constant query — no N+1 across the 657-agency
 * grid. Returns slug -> the latest annual value per card metric.
 *
 * Viewing is free by decision 2026-06-09, so shipping these figures to anonymous users on
 * the directory is the same posture as the detail page — no gate, no reveal branch.
 */
export async function getDirectoryCardValues(): Promise<
  Record<string, DirectoryValue[]>
> {
  const rows = await db
    .select({
      slug: agencies.slug,
      metricCode: metrics.code,
      serviceScope: metricValues.serviceScope,
      unit: metricValues.unit,
      value: metricValues.value,
      periodLabel: reportingPeriods.label,
      endDate: reportingPeriods.endDate,
    })
    .from(metricValues)
    .innerJoin(agencies, eq(metricValues.agencyId, agencies.id))
    .innerJoin(metrics, eq(metricValues.metricId, metrics.id))
    .innerJoin(reportingPeriods, eq(metricValues.reportingPeriodId, reportingPeriods.id))
    .where(
      and(
        eq(metricValues.isCurrent, true),
        isNull(metricValues.modeId),
        inArray(metrics.code, CARD_METRIC_CODES),
        inArray(reportingPeriods.periodType, ANNUAL_PERIOD_TYPES),
      ),
    )
    .orderBy(asc(reportingPeriods.endDate));

  // drizzle numeric comes back as a string.
  return pickDirectoryValues(rows.map((r) => ({ ...r, value: Number(r.value) })));
}

/**
 * The latest per-mode `fleet_size` (is_current=true, 'total' scope), grouped into
 * the 4 display classes (metric-set-build-plan.md Phase 6; supersedes the removed
 * `fleet_capacity` metric). One row per class present, "latest period per mode"
 * summed within a class. Not ranked -- no rank lookup here.
 */
export async function getFleetComposition(slug: string): Promise<FleetClassCount[]> {
  const agency = await getAgencyBySlug(slug);
  if (!agency) return [];

  const rows = await db
    .select({
      modeCode: modes.code,
      value: metricValues.value,
      endDate: reportingPeriods.endDate,
    })
    .from(metricValues)
    .innerJoin(metrics, eq(metricValues.metricId, metrics.id))
    .innerJoin(reportingPeriods, eq(metricValues.reportingPeriodId, reportingPeriods.id))
    .innerJoin(modes, eq(metricValues.modeId, modes.id))
    .where(
      and(
        eq(metricValues.agencyId, agency.id),
        eq(metricValues.isCurrent, true),
        eq(metrics.code, "fleet_size"),
        eq(metricValues.serviceScope, "total"),
        isNotNull(metricValues.modeId),
      ),
    )
    .orderBy(asc(reportingPeriods.endDate));

  // Latest value per mode: rows are chronological ascending, so the last write
  // per mode code wins (excludes ferry / paratransit / on_demand -- no FLEET_CLASS).
  const latestByModeClass = new Map<string, { cls: string; value: number }>();
  for (const r of rows) {
    const cls = FLEET_CLASS[r.modeCode];
    if (!cls) continue;
    latestByModeClass.set(r.modeCode, { cls, value: Number(r.value) });
  }

  const byClass = new Map<string, number>();
  for (const { cls, value } of latestByModeClass.values()) {
    byClass.set(cls, (byClass.get(cls) ?? 0) + value);
  }

  return [...byClass.entries()].map(([fleetClass, value]) => ({ fleetClass, value }));
}
