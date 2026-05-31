import { rankLabel, srRankLabel } from "@/lib/format";
import type { PaidMetricView } from "@/server/metrics/types";

/**
 * PAID surface — the dense financial-statement table. Reached ONLY when the choke
 * point revealed numbers (paid account OR the demo agency), so raw values here never
 * enter an anonymous render. Server-rendered (no client JS); the sparkline is inline
 * SVG with a text alternative (WCAG).
 */
const nf = new Intl.NumberFormat("en-CA", { maximumFractionDigits: 2 });

function formatValue(value: number, unit: string): string {
  if (unit === "CAD") return `$${nf.format(value)}`;
  if (unit === "%") return `${nf.format(value)}%`;
  return `${nf.format(value)} ${unit}`.trim();
}

function Sparkline({ trend }: { trend: PaidMetricView["trend"] }) {
  if (trend.length < 2) return <span className="text-ink-3">—</span>;
  const values = trend.map((t) => t.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const w = 80;
  const h = 22;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - ((v - min) / span) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const first = values[0]!;
  const last = values[values.length - 1]!;
  const pct = first === 0 ? 0 : ((last - first) / Math.abs(first)) * 100;
  const alt = `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}% over ${values.length} periods`;
  return (
    <span title={alt}>
      <span className="sr-only">{alt}</span>
      <svg aria-hidden width={w} height={h} className="overflow-visible">
        <polyline points={pts} fill="none" stroke="var(--teal)" strokeWidth="1.5" />
      </svg>
    </span>
  );
}

export function Spreadsheet({ metrics }: { metrics: PaidMetricView[] }) {
  return (
    <section className="mt-8">
      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-2">
        Full data
      </h2>
      <div className="overflow-x-auto rounded-cell border border-grid">
        <table className="w-full border-collapse text-sm">
          <caption className="sr-only">Sourced metrics for this agency.</caption>
          <thead>
            <tr className="border-b border-grid bg-card-2 text-left text-ink-2">
              <th scope="col" className="px-3 py-2 font-medium">Metric</th>
              <th scope="col" className="px-3 py-2 text-right font-medium">Value</th>
              <th scope="col" className="px-3 py-2 text-right font-medium">Rank</th>
              <th scope="col" className="px-3 py-2 font-medium">As of</th>
              <th scope="col" className="px-3 py-2 font-medium">Trend</th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m, i) => {
              const ord = rankLabel({ rank: m.rank, denominator: m.denominator });
              return (
                <tr key={m.metricCode} className={i % 2 ? "bg-card-2/40" : ""}>
                  <th scope="row" className="px-3 py-2 text-left font-normal text-ink">
                    {m.displayName}
                  </th>
                  <td className="px-3 py-2 text-right tnum font-medium text-ink">
                    {formatValue(m.value, m.unit)}
                  </td>
                  <td className="px-3 py-2 text-right tnum text-ink-2">
                    <span className="sr-only">
                      {srRankLabel({ rank: m.rank, denominator: m.denominator })}
                    </span>
                    <span aria-hidden className={ord === "not yet ranked" ? "italic text-ink-3" : ""}>
                      {ord}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-ink-2">{m.periodLabel || "—"}</td>
                  <td className="px-3 py-2">
                    <Sparkline trend={m.trend} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
