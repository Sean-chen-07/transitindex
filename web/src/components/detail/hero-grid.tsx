"use client";

import * as React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";
import { cn } from "@/lib/cn";
import { formatMetricValue, formatYoy, rankLabel, srRankLabel } from "@/lib/format";
import type { HeroVM } from "@/server/metrics/detail-model";
import type { SeriesPoint } from "@/server/metrics/types";

/**
 * The six hero boxes (docs/design/detail-view-metrics.md §3.1) in rows of 3, each a
 * button that drops an accordion history chart beneath its row (one open at a time).
 * Arrows are NEUTRAL direction-only (never green/red — the no-grade invariant), and
 * chart gaps stay gaps: a missing interior period is a null, never interpolated (§5).
 * HeroVM is plain serializable data shaped server-side; nothing is computed from the DB here.
 */

const GLYPH: Record<"up" | "down" | "flat", string> = { up: "▲", down: "▼", flat: "—" };

interface ChartPoint {
  label: string;
  value: number | null;
}

function endYear(p: SeriesPoint): number {
  return Number(p.endDate.slice(0, 4));
}

/** One slot per year first→last; a missing interior year is a null (the line BREAKS). */
function annualWithGaps(points: SeriesPoint[]): ChartPoint[] {
  const byYear = new Map<number, SeriesPoint>();
  for (const p of points) byYear.set(endYear(p), p);
  const years = [...byYear.keys()].sort((a, b) => a - b);
  const first = years[0];
  const last = years[years.length - 1];
  if (first === undefined || last === undefined) return [];
  const out: ChartPoint[] = [];
  for (let y = first; y <= last; y++) {
    const p = byYear.get(y);
    out.push({ label: p?.periodLabel ?? String(y), value: p?.value ?? null });
  }
  return out;
}

/** Same gap rule month-by-month. */
function monthlyWithGaps(points: SeriesPoint[]): ChartPoint[] {
  const keyOf = (p: SeriesPoint) => endYear(p) * 12 + (Number(p.endDate.slice(5, 7)) - 1);
  const byMonth = new Map<number, SeriesPoint>();
  for (const p of points) byMonth.set(keyOf(p), p);
  const keys = [...byMonth.keys()].sort((a, b) => a - b);
  const first = keys[0];
  const last = keys[keys.length - 1];
  if (first === undefined || last === undefined) return [];
  const out: ChartPoint[] = [];
  for (let k = first; k <= last; k++) {
    const p = byMonth.get(k);
    out.push({
      label: p?.periodLabel ?? `${Math.floor(k / 12)}-${String((k % 12) + 1).padStart(2, "0")}`,
      value: p?.value ?? null,
    });
  }
  return out;
}

