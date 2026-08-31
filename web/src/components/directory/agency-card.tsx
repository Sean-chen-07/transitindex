import Link from "next/link";
import { rankLabel, srRankLabel, provinceName, formatMetricValue } from "@/lib/format";
import { cn } from "@/lib/cn";
import type { AgencyListItem, AgencyRank } from "@/server/data/types";
import type { DirectoryValue } from "@/server/metrics/access";

// Soft mode-group colour + label (DESIGN.md). Colour is paired with the text label
// below, never the sole signal. `bar`/`ring` drive the route rail on the ticket stub.
function modeGroup(modes: string[]): { bar: string; ring: string; label: string } {
  if (modes.includes("subway"))
    return { bar: "bg-teal", ring: "border-teal", label: "Rapid rail" };
  if (modes.includes("commuter_rail"))
    return { bar: "bg-mode-blue", ring: "border-mode-blue", label: "Commuter rail" };
  if (modes.includes("light_rail") || modes.includes("streetcar"))
    return { bar: "bg-mode-sage", ring: "border-mode-sage", label: "Light rail" };
  if (modes.includes("ferry"))
    return { bar: "bg-coral", ring: "border-coral", label: "Multimodal" };
  return { bar: "bg-mode-yellow", ring: "border-mode-yellow", label: "Bus" };
}

/**
 * The six ticket fields. Ridership leads AND is repeated in the stamp — deliberate,
 * it is the headline number. `fleet_size` is the one unranked slot: it is summed from
 * per-mode counts and has no cohort, so it prints a figure with no ordinal.
 */
const FIELDS: { label: string; code: string }[] = [
  { label: "Riders / yr", code: "ridership" },
  { label: "Revenue / yr", code: "total_revenue_excluding_subsidy" },
  { label: "On-time", code: "on_time_performance" },
  { label: "Cost / rider", code: "cost_per_rider" },
  { label: "Subsidy / rider", code: "subsidy_per_rider" },
  { label: "Fleet", code: "fleet_size" },
];

/** Ordinal + its screen-reader long form, or null when nothing is safe to show. */
function rankFor(ranks: AgencyRank[], code: string): { ordinal: string; sr: string } | null {
  const r = ranks.find(
    (x) => x.metricCode === code && x.status === "ranked" && x.rank != null,
  );
  if (!r) return null;
  // The suppression gate can still refuse (N<5, out-of-range) — treat that as unranked
  // rather than printing "not yet ranked" into a slot the width of an ordinal.
  const ordinal = rankLabel({ rank: r.rank, denominator: r.denominator });
  if (ordinal === "not yet ranked") return null;
  return { ordinal, sr: srRankLabel({ rank: r.rank, denominator: r.denominator }) };
}

/**
 * One agency as a paper fare ticket for the grid directory: a perforated stub carrying
 * the mode-group route rail, the agency name, a stamped ridership rank, and six fields
 * each printing the figure with its ordinal beside it ("411.5M · 1st"). Crawlable: name
 * and footer are real <Link>s in the server HTML. Texture is decorative and safe to strip.
 */
