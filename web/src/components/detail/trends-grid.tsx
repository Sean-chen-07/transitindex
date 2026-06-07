import { Fragment } from "react";
import { cn } from "@/lib/cn";
import { buildGridRows, type GridCell, type GridRow } from "./trend-grid-model";
import type { PaidMetricView } from "@/server/metrics/types";

/**
 * PAID surface — the per-agency calendar-year time-series grid (one dense spreadsheet per
 * metric). Reached ONLY on a revealed render (paid account OR demo), so the raw values it
 * prints never enter an anonymous payload. It reshapes the values already on
 * PaidMetricView.trend (no new raw-value query); month cells are raw readings, while the
 * Q / YTD / Year cells are DERIVED roll-ups — visually distinct and carrying the `°`
 * provenance marker. Server-rendered, no client JS.
 */
const nf = new Intl.NumberFormat("en-CA", { maximumFractionDigits: 2 });

function formatValue(value: number, unit: string): string {
  if (unit === "CAD") return `$${nf.format(value)}`;
  if (unit === "%") return `${nf.format(value)}%`;
  return nf.format(value);
}

// Month + quarter columns interleave M1 M2 M3 Q1 | … | Q4, then YTD, then Year.
const MONTH_GROUPS = [
  [0, 1, 2],
  [3, 4, 5],
  [6, 7, 8],
  [9, 10, 11],
] as const;

function Cell({ cell, unit }: { cell: GridCell | null | undefined; unit: string }) {
  if (!cell) return <span className="text-ink-3">—</span>;
  return (
    <span title={cell.periodLabel}>
      {formatValue(cell.value, unit)}
      {cell.derived && (
        <span aria-hidden className="ml-0.5 align-super text-[9px] text-coral">
          °
        </span>
      )}
    </span>
  );
}

function asOf(row: GridRow): string {
  // The most recent populated cell drives the per-row "as of".
  for (let i = 11; i >= 0; i--) {
    if (row.months[i]) return row.months[i]!.periodLabel;
  }
  return row.year_total?.periodLabel ?? row.ytd?.periodLabel ?? "—";
}

const TH = "px-2 py-1.5 text-right font-medium";
const DERIVED_CELL = "bg-coral-soft/40";

function MetricGrid({ metric }: { metric: PaidMetricView }) {
  const rows = buildGridRows(metric.trend);
  if (rows.length === 0) return null;

  return (
    <div className="mb-6">
      <h3 className="mb-2 text-sm font-semibold text-ink">{metric.displayName}</h3>
      <div className="overflow-x-auto rounded-cell border border-grid">
        <table className="w-full border-collapse text-xs">
          <caption className="sr-only">
            {metric.displayName}: monthly readings with derived quarter, year-to-date and
            full-year roll-ups, by calendar year.
          </caption>
          <thead>
            <tr className="border-b border-grid bg-card-2 text-ink-2">
              <th scope="col" className="px-2 py-1.5 text-left font-medium">
                Year
              </th>
              {MONTH_GROUPS.map((g, qi) => (
                <Fragment key={qi}>
                  {g.map((mi) => (
                    <th key={mi} scope="col" className={TH}>
                      M{mi + 1}
                    </th>
                  ))}
                  <th scope="col" className={cn(TH, DERIVED_CELL)}>
                    Q{qi + 1}
                  </th>
                </Fragment>
              ))}
              <th scope="col" className={cn(TH, DERIVED_CELL)}>
                YTD
              </th>
              <th scope="col" className={cn(TH, DERIVED_CELL)}>
                Year
              </th>
              <th scope="col" className="px-2 py-1.5 text-left font-medium">
                As of
              </th>
            </tr>
          </thead>
          <tbody className="tnum">
            {rows.map((row, ri) => (
              <tr key={row.year} className={cn("border-b border-grid/60", ri % 2 && "bg-card-2/40")}>
                <th scope="row" className="px-2 py-1.5 text-left font-normal text-ink">
                  {row.fiscal ? `FY${row.year}` : row.year}
                </th>
                {MONTH_GROUPS.map((g, qi) => (
                  <Fragment key={qi}>
                    {g.map((mi) => (
                      <td key={mi} className="px-2 py-1.5 text-right text-ink">
                        <Cell cell={row.months[mi]} unit={metric.unit} />
                      </td>
                    ))}
                    <td className={cn("px-2 py-1.5 text-right text-ink-2", DERIVED_CELL)}>
                      <Cell cell={row.quarters[qi]} unit={metric.unit} />
                    </td>
                  </Fragment>
                ))}
                <td className={cn("px-2 py-1.5 text-right text-ink-2", DERIVED_CELL)}>
                  <Cell cell={row.ytd} unit={metric.unit} />
                </td>
                <td className={cn("px-2 py-1.5 text-right font-medium text-ink", DERIVED_CELL)}>
                  <Cell cell={row.year_total} unit={metric.unit} />
                </td>
                <td className="px-2 py-1.5 text-left text-ink-3">{asOf(row)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function TrendsGrid({ metrics }: { metrics: PaidMetricView[] }) {
  const withTrend = metrics.filter((m) => m.trend.length > 0);
  if (withTrend.length === 0) {
    return (
      <p className="mt-4 text-sm text-ink-3">No time series recorded yet for this agency.</p>
    );
  }
  return (
    <section className="mt-6">
      <p className="mb-4 text-xs text-ink-3">
        Monthly readings, by calendar year. Cells marked{" "}
        <span aria-hidden className="text-coral">°</span> (Q / YTD / Year) are derived
        roll-ups of the monthly figures.
      </p>
      {withTrend.map((m) => (
        <MetricGrid key={m.metricCode} metric={m} />
      ))}
    </section>
  );
}
