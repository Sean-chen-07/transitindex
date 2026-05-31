import { Lock } from "lucide-react";
import { rankLabel, srRankLabel } from "@/lib/format";
import { UpgradeDialog } from "./upgrade-dialog";
import type { FreeMetricView } from "@/server/metrics/types";

/**
 * The "numbers gated (anonymous)" state: the real rank is shown, the value is a LOCKED
 * placeholder (never a real number — the free payload carries none), with one upgrade
 * CTA below the table. This is an account-gate, not a metered wall.
 */
export function GatedTable({
  metrics,
  agencyId,
}: {
  metrics: FreeMetricView[];
  agencyId: number;
}) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-2">
        Full data
      </h2>
      <table className="w-full border-collapse text-sm">
        <caption className="sr-only">
          Metrics for this agency. Numbers are gated behind a membership; ranks are free.
        </caption>
        <thead>
          <tr className="border-b border-grid text-left text-ink-2">
            <th scope="col" className="py-2 pr-4 font-medium">Metric</th>
            <th scope="col" className="py-2 pr-4 text-right font-medium">Value</th>
            <th scope="col" className="py-2 text-right font-medium">Rank</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => {
            const ord = rankLabel({ rank: m.rank, denominator: m.denominator });
            return (
              <tr key={m.metricCode} className="border-b border-grid/60">
                <td className="py-2 pr-4 text-ink">{m.displayName}</td>
                <td className="py-2 pr-4 text-right">
                  <span className="sr-only">Value hidden — members only</span>
                  <span
                    aria-hidden
                    className="inline-flex items-center gap-1 text-ink-3"
                  >
                    <Lock className="h-3.5 w-3.5" /> ••••
                  </span>
                </td>
                <td className="py-2 text-right tnum text-ink">
                  <span className="sr-only">{srRankLabel({ rank: m.rank, denominator: m.denominator })}</span>
                  <span aria-hidden className={ord === "not yet ranked" ? "italic text-ink-3" : ""}>
                    {ord}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="mt-5">
        <UpgradeDialog agencyId={agencyId} />
      </div>
    </section>
  );
}
