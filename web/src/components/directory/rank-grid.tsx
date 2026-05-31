import { rankLabel, srRankLabel } from "@/lib/format";
import type { AgencyRank } from "@/server/data/types";

/**
 * The free rank grid: plain ordinals ("3rd"), with the comparison set named ONCE per
 * grid (not on every cell). Renders the committed period-miss / N<5 states instead of
 * vanishing. Screen-reader text reads "ranked Nth of M". No raw numbers.
 */
export function RankGrid({ ranks }: { ranks: AgencyRank[] }) {
  if (ranks.length === 0) return null;
  return (
    <div>
      <p className="mb-2 text-xs text-ink-3">Ranked vs all Canadian agencies</p>
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {ranks.map((r) => (
          <RankCell key={r.metricCode} rank={r} />
        ))}
      </ul>
    </div>
  );
}

function RankCell({ rank }: { rank: AgencyRank }) {
  const periodMiss = rank.status === "not_ranked_period_miss";
  const visible = periodMiss
    ? `not ranked — latest ${rank.periodLabel ?? "—"}`
    : rankLabel({ rank: rank.rank, denominator: rank.denominator });
  const sr = periodMiss
    ? `${rank.metricDisplayName}: not ranked, latest ${rank.periodLabel ?? "unknown"}`
    : `${rank.metricDisplayName}: ${srRankLabel({ rank: rank.rank, denominator: rank.denominator })}`;
  const isOrdinal = !periodMiss && visible !== "not yet ranked";

  return (
    <li className="rounded-cell border border-line-2 bg-card-2 p-3">
      <span className="sr-only">{sr}</span>
      <p aria-hidden className="text-xs text-ink-2">
        {rank.metricDisplayName}
      </p>
      <p
        aria-hidden
        className={
          isOrdinal
            ? "tnum text-2xl font-semibold text-ink"
            : "mt-0.5 text-sm italic text-ink-3"
        }
      >
        {visible}
      </p>
    </li>
  );
}