export function AgencyCard({
  item,
  ranks,
  values,
}: {
  item: AgencyListItem;
  ranks: AgencyRank[];
  values: DirectoryValue[];
}) {
  const group = modeGroup(item.primaryModes);
  const headline = rankFor(ranks, "ridership");
  const byCode = new Map(values.map((v) => [v.metricCode, v]));
  // "Request this agency" is only honest when the detail page has NOTHING to show. An
  // agency can carry figures without ranks (ranks are refreshed per cohort run), so the
  // CTA follows either signal — not ranks alone.
  const hasData =
    values.length > 0 || ranks.some((r) => r.status === "ranked" && r.rank != null);

  // "As of" is the LATEST annual period among the card's figures. Metrics can carry
  // different periods (calendar vs fiscal years); the per-metric "as of" lives on the
  // detail page, so this is labelled as-of rather than presented as one fiscal year.
  const asOf = values
    .filter((v) => v.endDate)
    .sort((a, b) => a.endDate.localeCompare(b.endDate))
    .at(-1);

  return (
    <div className="ticket-paper relative flex overflow-hidden rounded-ticket bg-paper shadow-soft transition-shadow hover:shadow-soft-hover">
      {/* Route rail — stretches with the card so the line never stops short. The column
          must be flex-col: in a row flex, `flex-1` would grow the line sideways. */}
      <div
        aria-hidden
        className="relative flex w-[52px] shrink-0 flex-col items-center py-5"
      >
        <span className={cn("w-1 flex-1 rounded-full", group.bar)} />
        <span
          className={cn("absolute left-1/2 top-4 h-3 w-3 -translate-x-1/2 rounded-full", group.bar)}
        />
        {["top-[30%]", "top-[52%]", "top-[74%]"].map((pos) => (
          <span
            key={pos}
            className={cn(
              "absolute left-1/2 h-[11px] w-[11px] -translate-x-1/2 rounded-full border-[2.5px] bg-paper",
              group.ring,
              pos,
            )}
          />
        ))}
      </div>
      <span aria-hidden className="ticket-perf absolute inset-y-2 left-[52px] w-0.5" />

      <div className="flex min-w-0 flex-1 flex-col px-5 pt-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            {/* Two lines, then ellipsis — legal names ("Alameda-Contra Costa Transit
                District") are long enough that single-line truncation loses the city. */}
            <Link
              href={`/agency/${item.slug}`}
              className="line-clamp-2 text-[17px] font-bold leading-tight text-ink hover:underline"
            >
              {item.shortName ?? item.legalName}
            </Link>
            <p className="mt-1 truncate text-[10px] uppercase tracking-[0.16em] text-ink-3">
              {provinceName(item.subdivision)} · {group.label}
            </p>
          </div>
          {/* Border keeps the rubber-stamp coral; the text uses --coral-ink because
              --coral is only ~3:1 on paper and this is 9.5px. */}
          {headline ? (
            <span className="tnum -rotate-6 shrink-0 rounded-[3px] border-[1.5px] border-coral px-2 py-1 text-center text-[9.5px] font-bold uppercase leading-tight tracking-[0.1em] text-coral-ink">
              <span aria-hidden>
                Ridership
                <br />
                {headline.ordinal}
              </span>
              <span className="sr-only">Ridership {headline.sr}</span>
            </span>
          ) : (
            <span className="shrink-0 rounded-[3px] border border-dashed border-paper-line px-2 py-1 text-center text-[9.5px] font-bold uppercase leading-tight tracking-[0.1em] text-ink-3">
              Ridership
              <br />
              pending
            </span>
          )}
        </div>

        <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-3">
          {FIELDS.map((field) => {
            const value = byCode.get(field.code);
            const rank = rankFor(ranks, field.code);
            return (
              <div
                key={field.code}
                className="border-b border-dotted border-paper-line pb-1.5"
              >
                <div className="text-[9px] uppercase leading-tight tracking-[0.14em] text-ink-3">
                  {field.label}
                </div>
                <div className="mt-1 flex items-baseline gap-1.5">
                  <span className="tnum text-[17px] font-semibold leading-none text-ink">
                    {value == null ? (
                      <span aria-hidden className="font-medium text-ink-3">
                        —
                      </span>
                    ) : (
                      formatMetricValue(value.value, value.unit, item.currency, {
                        compact: true,
                      })
                    )}
                  </span>
                  {rank && (
                    <span className="tnum text-[10px] font-medium leading-none text-ink-3">
                      <span aria-hidden>{rank.ordinal}</span>
                    </span>
                  )}
                  <span className="sr-only">
                    {field.label}
                    {rank ? `, ${rank.sr}` : ", not yet ranked"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        <Link
          href={`/agency/${item.slug}`}
          className="mt-auto flex min-h-[44px] items-center justify-between gap-2 border-t border-dashed border-paper-line text-[10.5px] font-bold uppercase tracking-[0.14em] text-coral-ink hover:underline"
        >
          <span className="truncate font-medium text-ink-3">
            {asOf ? `As of ${asOf.periodLabel} · ${item.currency}` : item.currency}
          </span>
          <span className="shrink-0">
            {hasData ? "Full data →" : "Request →"}
          </span>
        </Link>
      </div>
    </div>
  );
}
