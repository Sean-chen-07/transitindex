import { toShape } from "./shape";
import { licenseToAttribution } from "./attribution";
import { MIN_DENOMINATOR } from "@/lib/format";
import type {
  FreeMetricView,
  PaidMetricView,
  RankDirection,
  MetricSuppressedReason,
  MetricProvenance,
} from "./types";

/**
 * The raw, value-bearing row produced ONLY by the server-only queries module. It is
 * mapped to a Free or Paid view here. These transforms are PURE (no DB) so the
 * leak-prevention logic is unit-tested offline: toFreeView must never carry `value`,
 * `trend`, `provenance`, or any recoverable raw number.
 */
export interface RawMetricRow {
  metricCode: string;
  displayName: string;
  unit: string;
  higherIsBetter: boolean | null;
  serviceScope: string | null;
  rank: number | null;
  denominator: number | null;
  value: number;
  currency: string | null;
  periodLabel: string;
  trend: { periodLabel: string; value: number }[];
  provenance: MetricProvenance[];
  /** Whether the agency has a rank in the cohort's latest period for this metric. */
  hasComparablePeriod: boolean;
}

function directionOf(hib: boolean | null): RankDirection {
  if (hib === true) return "higher_is_better";
  if (hib === false) return "lower_is_better";
  return "neutral";
}

function suppressedReason(row: RawMetricRow): MetricSuppressedReason | undefined {
  if (!row.hasComparablePeriod) return "no_comparable_period";
  if (row.rank == null || row.denominator == null) return "pending";
  if (row.denominator < MIN_DENOMINATOR) return "below_min_denominator";
  return undefined;
}

/** Free view: rank + direction + as-of + attribution + a non-invertible shape. NO value. */
export function toFreeView(row: RawMetricRow): FreeMetricView {
  const reason = suppressedReason(row);
  return {
    metricCode: row.metricCode,
    displayName: row.displayName,
    unit: row.unit,
    rank: reason ? null : row.rank,
    denominator: reason ? null : row.denominator,
    direction: directionOf(row.higherIsBetter),
    serviceScope: row.serviceScope,
    asOfLabel: row.periodLabel ?? "",
    attribution: licenseToAttribution(row.provenance[0]?.license ?? null),
    shape: toShape(row.trend.map((t) => t.value)),
    ...(reason ? { suppressedReason: reason } : {}),
  };
}

/** Paid view: the free view PLUS the raw value, full trend, and page-level provenance. */
export function toPaidView(row: RawMetricRow): PaidMetricView {
  return {
    ...toFreeView(row),
    value: row.value,
    currency: row.currency,
    periodLabel: row.periodLabel,
    trend: row.trend,
    provenance: row.provenance,
  };
}
