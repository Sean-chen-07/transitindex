import "server-only";

// The minimum cohort size before a rank is shown (shared with the renderer's
// defensive gate in @/lib/format). Below this -> "not yet ranked".
export { MIN_DENOMINATOR as MIN_DENOMINATOR_ALL } from "@/lib/format";

// Free re-rank scope only. The paid 'subdivision' (province) re-rank is deferred out
// of M1 (no province has >=5 launch agencies), so the free path hard-filters to 'all'.
export const FREE_COMPARISON_SET = "all" as const;