/** Text alternative for the chart: first-vs-last, e.g. "+4.1% over 5 years". */
function trendSentence(points: SeriesPoint[]): string {
  const first = points[0];
  const last = points[points.length - 1];
  if (!first || !last || first === last) return "Not enough history for a trend.";
  if (first.value === 0) return `From ${first.periodLabel} to ${last.periodLabel}.`;
  const pct = ((last.value - first.value) / Math.abs(first.value)) * 100;
  const signed = `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
  const span = endYear(last) - endYear(first);
  if (span >= 1) return `${signed} over ${span} year${span === 1 ? "" : "s"}`;
  return `${signed} from ${first.periodLabel} to ${last.periodLabel}`;
}

function HeroBox({
  hero,
  open,
  onToggle,
}: {
  hero: HeroVM;
  open: boolean;
  onToggle: () => void;
}) {
  const ordinal = rankLabel(hero);
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-expanded={open}
      aria-controls={open ? `hero-chart-${hero.code}` : undefined}
      className={cn(
        "min-h-[44px] rounded-card border border-line bg-card p-4 text-left shadow-soft transition-shadow hover:shadow-soft-hover",
        open && "border-teal",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-[10px] uppercase leading-tight tracking-wide text-ink-3">
          {hero.label}
        </span>
        {ordinal === "not yet ranked" ? (
          <span className="shrink-0 text-xs italic text-ink-3">not yet ranked</span>
        ) : (
          <span className="tnum shrink-0 rounded-full bg-card-2 px-2 py-0.5 text-xs font-medium text-ink-2">
            <span aria-hidden>{ordinal}</span>
            <span className="sr-only">{srRankLabel(hero)}</span>
          </span>
        )}
      </div>
      <div className="tnum mt-2 text-2xl font-bold leading-none text-ink">
        {hero.value == null ? (
          <span className="text-base font-medium italic text-ink-3">— not yet sourced</span>
        ) : (
          formatMetricValue(hero.value, hero.unit, hero.currency, { compact: true })
        )}
      </div>
      {/* Direction only — one neutral ink, never green/red (rank direction is NEUTRAL). */}
      <div className="tnum mt-2 text-sm text-ink-2">
        {hero.yoy ? (
          <>
            <span aria-hidden>{GLYPH[hero.yoy.direction]}</span>
            <span className="sr-only">{hero.yoy.direction}</span>{" "}
            {formatYoy(hero.yoy.pct)} vs {hero.yoy.vsLabel}
          </>
        ) : (
          <span className="text-ink-3">—</span>
        )}
      </div>
    </button>
  );
}

function HeroChart({ hero }: { hero: HeroVM }) {
  const hasMonthly = hero.monthly.length > 1;
  const [view, setView] = React.useState<"yearly" | "monthly">("yearly");
  const showMonthly = hasMonthly && (view === "monthly" || hero.annual.length === 0);
  const source = showMonthly ? hero.monthly : hero.annual;
  const data = showMonthly ? monthlyWithGaps(hero.monthly) : annualWithGaps(hero.annual);
  const useBars = !showMonthly && hero.annual.length <= 4;

  const fmt = (v: number) => formatMetricValue(v, hero.unit, hero.currency, { compact: true });
  const tick = { fontSize: 11, fill: "var(--ink-3)" };
  const margin = { top: 8, right: 8, bottom: 0, left: 0 };
  const tooltipProps = {
    // Param matches recharts' ValueType (arrays/undefined never occur for one series).
    formatter: (v: number | string | readonly (number | string)[] | undefined) => fmt(Number(v)),
    contentStyle: {
      borderRadius: 12,
      border: "1px solid var(--line)",
      background: "var(--card)",
      fontSize: 12,
    },
  };

  const first = source[0];
  const last = source[source.length - 1];

  return (
    <div
      id={`hero-chart-${hero.code}`}
      role="region"
      aria-label={`${hero.label} history`}
      className="tnum mt-3 rounded-card border border-line bg-card p-4 shadow-soft"
    >
      {hasMonthly && hero.annual.length > 0 && (
        <div className="mb-2 inline-flex rounded-full border border-line bg-card-2 p-0.5">
          {(["yearly", "monthly"] as const).map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={view === v}
              onClick={() => setView(v)}
              className={cn(
                "min-h-[44px] rounded-full px-4 text-xs font-medium transition-colors",
                view === v ? "bg-card text-ink shadow-soft" : "text-ink-3 hover:text-ink-2",
              )}
            >
              {v === "yearly" ? "Yearly" : "Monthly"}
            </button>
          ))}
        </div>
      )}
      {data.length === 0 ? (
        <p className="text-sm italic text-ink-3">No history to chart yet.</p>
      ) : (
        <>
          <ResponsiveContainer width="100%" height={220}>
            {useBars ? (
              <BarChart data={data} margin={margin}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="label" tick={tick} tickLine={false} axisLine={{ stroke: "var(--grid)" }} />
                <YAxis tick={tick} tickLine={false} axisLine={false} tickFormatter={fmt} width={64} />
                <Tooltip {...tooltipProps} cursor={{ fill: "var(--card-2)" }} />
                <Bar dataKey="value" fill="var(--teal)" radius={[4, 4, 0, 0]} maxBarSize={48} />
              </BarChart>
            ) : (
              <LineChart data={data} margin={margin}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis
                  dataKey="label"
                  tick={tick}
                  tickLine={false}
                  axisLine={{ stroke: "var(--grid)" }}
                  minTickGap={24}
                  interval="preserveStartEnd"
                />
                <YAxis tick={tick} tickLine={false} axisLine={false} tickFormatter={fmt} width={64} />
                <Tooltip {...tooltipProps} cursor={{ stroke: "var(--grid)" }} />
                {/* connectNulls=false: a missing period is a BREAK in the line, never a bridge. */}
                <Line
                  dataKey="value"
                  stroke="var(--teal)"
                  strokeWidth={2}
                  dot={{ r: 2.5, fill: "var(--teal)", strokeWidth: 0 }}
                  connectNulls={false}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
          <p className="sr-only">{trendSentence(source)}</p>
          {first && last && (
            <p aria-hidden className="mt-2 text-xs text-ink-3">
              {first.periodLabel} – {last.periodLabel}
            </p>
          )}
        </>
      )}
    </div>
  );
}

export function HeroGrid({ heroes }: { heroes: HeroVM[] }) {
  const [open, setOpen] = React.useState<string | null>(null);
  const rows: HeroVM[][] = [];
  for (let i = 0; i < heroes.length; i += 3) rows.push(heroes.slice(i, i + 3));

  return (
    <div className="mt-6">
      {/* Comparison set named ONCE per page (DESIGN.md rank-display rule). */}
      <p className="text-xs text-ink-3">Ranked vs all Canadian transit agencies.</p>
      {rows.map((row, i) => {
        const openHero = row.find((h) => h.code === open);
        return (
          <React.Fragment key={row[0]?.code ?? i}>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {row.map((h) => (
                <HeroBox
                  key={h.code}
                  hero={h}
                  open={open === h.code}
                  onToggle={() => setOpen(open === h.code ? null : h.code)}
                />
              ))}
            </div>
            {openHero && <HeroChart key={openHero.code} hero={openHero} />}
          </React.Fragment>
        );
      })}
    </div>
  );
}
