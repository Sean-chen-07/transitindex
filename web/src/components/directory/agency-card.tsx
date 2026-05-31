"use client";

import Link from "next/link";
import { Card } from "@/components/ui/card";
import { AgencyCardExpand } from "./agency-card-expand";
import { RankGrid } from "./rank-grid";
import { PendingNotice } from "@/components/common/states";
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

function modeLabel(code: string): string {
  return MODE_LABELS[code] ?? code;
}

/** Free directory card — expands in place to the rank grid (or a pending notice). */
export function AgencyCard({ item, ranks }: { item: AgencyListItem; ranks: AgencyRank[] }) {
  const header = (
    <div className="min-w-0">
      <p className="truncate text-base font-semibold text-ink">
        {item.shortName ?? item.legalName}
      </p>
      <p className="truncate text-sm text-ink-2">{item.legalName}</p>
      <div className="mt-2 flex flex-wrap gap-1">
        {item.primaryModes.map((m) => (
          <span
            key={m}
            className="rounded-full border border-line-2 bg-card-2 px-2 py-0.5 text-xs text-ink-2"
          >
            {modeLabel(m)}
          </span>
        ))}
      </div>
    </div>
  );

  return (
    <Card className="overflow-hidden hover:shadow-soft-hover">
      <AgencyCardExpand header={header}>
        {ranks.length > 0 ? <RankGrid ranks={ranks} /> : <PendingNotice slug={item.slug} />}
        <div className="mt-4">
          <Link
            href={`/agency/${item.slug}`}
            className="text-sm font-medium text-coral underline-offset-2 hover:underline"
          >
            Open full data →
          </Link>
        </div>
      </AgencyCardExpand>
    </Card>
  );
}
