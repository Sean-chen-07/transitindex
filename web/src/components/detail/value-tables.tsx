import { formatMetricValue } from "@/lib/format";
import type { ValueRowVM } from "@/server/metrics/detail-model";

/**
 * The two compact value lists under the heroes (docs/design/detail-view-metrics.md
 * §§3.2–3.3): current value only — no charts, no history, no rank badges. Each row
 * carries its own as-of period label (per-metric period, never a page-level stamp).
 */

function MiniTable({ heading, rows }: { heading: string; rows: ValueRowVM[] }) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-3">{heading}</h3>
      <table className="mt-2 w-full text-sm">
        <caption className="sr-only">{heading} — current values</caption>
        <tbody>
          {rows.map((r) => (
            <tr key={r.code} className="border-t border-line-2 first:border-t-0">
              <th scope="row" className="py-2 pr-3 text-left font-normal text-ink">
                {r.label}
              </th>
              <td className="tnum py-2 text-right font-medium text-ink">
                {r.value == null ? (
                  <span className="text-ink-3">—</span>
                ) : (
                  <>
                    {formatMetricValue(r.value, r.unit, r.currency, { compact: true })}
                    {r.asOfLabel && (
                      <span className="ml-1.5 text-[10px] font-normal text-ink-3">
                        {r.asOfLabel}
                      </span>
                    )}
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ValueTables({
  ratios,
  serviceFleet,
}: {
  ratios: ValueRowVM[];
  serviceFleet: ValueRowVM[];
}) {
  return (
    <div className="mt-8 grid gap-6 sm:grid-cols-2">
      <MiniTable heading="Efficiency ratios" rows={ratios} />
      <MiniTable heading="Service & fleet" rows={serviceFleet} />
    </div>
  );
}
