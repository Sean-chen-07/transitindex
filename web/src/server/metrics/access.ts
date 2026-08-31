import "server-only";
// This is STILL the only importer of the raw-value query layer (ESLint-enforced), so
// every value read stays on one audited path. Viewing is free by decision 2026-06-09
// (docs/design/detail-view-metrics.md §6) — no session, no reveal branch; the money
// gate now lives in the download route (/api/agency/[slug]/download).
import { getRawMetricSeries, getFleetComposition, getDirectoryCardValues } from "./queries";
import { toMetricView } from "./transform";
import type { MetricView } from "./types";

// Re-exported through access.ts, the only permitted importer of queries.ts.
// getDirectoryCardValues feeds the free directory card, which prints figures alongside
// ordinals as of 2026-08-05 — same free-viewing posture as the detail page.
export { getFleetComposition, getDirectoryCardValues };
export type { DirectoryValue } from "./transform";

export async function getDetailMetrics(slug: string): Promise<MetricView[]> {
  return (await getRawMetricSeries(slug)).map(toMetricView);
}
