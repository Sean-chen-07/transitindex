/**
 * Pure rendering helpers. The rank helpers are LOAD-BEARING for rank safety:
 * core.metric_ranks.rank / denominator / direction are all nullable with no CHECK,
 * and the Lane A rank job does not suppress small pools (db/migrations/005:34
 * "no minimum pool needed"). So this is the PRIMARY guard against "1st of 2" and
 * "nullth", not a mirror of something the DB enforces.
 */

/** Minimum cohort size before a rank is shown. Below this -> "not yet ranked". */
export const MIN_DENOMINATOR = 5;

const PROVINCE_NAMES: Record<string, string> = {
  AB: "Alberta",
  BC: "British Columbia",
  MB: "Manitoba",
  NB: "New Brunswick",
  NL: "Newfoundland and Labrador",
  NS: "Nova Scotia",
  NT: "Northwest Territories",
  NU: "Nunavut",
  ON: "Ontario",
  PE: "Prince Edward Island",
  QC: "Quebec",
  SK: "Saskatchewan",
  YT: "Yukon",
};

/** Full province name for the civic audience; falls back to the code, then "Other". */
export function provinceName(code: string | null | undefined): string {
  if (!code) return "Other";
  return PROVINCE_NAMES[code] ?? code;
}

/** 1 -> "1st", 2 -> "2nd", 3 -> "3rd", 4 -> "4th", 11/12/13 -> "th". */
export function toOrdinal(n: number): string {
  const abs = Math.abs(Math.trunc(n));
  const mod100 = abs % 100;
  const mod10 = abs % 10;
  let suffix = "th";
  if (mod100 < 11 || mod100 > 13) {
    if (mod10 === 1) suffix = "st";
    else if (mod10 === 2) suffix = "nd";
    else if (mod10 === 3) suffix = "rd";
  }
  return `${abs}${suffix}`;
}

export interface RankInput {
  rank: number | null;
  denominator: number | null;
}

/**
 * The defensive render gate. Returns an ordinal ("3rd") ONLY when the rank is safe
 * to show; otherwise "not yet ranked". Short-circuits on null/zero/below-min/out-of-range
 * BEFORE any formatting, so "nullth" and "rank of " can never render.
 */
export function rankLabel(
  { rank, denominator }: RankInput,
  minDenominator: number = MIN_DENOMINATOR,
): string {
  if (
    rank == null ||
    denominator == null ||
    denominator === 0 ||
    denominator < minDenominator ||
    rank < 1 ||
    rank > denominator
  ) {
    return "not yet ranked";
  }
  return toOrdinal(rank);
}

/** Screen-reader label: "ranked 3rd of 10", or "not yet ranked" when suppressed. */
export function srRankLabel(
  input: RankInput,
  minDenominator: number = MIN_DENOMINATOR,
): string {
  const label = rankLabel(input, minDenominator);
  if (label === "not yet ranked") return label;
  return `ranked ${label} of ${input.denominator}`;
}

/** Compact notation only kicks in at this magnitude ($1.42B, 521M — never "4.8K buses"). */
const COMPACT_MIN = 100_000;

const compactNum = new Intl.NumberFormat("en-CA", {
  notation: "compact",
  maximumFractionDigits: 2,
});

function plainNumber(value: number, maxDp = 2): string {
  return new Intl.NumberFormat("en-CA", { maximumFractionDigits: maxDp }).format(value);
}

function generalNumber(value: number, compact: boolean): string {
  return compact && Math.abs(value) >= COMPACT_MIN
    ? compactNum.format(value)
    : plainNumber(value);
}

/** "$1.42B" compact, else "$4.60" / "$85,000" (2dp shown only when fractional). */
function cad(value: number, compact: boolean): string {
  const sign = value < 0 ? "-" : "";
  const abs = Math.abs(value);
  if (compact && abs >= COMPACT_MIN) return `${sign}$${compactNum.format(abs)}`;
  const dp = Number.isInteger(abs) ? 0 : 2;
  const plain = new Intl.NumberFormat("en-CA", {
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  }).format(abs);
  return `${sign}$${plain}`;
}

/**
 * One display formatter per metric unit (docs/design/detail-view-metrics.md §2 examples).
 * `currency` rides along for the signature contract (only CAD exists today, so the unit
 * alone decides the symbol). Pass { compact: true } for headline / table-cell rendering.
 */
export function formatMetricValue(
  value: number,
  unit: string,
  currency: string | null,
  opts?: { compact?: boolean },
): string {
  void currency;
  const compact = opts?.compact ?? false;
  switch (unit) {
    case "CAD":
      return cad(value, compact);
    case "%":
      return `${plainNumber(value, 1)}%`;
    case "count":
      return generalNumber(value, compact);
    case "hours":
      return `${generalNumber(value, compact)} hrs`;
    case "km":
      return `${generalNumber(value, compact)} km`;
    case "years":
      return `${value.toFixed(1)} yrs`;
    case "CAD/hr":
      return `$${plainNumber(value)}/hr`;
    case "trips/hr":
      return plainNumber(value, 1);
    default:
      return unit ? `${plainNumber(value)} ${unit}` : plainNumber(value);
  }
}

/** "4.2%" — absolute value, 1dp; the neutral arrow glyph carries the sign, not the text. */
export function formatYoy(pct: number): string {
  return `${Math.abs(pct).toFixed(1)}%`;
}
