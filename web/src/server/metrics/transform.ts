import { MIN_DENOMINATOR } from "@/lib/format";
import type { MetricView, MetricSuppressedReason } from "./types";

/**
 * The raw, value-bearing series produced ONLY by the server-only queries module —
 * one entry per metric, points in chronological order. The transform is PURE (no DB)
 * so the rank-suppression logic is unit-tested offline (transform.test.ts).
 */
export interface RawMetricSeries {
  metricCode: string;
  displayName: string;
  unit: string;
  higherIsBetter: boolean | null;
  serviceScope: string;
  /** From the latest point's row. */
  currency: string | null;
  rank: number | null;
  denominator: number | null;
  /** Whether the series has a point in the cohort's latest ranked period. */
  hasComparablePeriod: boolean;
  /** Chronological (endDate asc); never empty when produced by queries.ts. */
  points: {
    periodId: number;
    periodType: string;
    periodLabel: string;
    endDate: string;
    value: number;
  }[];
}

/* ------------------------------------------------------------------------- *
 * Directory-card values (2026-08-05). The card now shows the FIGURE next to the
 * ordinal, so the homepage needs one batched value read across every agency. The
 * DB work stays in queries.ts; the picking rules live here so they are unit-tested
 * offline, exactly like the rank suppression above.
 * ------------------------------------------------------------------------- */

/** One system-wide annual row as selected by queries.ts, chronological asc. */
export interface DirectoryValueRow {
  slug: string;
  metricCode: string;
  serviceScope: string;
  unit: string;
  value: number;
  periodLabel: string;
  endDate: string;
}

/** The latest annual figure for one metric on one agency's card. */
export interface DirectoryValue {
  metricCode: string;
  value: number;
  unit: string;
  periodLabel: string;
  endDate: string;
}

/**
 * Latest annual value per (agency, metric). Scope preference mirrors getRawMetricSeries:
 * 'total' when present, else the lexically-first scope, so a card never silently mixes a
 * conventional-only figure with a total one. Rows must arrive endDate-ascending.
 */
export function pickDirectoryValues(
  rows: DirectoryValueRow[],
): Record<string, DirectoryValue[]> {
  const groups = new Map<string, DirectoryValueRow[]>();
  for (const r of rows) {
    const key = `${r.slug} ${r.metricCode}`;
    const list = groups.get(key) ?? [];
    list.push(r);
    groups.set(key, list);
  }

  const out: Record<string, DirectoryValue[]> = {};
  for (const list of groups.values()) {
    const scopes = [...new Set(list.map((r) => r.serviceScope))];
    const scope = scopes.includes("total")
      ? "total"
      : scopes.reduce((a, b) => (a < b ? a : b));
    const kept = list.filter((r) => r.serviceScope === scope);
    const latest = kept[kept.length - 1];
    if (!latest) continue; // unreachable: scope comes from the rows themselves
    (out[latest.slug] ??= []).push({
      metricCode: latest.metricCode,
      value: latest.value,
      unit: latest.unit,
      periodLabel: latest.periodLabel,
      endDate: latest.endDate,
    });
  }
  return out;
}

function suppressedReason(raw: RawMetricSeries): MetricSuppressedReason | undefined {
  if (!raw.hasComparablePeriod) return "no_comparable_period";
  if (raw.rank == null || raw.denominator == null) return "pending";
  if (raw.denominator < MIN_DENOMINATOR) return "below_min_denominator";
  return undefined;
}

/** Value + as-of come from the LAST (latest) point; suppressed ranks are nulled. */
export function toMetricView(raw: RawMetricSeries): MetricView {
  const last = raw.points[raw.points.length - 1];
  if (!last) throw new Error(`empty metric series for ${raw.metricCode}`);
  const reason = suppressedReason(raw);
  return {
    metricCode: raw.metricCode,
    displayName: raw.displayName,
    unit: raw.unit,
    currency: raw.currency,
    value: last.value,
    asOfLabel: last.periodLabel,
    rank: reason ? null : raw.rank,
    denominator: reason ? null : raw.denominator,
    points: raw.points.map((p) => ({
      periodType: p.periodType,
      periodLabel: p.periodLabel,
      endDate: p.endDate,
      value: p.value,
    })),
    ...(reason ? { suppressedReason: reason } : {}),
  };
}
