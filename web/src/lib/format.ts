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
