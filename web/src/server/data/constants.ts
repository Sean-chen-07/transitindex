import "server-only";

// The minimum cohort size before a rank is shown (shared with the renderer's
// defensive gate in @/lib/format). Below this -> "not yet ranked".
export { MIN_DENOMINATOR as MIN_DENOMINATOR_ALL } from "@/lib/format";

/**
 * The single DEMO agency (user decision 2026-05-31): its detail page serves the full
 * paid shape (numbers + provenance + trend) to EVERYONE, including crawlers — a
 * deliberate SEO/trust taste. The other 9 agencies stay account-gated. The reveal
 * decision lives inside the server-only choke point (access.ts) using this constant
 * + the real route slug — never a forgeable boolean.
 */
export const DEMO_AGENCY_SLUG = "ttc";

// Free re-rank scope only. The paid 'subdivision' (province) re-rank is deferred out
// of M1 (no province has >=5 launch agencies), so the free path hard-filters to 'all'.
export const FREE_COMPARISON_SET = "all" as const;
