/**
 * Free-path return types for the read-data layer. By construction NONE of these
 * carries a raw metric `value` — the only place a raw number exists is PaidMetricView
 * in @/server/metrics/types, produced exclusively by the server-only choke point.
 */

export type RankStatus =
  | "ranked"
  | "not_yet_ranked"
  | "not_ranked_period_miss"
  | "pending";

export interface AgencyRank {
  metricCode: string;
  metricDisplayName: string;
  unitType: string | null;
  higherIsBetter: boolean | null;
  comparisonSet: "all";
  status: RankStatus;
  rank: number | null;
  denominator: number | null;
  periodLabel: string | null;
  periodEnd: string | null;
  computedAt: string | null;
  // NO `value`.
}

export interface AgencyListItem {
  slug: string;
  shortName: string | null;
  legalName: string;
  subdivision: string;
  primaryModes: string[];
  hasAnyRank: boolean;
}

export interface AgencyListGroup {
  subdivision: string; // province code
  provinceName: string; // full name for the civic audience
  agencies: AgencyListItem[];
}

export interface AgencySummary {
  id: number;
  slug: string;
  shortName: string | null;
  legalName: string;
  subdivision: string;
  provinceName: string;
  primaryModes: string[];
  modes: { code: string; displayName: string }[];
}

export interface Attribution {
  title: string | null;
  sourceUrl: string | null;
  license: string | null;
  publicationDate: string | null;
  retrievedAt: string | null;
}

export interface FeedFreshness {
  code: string;
  displayName: string;
  status: string | null;
  lastGoodAt: string | null;
  expectedCadence: string | null;
}
