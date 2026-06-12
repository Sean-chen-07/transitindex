import "server-only";
// This is STILL the only importer of the raw-value query layer (ESLint-enforced), so
// every value read stays on one audited path. Viewing is free by decision 2026-06-09
// (docs/design/detail-view-metrics.md §6) — no session, no reveal branch; the money
// gate now lives in the download route (/api/agency/[slug]/download).
import { getRawMetricSeries } from "./queries";
import { toMetricView } from "./transform";
import type { MetricView } from "./types";

export async function getDetailMetrics(slug: string): Promise<MetricView[]> {
  return (await getRawMetricSeries(slug)).map(toMetricView);
}
