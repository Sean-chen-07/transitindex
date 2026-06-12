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
