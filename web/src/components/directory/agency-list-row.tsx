import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { rankLabel, provinceName } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { AgencyListItem, AgencyRank } from "@/server/data/types";

// Mode-group color + label (DESIGN.md). Mirrors agency-card.tsx; kept local so the two
// directory layouts (phone list / desktop cards) stay independently editable.
function modeGroup(modes: string[]): { cls: string; label: string } {
  if (modes.includes("subway")) return { cls: "bg-teal", label: "Rapid rail" };
  if (modes.includes("commuter_rail")) return { cls: "bg-mode-blue", label: "Commuter rail" };
  if (modes.includes("light_rail") || modes.includes("streetcar"))
    return { cls: "bg-mode-sage", label: "Light rail" };
  if (modes.includes("ferry")) return { cls: "bg-coral", label: "Multimodal" };
  return { cls: "bg-mode-yellow", label: "Bus" };
}

const PEEK_LABELS: Record<string, string> = {
  annual_ridership: "ridership",
  monthly_ridership: "ridership",
  operating_revenue: "revenue",
  farebox_recovery_ratio: "farebox",
  cost_per_rider: "cost/rider",
  revenue_service_hours: "service hrs",
  fleet_size: "fleet",
};

// Up to two safe-to-show ordinals, marquee metrics first, de-duplicated by label.
function pickPeek(ranks: AgencyRank[]): AgencyRank[] {
  const order = ["annual_ridership", "monthly_ridership", "operating_revenue", "farebox_recovery_ratio"];
  const seen = new Set<string>();
  return ranks
    .filter((r) => r.status === "ranked" && r.rank != null)
    .sort((a, b) => {
      const ai = order.indexOf(a.metricCode);
      const bi = order.indexOf(b.metricCode);
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    })
    .filter((r) => {
      const label = PEEK_LABELS[r.metricCode] ?? r.metricCode;
      if (seen.has(label)) return false;
      seen.add(label);
      return true;
    })
    .slice(0, 2);
}

/**
 * Compact phone-only directory row: one tap target linking to the agency detail page.
 * Shows the agency, its mode bar, and up to two peek ranks (or "pending"). Denser than the
 * desktop card grid — used under the `sm` breakpoint.
 */
export function AgencyListRow({
  item,
  ranks,
}: {
  item: AgencyListItem;
  ranks: AgencyRank[];
}) {
  const group = modeGroup(item.primaryModes);
  const peek = pickPeek(ranks);

  return (
    <Link
      href={`/agency/${item.slug}`}
      className="flex items-center gap-3 px-4 py-3 hover:bg-card-2"
    >
      <span aria-hidden className={cn("h-8 w-1.5 shrink-0 rounded-full", group.cls)} />
      <span className="sr-only">Mode group: {group.label}. </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-semibold text-ink">
          {item.shortName ?? item.legalName}
        </span>
        <span className="block truncate text-xs text-ink-2">
          {provinceName(item.subdivision)}
        </span>
      </span>
      {peek.length > 0 ? (
        <span className="flex shrink-0 items-center gap-3">
          {peek.map((r) => (
            <span key={r.metricCode} className="w-12 text-center">
              <span className="tnum block text-base font-bold leading-none text-ink">
                {rankLabel({ rank: r.rank, denominator: r.denominator })}
              </span>
              <span className="mt-0.5 block text-[10px] uppercase tracking-wide text-ink-3">
                {PEEK_LABELS[r.metricCode] ?? ""}
              </span>
            </span>
          ))}
        </span>
      ) : (
        <span className="shrink-0 text-xs italic text-ink-3">pending</span>
      )}
      <ChevronRight aria-hidden className="h-4 w-4 shrink-0 text-ink-3" />
    </Link>
  );
}
