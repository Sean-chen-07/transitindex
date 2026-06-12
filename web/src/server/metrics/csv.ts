import type { FinancialsVM, StatementRowVM } from "./detail-model";

/**
 * The paid artifact: the Financials grid as RFC-4180 CSV. Values are RAW unformatted
 * numbers; a missing year is an empty cell, never 0. UTF-8 BOM + CRLF so Excel opens
 * it cleanly. Pure (no DB) so the layout is golden-string tested (csv.test.ts).
 */

function escapeField(field: string): string {
  return /[",\r\n]/.test(field) ? `"${field.replace(/"/g, '""')}"` : field;
}

function rowFields(section: string, row: StatementRowVM): string[] {
  return [section, row.label, row.unit, ...row.cells.map((c) => (c == null ? "" : String(c)))];
}

export function financialsToCsv(fin: FinancialsVM): string {
  const lines: string[][] = [
    ["Section", "Line", "Unit", ...fin.years.map((y) => y.label)],
    ...fin.operations.map((r) => rowFields("Statement of Operations", r)),
    ...fin.position.map((r) => rowFields("Statement of Financial Position", r)),
  ];
  // U+FEFF byte-order mark (built via fromCharCode so no invisible char lives in source).
  const bom = String.fromCharCode(0xfeff);
  return bom + lines.map((fields) => fields.map(escapeField).join(",")).join("\r\n");
}
