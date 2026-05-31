import "server-only";
import { DEMO_AGENCY_SLUG } from "@/server/data/constants";
import { isPaid, type Session } from "@/server/entitlement";
// This is the ONE module allowed to import the raw-value query layer (ESLint-enforced).
import { getRawMetricSeries } from "./queries";
import { toFreeView, toPaidView } from "./transform";
import type { FreeMetricView, PaidMetricView } from "./types";

export interface DetailMetrics {
  /** true => raw numbers are shown (paid account OR the demo agency). */
  reveal: boolean;
  metrics: FreeMetricView[] | PaidMetricView[];
}

/**
 * THE PAYWALL CHOKE POINT. The only path that turns raw values into a view. The reveal
 * decision uses non-forgeable inputs only — the real route slug (demo un-gate) and the
 * real session (paid) — never a caller-supplied boolean. If not revealed, raw values are
 * dropped here and a value-free FreeMetricView[] is returned (so anon/crawler detail
 * pages still render ranks for SEO).
 */
export async function getDetailMetrics(
  slug: string,
  session: Session | null,
): Promise<DetailMetrics> {
  const reveal = slug === DEMO_AGENCY_SLUG || (await isPaid(session));
  const raw = await getRawMetricSeries(slug);
  return reveal
    ? { reveal: true, metrics: raw.map(toPaidView) }
    : { reveal: false, metrics: raw.map(toFreeView) };
}

/**
 * Free metrics only — for generateMetadata / JSON-LD / sitemap, which must NEVER reveal
 * numbers regardless of who is asking (not even for the demo agency, to keep structured
 * data value-free).
 */
export async function getFreeMetrics(slug: string): Promise<FreeMetricView[]> {
  const raw = await getRawMetricSeries(slug);
  return raw.map(toFreeView);
}
