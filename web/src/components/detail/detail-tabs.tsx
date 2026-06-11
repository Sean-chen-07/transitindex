"use client";

import * as React from "react";
import { cn } from "@/lib/cn";

/**
 * Minimal two-panel tab switch for the detail page (Highlights / Financials,
 * docs/design/detail-view-metrics.md §1). Both panels are server-rendered and passed in
 * as props — the client only toggles which one is visible, so no value crosses the
 * network that the server didn't already decide to reveal.
 */
export function DetailTabs({
  highlights,
  financials,
}: {
  highlights: React.ReactNode;
  financials: React.ReactNode;
}) {
  const [tab, setTab] = React.useState<"highlights" | "financials">("highlights");
  return (
    <section className="mt-8">
      <div role="tablist" aria-label="Data views" className="flex gap-1 border-b border-grid">
        {(["highlights", "financials"] as const).map((t) => (
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
            {t === "highlights" ? "Highlights" : "Financials"}
          </button>
        ))}
      </div>
      <div role="tabpanel" id="panel-highlights" aria-labelledby="tab-highlights" hidden={tab !== "highlights"}>
        {highlights}
      </div>
      <div role="tabpanel" id="panel-financials" aria-labelledby="tab-financials" hidden={tab !== "financials"}>
        {financials}
      </div>
    </section>
  );
}
