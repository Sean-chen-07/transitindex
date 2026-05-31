/**
 * The free-tier trend "shape". A sparkline shape is allowed on the free surface,
 * but the RAW values behind it are paid — so the shape must be NON-INVERTIBLE:
 * min-max normalize to 0..1, then quantize to <=10 coarse buckets so neither the
 * original values nor inter-period ratios are recoverable from the points shipped
 * to the client. Below 2 points the chart is suppressed entirely (the absent trend
 * is itself the signal "not enough history").
 *
 * This is pure (no DB, no `value` ever leaves here) so it is safe to ship the
 * RESULT to a client component. The raw input array is assembled only inside the
 * server-only metrics choke point.
 */

const SHAPE_BUCKETS = 10;
export const MIN_SHAPE_POINTS = 2;

export function toShape(values: number[]): number[] {
  if (values.length < MIN_SHAPE_POINTS) return [];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min;
  return values.map((v) => {
    const norm = span === 0 ? 0.5 : (v - min) / span;
    return Math.round(norm * SHAPE_BUCKETS) / SHAPE_BUCKETS;
  });
}
