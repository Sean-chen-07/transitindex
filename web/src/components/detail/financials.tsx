import type { ReactNode } from "react";
import { cn } from "@/lib/cn";
import { formatMetricValue } from "@/lib/format";
import type { FinancialsVM, StatementRowVM } from "@/server/metrics/detail-model";

/**
 * Tab 2 — the audited statements with every year as a column
 * (docs/design/detail-view-metrics.md §4). The one dense-spreadsheet surface left:
 * hairline grid, zebra rows, tabular numbers. A missing year is an em-dash, NEVER 0
 * (a 0 reads as "the agency collapsed").
 */

function StatementTable({
  title,
  note,
  years,
  rows,
}: {
  title: string;
  note?: string;
  years: FinancialsVM["years"];
  rows: StatementRowVM[];
}) {
  return (
    <div className="mt-6">
      <h3 className="text-xs font-semibold uppercase tracking-wide text-ink-3">{title}</h3>
      {note && <p className="mt-1 text-xs text-ink-3">{note}</p>}
      <div className="mt-2 overflow-x-auto rounded-cell border border-grid">
        <table className="w-full text-sm">
          <caption className="sr-only">
            {title}, one column per year, {years.length} years
          </caption>
          <thead>
            <tr className="border-b border-grid bg-card-2">
              <th scope="col" className="px-3 py-2 text-left font-medium text-ink-2">
                <span className="sr-only">Line item</span>
              </th>
              {years.map((y) => (
                <th
                  key={y.key}
                  scope="col"
                  className="tnum px-3 py-2 text-right font-medium text-ink-2"
                >
                  {y.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-grid">
            {rows.map((row) => (
              <tr key={row.code} className="odd:bg-card even:bg-card-2">
                <th
                  scope="row"
                  className={cn(
                    "whitespace-nowrap py-2 pr-3 text-left",
                    row.indent ? "pl-6" : "pl-3",
                    row.bold ? "font-semibold text-ink" : "font-normal text-ink",
                  )}
                >
                  {row.label}
                </th>
                {row.cells.map((v, i) => (
                  <td
                    key={years[i]?.key ?? i}
                    title={v == null ? undefined : String(v)}
                    className={cn(
                      "tnum whitespace-nowrap px-3 py-2 text-right text-ink",
                      row.bold && "font-semibold",
                    )}
                  >
                    {v == null ? (
                      <span className="text-ink-3">—</span>
                    ) : (
                      formatMetricValue(v, row.unit, row.currency, { compact: true })
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function Financials({
  financials,
  currency,
  downloadSlot,
}: {
  financials: FinancialsVM;
  /** The agency's reporting currency ("CAD" | "USD") — named once for the whole tab. */
  currency: string;
  downloadSlot: ReactNode;
}) {
  const currencyNote =
    currency === "USD"
      ? "All figures in US dollars (USD), as published."
      : "All figures in Canadian dollars (CAD), as published.";
  return (
    <section className="mt-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-ink">Financial statements</h2>
        {downloadSlot}
      </div>
      <p className="mt-1 text-xs text-ink-3">{currencyNote}</p>
      {financials.years.length === 0 ? (
        <p className="mt-4 rounded-card border border-dashed border-line-2 bg-card-2 p-4 text-sm text-ink-2">
          No financial statements sourced yet.
        </p>
      ) : (
        <>
          <StatementTable
            title="Revenue & expenses"
            note={
              "Capital spending is shown for reference only — it is not counted as an expense; the yearly wear on assets appears as amortization."
            }
            years={financials.years}
            rows={financials.operations}
          />
          {financials.hasFiscal && (
            <p className="mt-3 text-xs text-ink-3">
              Fiscal-year figures are shown under the calendar year the fiscal year ends in.
            </p>
          )}
        </>
      )}
    </section>
  );
}
