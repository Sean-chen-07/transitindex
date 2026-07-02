/**
 * The detail-page metric view. The free/paid disjoint-type split (a value-free
 * FreeMetricView vs PaidMetricView) is RETIRED: viewing is free by decision 2026-06-09
 * (docs/design/detail-view-metrics.md §6), so raw numbers ship to everyone. MetricView
 * is still produced ONLY by the server choke point (access.ts → queries.ts); the paid
 * gate now lives on the per-agency CSV download route.
 */

export type MetricSuppressedReason =
  | "below_min_denominator"
  | "no_comparable_period"
  | "pending";

export interface SeriesPoint {
  periodType: string;
  periodLabel: string;
  endDate: string;
  value: number;
}

export interface MetricView {
  metricCode: string;
  displayName: string;
  unit: string;
  currency: string | null;
  value: number;
  asOfLabel: string;
  rank: number | null;
  denominator: number | null;
  suppressedReason?: MetricSuppressedReason;
  points: SeriesPoint[];
}

/** One fleet display class's latest summed count (metric-set-build-plan.md Phase 6). */
export interface FleetClassCount {
  fleetClass: string;
  value: number;
}
