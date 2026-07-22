/**
 * READ TYPES for the `core` schema — the ingestion-written tables the web app reads.
 *
 * Mirrored by hand from the canonical contract in `db/schema.sql` (Lane 0). These are
 * READ types only: the web app never defines or migrates tables. `npm run db:pull`
 * (drizzle-kit introspect) regenerates this from the live schema once the
 * drizzle-kit/drizzle-orm versions are aligned; until then this hand-mirror is the
 * committed contract. Keep it in lockstep with db/schema.sql.
 *
 * NOTE: `core.pending_values` and `core.metric_value_audit` are deliberately OMITTED —
 * the web app has no free OR paid use for them (Lane-0 migration 008 will REVOKE the
 * web grant on them). Their absence here is the first line of the choke point.
 */
import {
  pgSchema,
  bigint,
  text,
  integer,
  smallint,
  numeric,
  boolean,
  date,
  timestamp,
} from "drizzle-orm/pg-core";

export const core = pgSchema("core");

export const agencies = core.table("agencies", {
  id: bigint("id", { mode: "number" }).primaryKey(),
  slug: text("slug").notNull(),
  legalName: text("legal_name").notNull(),
  shortName: text("short_name"),
  country: text("country").notNull(),
  subdivision: text("subdivision").notNull(),
  serviceAreaPopulation: integer("service_area_population"),
  primaryModes: text("primary_modes").array(),
  fiscalYearEndMonth: smallint("fiscal_year_end_month").notNull(),
  currency: text("currency").notNull(),
  ntdId: text("ntd_id"),
  parentAgencyId: bigint("parent_agency_id", { mode: "number" }),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull(),
});

export const modes = core.table("modes", {
  id: bigint("id", { mode: "number" }).primaryKey(),
  code: text("code").notNull(),
  displayName: text("display_name").notNull(),
  description: text("description"),
});

export const agencyModes = core.table("agency_modes", {
  agencyId: bigint("agency_id", { mode: "number" }).notNull(),
  modeId: bigint("mode_id", { mode: "number" }).notNull(),
  yearStarted: smallint("year_started"),
  status: text("status").notNull(),
});

export const metrics = core.table("metrics", {
  id: bigint("id", { mode: "number" }).primaryKey(),
  code: text("code").notNull(),
  displayName: text("display_name").notNull(),
  description: text("description"),
  unit: text("unit").notNull(),
  unitType: text("unit_type"),
  applicableModes: text("applicable_modes").array(),
  isDerived: boolean("is_derived").notNull(),
  formula: text("formula"),
  higherIsBetter: boolean("higher_is_better"),
  cutaReference: text("cuta_reference"),
  ntdReference: text("ntd_reference"),
});

export const reportingPeriods = core.table("reporting_periods", {
  // Shared across agencies (migration 009): identity is (period_type, start_date,
  // end_date), so one row per calendar period serves every agency's values + ranks.
  id: bigint("id", { mode: "number" }).primaryKey(),
  periodType: text("period_type").notNull(),
  startDate: date("start_date").notNull(),
  endDate: date("end_date").notNull(),
  label: text("label").notNull(),
});

export const metricRanks = core.table("metric_ranks", {
  id: bigint("id", { mode: "number" }).primaryKey(),
  agencyId: bigint("agency_id", { mode: "number" }).notNull(),
  metricId: bigint("metric_id", { mode: "number" }).notNull(),
  reportingPeriodId: bigint("reporting_period_id", { mode: "number" }).notNull(),
  comparisonSet: text("comparison_set").notNull(),
  rank: integer("rank"),
  denominator: integer("denominator"),
  direction: text("direction"),
  computedAt: timestamp("computed_at", { withTimezone: true }).notNull(),
});

/**
 * RAW VALUES — paid-tier only. This table object must be imported ONLY by
 * src/server/metrics/queries.ts (the single value-bearing query module). The ESLint
 * no-restricted-imports rule guards the queries module; treat this export the same.
 */
export const metricValues = core.table("metric_values", {
  id: bigint("id", { mode: "number" }).primaryKey(),
  agencyId: bigint("agency_id", { mode: "number" }).notNull(),
  metricId: bigint("metric_id", { mode: "number" }).notNull(),
  reportingPeriodId: bigint("reporting_period_id", { mode: "number" }).notNull(),
  modeId: bigint("mode_id", { mode: "number" }),
  serviceScope: text("service_scope").notNull(),
  value: numeric("value").notNull(),
  unit: text("unit").notNull(),
  currency: text("currency"),
  quality: text("quality").notNull(),
  comparableFlag: boolean("comparable_flag").notNull(),
  crosscheckValue: numeric("crosscheck_value"),
  crosscheckSourceDocumentId: bigint("crosscheck_source_document_id", { mode: "number" }),
  restatementOfId: bigint("restatement_of_id", { mode: "number" }),
  isCurrent: boolean("is_current").notNull(),
  notes: text("notes"),
  // Accounting basis of an expense value: 'operating' (amortization-excluded) |
  // 'psab_total' (amortization-included). Migration 020. Introspection only —
  // never migrated from here (web/CLAUDE.md).
  costBasis: text("cost_basis").notNull(),
  createdAt: timestamp("created_at", { withTimezone: true }).notNull(),
  updatedAt: timestamp("updated_at", { withTimezone: true }).notNull(),
});

export const metricValueSources = core.table("metric_value_sources", {
  metricValueId: bigint("metric_value_id", { mode: "number" }).notNull(),
  sourceDocumentId: bigint("source_document_id", { mode: "number" }).notNull(),
  pageNumber: integer("page_number"),
  tableReference: text("table_reference"),
  extractionMethod: text("extraction_method"),
  confidence: numeric("confidence"),
});

export const sourceDocuments = core.table("source_documents", {
  id: bigint("id", { mode: "number" }).primaryKey(),
  agencyId: bigint("agency_id", { mode: "number" }),
  documentType: text("document_type").notNull(),
  title: text("title"),
  publicationDate: date("publication_date"),
  sourceUrl: text("source_url"),
  archiveUri: text("archive_uri"),
  fileHash: text("file_hash"),
  license: text("license"),
  retrievedAt: timestamp("retrieved_at", { withTimezone: true }),
  verifiedAt: timestamp("verified_at", { withTimezone: true }),
  verifiedBy: text("verified_by"),
});

export const sourceFeeds = core.table("source_feeds", {
  id: bigint("id", { mode: "number" }).primaryKey(),
  code: text("code").notNull(),
  displayName: text("display_name").notNull(),
  tier: smallint("tier"),
  expectedCadence: text("expected_cadence"),
  enabled: boolean("enabled").notNull(),
});

export const feedRuns = core.table("feed_runs", {
  id: bigint("id", { mode: "number" }).primaryKey(),
  feedId: bigint("feed_id", { mode: "number" }).notNull(),
  startedAt: timestamp("started_at", { withTimezone: true }),
  finishedAt: timestamp("finished_at", { withTimezone: true }),
  status: text("status"),
  rowsFetched: integer("rows_fetched"),
  schemaFingerprint: text("schema_fingerprint"),
  lastGoodAt: timestamp("last_good_at", { withTimezone: true }),
  message: text("message"),
});
