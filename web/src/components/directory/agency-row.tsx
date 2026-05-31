"use client";

import * as React from "react";
import Link from "next/link";
import { ChevronDown } from "lucide-react";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";
import { RankGrid } from "./rank-grid";
import { PendingNotice } from "@/components/common/states";
import { rankLabel, provinceName } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { AgencyListItem, AgencyRank } from "@/server/data/types";

const MODE_LABELS: Record<string, string> = {
  bus: "Bus",
  subway: "Subway",
  light_rail: "Light rail",
  commuter_rail: "Commuter rail",
  streetcar: "Streetcar",
  brt: "BRT",
  trolleybus: "Trolleybus",
  ferry: "Ferry",
  paratransit: "Paratransit",
  on_demand: "On-demand",
};

// Short labels for the 1–2 peek ranks shown on the collapsed row.
const PEEK_LABELS: Record<string, string> = {
  annual_ridership: "ridership",
  monthly_ridership: "ridership",
  farebox_recovery_ratio: "farebox",
  cost_per_rider: "cost/rider",
  operating_revenue: "revenue",
  revenue_service_hours: "service hrs",
  fleet_size: "fleet",
};

// Soft mode-group color bar (DESIGN.md). Color is paired with an sr-only group label —
// never the sole signal — and is decorative for sighted users (modes are labelled on
// expand + on the detail page).
function modeGroup(modes: string[]): { cls: string; label: string } {
  if (modes.includes("subway")) return { cls: "bg-teal", label: "Rapid rail" };
  if (modes.includes("commuter_rail")) return { cls: "bg-mode-blue", label: "Commuter rail" };
  if (modes.includes("light_rail") || modes.includes("streetcar"))
    return { cls: "bg-mode-sage", label: "Light rail" };
  if (modes.includes("ferry")) return { cls: "bg-coral", label: "Multimodal" };
  // Bus family (bus / on-demand / paratransit / BRT) — the long-tail default.
  return { cls: "bg-mode-yellow", label: "Bus" };
}

function peekLabel(rank: AgencyRank): string {
  return (
    PEEK_LABELS[rank.metricCode] ??
    (rank.metricDisplayName.split(" ")[0] ?? rank.metricDisplayName).toLowerCase()
  );
}

// Up to two safe-to-show ordinals, marquee metrics first. Deduplicated by label so
// "annual ridership" and "monthly ridership" (both map to "ridership") never both appear.
function pickPeek(ranks: AgencyRank[]): AgencyRank[] {
  const order = ["annual_ridership", "monthly_ridership", "farebox_recovery_ratio", "cost_per_rider"];
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
 * One agency as a full-width, table-like directory row that expands in place
 * (DESIGN.md D11 / wireframes-v5). The name is an always-rendered <Link> (crawlable in
 * the server HTML, regardless of expand state); the right-hand cluster is the expand
 * trigger. Payload is rank-only — no raw numbers ever reach the client.
 */
export function AgencyRow({ item, ranks }: { item: AgencyListItem; ranks: AgencyRank[] }) {
  const [open, setOpen] = React.useState(false);
  const group = modeGroup(item.primaryModes);
  const peek = pickPeek(ranks);

  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className={cn(
        "border-b border-line-2 last:border-b-0",
        open && "bg-card-2",
      )}
    >
      <div className="flex items-stretch">
        <Link
          href={`/agency/${item.slug}`}
          className="group flex min-w-0 flex-1 items-center gap-3 px-4 py-3 hover:bg-card-2"
        >
          <span aria-hidden className={cn("h-9 w-1.5 shrink-0 rounded-full", group.cls)} />
          <span className="sr-only">Mode group: {group.label}. </span>
          <span className="min-w-0">
            <span className="block truncate font-semibold text-ink group-hover:underline">
              {item.shortName ?? item.legalName}
            </span>
            <span className="block truncate text-xs text-ink-2">{item.legalName}</span>
          </span>
        </Link>

        <CollapsibleTrigger
          className="flex shrink-0 items-center gap-3 px-3 py-3 text-left hover:bg-card-2 sm:gap-5 sm:px-4"
          aria-label={`${open ? "Collapse" : "Expand"} ranks for ${item.shortName ?? item.legalName}`}
        >
          <span className="hidden w-32 truncate text-sm text-ink-2 md:block">
            {provinceName(item.subdivision)}
          </span>

          <span className="hidden items-center gap-4 sm:w-[152px] sm:flex">
            {peek.length > 0 ? (
              peek.map((r) => (
                <span key={r.metricCode} className="w-14 text-center">
                  <span className="tnum block text-lg font-bold leading-none text-ink">
                    {rankLabel({ rank: r.rank, denominator: r.denominator })}
                  </span>
                  <span className="mt-0.5 block text-[10px] uppercase tracking-wide text-ink-3">
                    {peekLabel(r)}
                  </span>
                </span>
              ))
            ) : (
              <span className="text-xs italic text-ink-3">Fundamentals pending</span>
            )}
          </span>

          <ChevronDown
            aria-hidden
            className={cn(
              "h-5 w-5 shrink-0 text-ink-3 transition-transform",
              open && "rotate-180 text-coral",
            )}
          />
        </CollapsibleTrigger>
      </div>

      <CollapsibleContent className="px-4 pb-5 pt-1">
        <div className="mb-3 flex flex-wrap gap-1.5">
          {item.primaryModes.map((m) => (
            <span
              key={m}
              className="rounded-full border border-line bg-card px-2 py-0.5 text-xs font-medium text-ink-2"
            >
              {MODE_LABELS[m] ?? m}
            </span>
          ))}
        </div>

        {item.hasAnyRank && ranks.length > 0 ? (
          <RankGrid ranks={ranks} />
        ) : (
          <PendingNotice slug={item.slug} />
        )}

        <div className="mt-4">
          <Link
            href={`/agency/${item.slug}`}
            className="text-sm font-medium text-coral underline-offset-2 hover:underline"
          >
            Open full data →
          </Link>
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
