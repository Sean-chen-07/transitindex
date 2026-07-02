import { describe, it, expect } from "vitest";
import { financialsToCsv } from "@/server/metrics/csv";
import type { FinancialsVM } from "@/server/metrics/detail-model";

const BOM = String.fromCharCode(0xfeff);

const FIN: FinancialsVM = {
  years: [
    { key: 2024, label: "FY2024 (Apr 2023, Mar 2024)" }, // comma -> must be quoted
    { key: 2025, label: "2025" },
  ],
  operations: [
    {
      code: "total_revenue_excluding_subsidy",
      label: "Fare & operating revenue",
      bold: false,
      indent: false,
      unit: "CAD",
      currency: "CAD",
      cells: [1234567.89, null], // null -> empty cell
    },
  ],
  position: [
    {
      code: "net_debt",
      label: 'Net "debt"', // embedded quotes -> doubled inside a quoted field
      bold: false,
      indent: false,
      unit: "CAD",
      currency: "CAD",
      cells: [null, -5],
    },
  ],
  hasFiscal: true,
};

describe("financialsToCsv", () => {
  it("golden string: BOM prefix, CRLF lines, RFC-4180 quoting, null -> empty", () => {
    const csv = financialsToCsv(FIN);
    expect(csv).toBe(
      BOM +
        'Section,Line,Unit,"FY2024 (Apr 2023, Mar 2024)",2025\r\n' +
        "Statement of Operations,Fare & operating revenue,CAD,1234567.89,\r\n" +
        'Statement of Financial Position,"Net ""debt""",CAD,,-5',
    );
  });

  it("starts with exactly one UTF-8 BOM character", () => {
    const csv = financialsToCsv(FIN);
    expect(csv.charCodeAt(0)).toBe(0xfeff);
    expect(csv.charCodeAt(1)).not.toBe(0xfeff);
  });
});
