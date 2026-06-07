"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

/**
 * Minimal two-panel tab switch for the detail page (Snapshot / Trends). Both panels are
 * server-rendered and passed in as props — the client only toggles which one is visible,
 * so no value crosses the network that the server didn't already decide to reveal.
 */
export function DetailTabs({
  snapshot,
  trends,
}: {
  snapshot: React.ReactNode;
  trends: React.ReactNode;
}) {
  const [tab, setTab] = React.useState<"snapshot" | "trends">("snapshot");
  return (
    <section className="mt-8">
      <div role="tablist" aria-label="Data views" className="flex gap-1 border-b border-grid">
        {(["snapshot", "trends"] as const).map((t) => (
          <button
            key={t}
            role="tab"
            id={`tab-${t}`}
            aria-selected={tab === t}
            aria-controls={`panel-${t}`}
            onClick={() => setTab(t)}
            className={cn(
              "min-h-[40px] px-4 text-sm font-medium transition-colors",
              tab === t
                ? "-mb-px border-b-2 border-coral text-ink"
                : "text-ink-3 hover:text-ink-2",
            )}
          >
            {t === "snapshot" ? "Snapshot" : "Trends"}
          </button>
        ))}
      </div>
      <div role="tabpanel" id="panel-snapshot" aria-labelledby="tab-snapshot" hidden={tab !== "snapshot"}>
        {snapshot}
      </div>
      <div role="tabpanel" id="panel-trends" aria-labelledby="tab-trends" hidden={tab !== "trends"}>
        {trends}
      </div>
    </section>
  );
}
