/**
 * The free/paid metric views. The disjoint shape is a structural guarantee: a
 * FreeMetricView has NO `value` field, so a raw number cannot be serialized into a
 * free/anonymous payload by accident — it would be a type error. The raw `value`,
 * full trend, and page-level provenance exist ONLY on PaidMetricView, produced
 * exclusively by the server-only choke point (access.ts).
 */

export type RankDirection = "higher_is_better" | "lower_is_better" | "neutral";

export type MetricSuppressedReason =
  | "below_min_denominator"
  | "no_comparable_period"
  | "pending";

export interface FreeMetricView {
  metricCode: string;
  displayName: string;
  unit: string; // a unit LABEL (e.g. "count", "CAD") — never a value
  rank: number | null;
  denominator: number | null;
  direction: RankDirection;
  serviceScope: string | null;
  asOfLabel: string; // period label or "" — never "as of null"
  attribution: string; // required license notice
  shape: number[]; // bucketed, non-invertible; [] when < 2 points
  suppressedReason?: MetricSuppressedReason;
}

export interface MetricProvenance {
  sourceTitle: string | null;
  sourceUrl: string | null;
  pageNumber: number | null;
  tableReference: string | null;
  license: string | null;
}

export interface PaidMetricView extends FreeMetricView {
  value: number;
  currency: string | null;
  periodLabel: string;
  trend: { periodLabel: string; value: number }[];
  provenance: MetricProvenance[];
}
