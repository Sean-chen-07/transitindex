import Link from "next/link";
import { rankLabel, provinceName } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { AgencyListItem, AgencyRank } from "@/server/data/types";

// Soft mode-group color + label (DESIGN.md). Color is paired with the text label below,
// never the sole signal.
function modeGroup(modes: string[]): { cls: string; label: string } {
  if (modes.includes("subway")) return { cls: "bg-teal", label: "Rapid rail" };
  if (modes.includes("commuter_rail")) return { cls: "bg-mode-blue", label: "Commuter rail" };
  if (modes.includes("light_rail") || modes.includes("streetcar"))
    return { cls: "bg-mode-sage", label: "Light rail" };
  if (modes.includes("ferry")) return { cls: "bg-coral", label: "Multimodal" };
  return { cls: "bg-mode-yellow", label: "Bus" };
}

// The six free "fundamentals". Free payload is rank-only — these are ORDINALS, never raw
// numbers (raw values live behind the gate on the detail page). Ridership prefers the annual
// rank, falling back to the monthly one.
const METRIC_SLOTS: { label: string; codes: string[] }[] = [
  { label: "Ridership", codes: ["annual_ridership", "monthly_ridership"] },
  { label: "Revenue", codes: ["operating_revenue"] },
  { label: "Farebox", codes: ["farebox_recovery_ratio"] },
  { label: "Cost / rider", codes: ["cost_per_rider"] },
  { label: "Service hrs", codes: ["revenue_service_hours"] },
  { label: "Fleet", codes: ["fleet_size"] },
];

function rankFor(ranks: AgencyRank[], codes: string[]): string | null {
  for (const code of codes) {
    const r = ranks.find(
      (x) => x.metricCode === code && x.status === "ranked" && x.rank != null,
    );
    if (r) return rankLabel({ rank: r.rank, denominator: r.denominator });
  }
  return null;
}

/**
 * One agency as a vertical "mini page" card for the grid directory: name + province + mode,
 * a fixed six-metric rank grid (ordinals only, "—" until sourced), and a drill-in button to
 * the detail page. Crawlable: name + button are real <Link>s in the server HTML.
 */
export function AgencyCard({
  item,
  ranks,
}: {
  item: AgencyListItem;
  ranks: AgencyRank[];
}) {
  const group = modeGroup(item.primaryModes);
  const hasRanks = ranks.some((r) => r.status === "ranked" && r.rank != null);

  return (
    <div className="flex flex-col overflow-hidden rounded-card border border-line bg-card shadow-soft transition-shadow hover:shadow-soft-hover">
      <div className="flex items-start justify-between gap-3 px-5 pt-5">
        <div className="min-w-0">
          <Link
            href={`/agency/${item.slug}`}
            className="block truncate text-lg font-semibold text-ink hover:underline"
          >
            {item.shortName ?? item.legalName}
          </Link>
          <p className="mt-0.5 truncate text-sm text-ink-2">
            {provinceName(item.subdivision)}
          </p>
        </div>
        <span className="inline-flex shrink-0 items-center gap-1.5 rounded-full bg-card-2 px-2.5 py-1 text-xs font-medium text-ink-2">
          <span aria-hidden className={cn("h-2 w-2 rounded-full", group.cls)} />
          {group.label}
        </span>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-x-3 gap-y-4 border-t border-line-2 px-5 py-4">
        {METRIC_SLOTS.map((slot) => {
          const r = rankFor(ranks, slot.codes);
          return (
            <div key={slot.label} className="text-center">
              <div className="tnum text-xl font-bold leading-none text-ink">
                {r ?? <span className="font-medium text-ink-3">—</span>}
              </div>
              <div className="mt-1 text-[10px] uppercase leading-tight tracking-wide text-ink-3">
                {slot.label}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-auto px-5 pb-5">
        <Link
          href={`/agency/${item.slug}`}
          className="flex w-full items-center justify-center rounded-full bg-coral-soft px-4 py-2.5 text-sm font-semibold text-coral transition-colors hover:bg-coral hover:text-card"
        >
          {hasRanks ? "View full data →" : "Request this agency →"}
        </Link>
      </div>
    </div>
  );
}
