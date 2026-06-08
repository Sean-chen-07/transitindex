"""The abstract write/read interface every pipeline component codes against.

`Repository` is a typing.Protocol: both `InMemoryRepository` (tests) and
`PostgresRepository` (production) satisfy it structurally. The method set
covers the full ingestion path -- id resolution, period/document upsert,
staging into core.pending_values, promotion into core.metric_values honoring
the one-current-value invariant, the derived-metric write path, cohort reads
for ranking, rank materialization, and feed-run bookkeeping.

Invariants the implementations MUST uphold:
  - one_current_value: at most ONE is_current row per
    (agency_id, metric_id, reporting_period_id, mode_id, service_scope), with
    mode_id None treated as a concrete key part (NULLS NOT DISTINCT).
  - supersede chain: writing a new current value flips the prior current row to
    is_current=False and points the new row's restatement_of_id at it.
  - audit: every metric_values insert/update appends a core.metric_value_audit
    entry (change_type 'insert'/'update', old_value/new_value).
  - staging door: an unreviewed value NEVER reaches metric_values; promotion
    flips the pending row to review_status='approved'.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional, Protocol, runtime_checkable

from ..contract import MetricValueRecord, SourceRef
from .models import (
    Document,
    Metric,
    MetricRankRow,
    MetricValue,
    PendingValue,
    ReportingPeriod,
    SourceDocument,
    BulkPendingRow,
    BulkPromoteResult,
    BulkMetricRankRow,
)


@runtime_checkable
class Repository(Protocol):
    """Write/read surface for the ingestion pipeline against the core schema."""

    # --- id resolution -------------------------------------------------------

    def agency_id(self, slug: str) -> int:
        """Resolve an agency slug to its core.agencies id (raise if unknown)."""
        ...

    def metric_id(self, code: str) -> int:
        """Resolve a metric code to its core.metrics id (raise if unknown)."""
        ...

    def mode_id(self, code: Optional[str]) -> Optional[int]:
        """Resolve a mode code to its id; None passes through as None."""
        ...

    def feed_id(self, code: str) -> int:
        """Resolve a source-feed code to its core.source_feeds id (raise if unknown)."""
        ...

    def list_metrics(self) -> list[Metric]:
        """Return all core.metrics rows."""
        ...

    def agency_population(self, agency_id: int) -> Optional[Decimal]:
        """The agency's static service_area_population, or None if unknown.
        Used as the read-only denominator for net_debt_per_capita."""
        ...

    # --- period & document upsert -------------------------------------------

    def get_or_create_reporting_period(
        self,
        period_type: str,
        start_date,
        end_date,
        label: str,
    ) -> int:
        """Return the id of the matching core.reporting_periods row, creating it
        if absent. Identity is (period_type, start_date, end_date) — periods are
        shared across agencies (migration 009)."""
        ...

    def get_or_create_source_document(self, source: SourceRef, agency_id: Optional[int]) -> int:
        """Return the id of the core.source_documents row for `source`, creating
        it if absent. Identity is (source_url, document_type) when a url exists,
        else a per-document new row."""
        ...

    # --- document catalog (core.documents) ----------------------------------

    def upsert_document(
        self,
        *,
        agency_id: int,
        year: int,
        doc_type: str,
        author_label: str,
        storage_key: str,
        source_url: Optional[str] = None,
        file_hash: Optional[str] = None,
        file_bytes: Optional[int] = None,
    ) -> int:
        """Insert or update a core.documents catalog row; return its id.

        Identity is storage_key (one row per stored file). On a re-upload the
        hash/size/source_url refresh in place; scan_status is NOT reset here."""
        ...

    def list_documents(self, status: Optional[str] = None) -> list[Document]:
        """List catalog rows, optionally filtered by scan_status, newest queue
        first (unscanned before scanned), then by agency/year."""
        ...

    def get_document(self, document_id: int) -> Optional[Document]:
        """Fetch one core.documents row by id, or None."""
        ...

    def mark_document_scanned(
        self, document_id: int, *, source_document_id: Optional[int], staged_count: int
    ) -> None:
        """Flip a catalog row to scan_status='scanned', recording the linked
        source_documents row and how many pending values the scan staged."""
        ...

    def mark_document_failed(self, document_id: int, *, error: str) -> None:
        """Flip a catalog row to scan_status='failed' with the error message."""
        ...

    # --- staging (core.pending_values) --------------------------------------

    def insert_pending_value(
        self,
        record: MetricValueRecord,
        source_document_id: Optional[int],
        review_status: str = "pending",
        flags: Optional[list[str]] = None,
    ) -> int:
        """Insert a core.pending_values row from `record`; return its id.
        This is the only door to metric_values -- nothing else writes there."""
        ...

    def list_pending_values(self, status: Optional[str] = None) -> list[PendingValue]:
        """List pending rows, optionally filtered by review_status."""
        ...

    def get_pending_value(self, pending_id: int) -> Optional[PendingValue]:
        """Fetch one core.pending_values row by id, or None."""
        ...

    def update_pending(
        self,
        pending_id: int,
        value: Optional[Decimal] = None,
        review_status: Optional[str] = None,
        reviewer_notes: Optional[str] = None,
    ) -> None:
        """Update a pending row's value / review_status / reviewer_notes
        (only the provided fields)."""
        ...

    # --- current-value reads -------------------------------------------------

    def list_reporting_periods(self) -> list[ReportingPeriod]:
        """All core.reporting_periods rows, ordered by start_date. Periods are
        shared across agencies (migration 009); the workbook export pairs each
        with an agency's own values via list_current_values_for_agency_period."""
        ...

    def get_current_metric_value(
        self,
        agency_id: int,
        metric_id: int,
        period_id: int,
        mode_id: Optional[int],
        service_scope: str,
    ) -> Optional[MetricValue]:
        """Return the single is_current metric value for the tuple, or None."""
        ...

    def list_current_values_for_metric_period(
        self, metric_id: int, period_id: int
    ) -> list[MetricValue]:
        """All is_current values for a metric in a period (the ranking cohort)."""
        ...

    def list_current_values_for_agency_period(
        self, agency_id: int, period_id: int
    ) -> list[MetricValue]:
        """All is_current values for an agency in a period (derived-metric inputs)."""
        ...

    # --- promotion & direct writes (core.metric_values) ---------------------

    def promote_pending(self, pending_id: int) -> int:
        """Promote a pending row into core.metric_values and return the new
        metric_value id. Honors one_current_value (supersedes any existing
        current row via restatement_of_id + is_current=False on the old one),
        inserts the core.metric_value_sources link, records an audit entry, and
        sets the pending row's review_status='approved'."""
        ...

    def insert_metric_value(
        self,
        agency_id: int,
        metric_id: int,
        reporting_period_id: int,
        mode_id: Optional[int],
        service_scope: str,
        value: Decimal,
        unit: str,
        quality: str,
        currency: Optional[str] = None,
        comparable_flag: bool = True,
        crosscheck_value: Optional[Decimal] = None,
        notes: Optional[str] = None,
    ) -> int:
        """Insert a metric value directly (used by the derived-metric job),
        with the SAME one-current/supersede/restatement semantics as
        promote_pending and an audit entry. Returns the new metric_value id."""
        ...

    def insert_derived_value(
        self,
        agency_id: int,
        metric_id: int,
        reporting_period_id: int,
        mode_id: Optional[int],
        service_scope: str,
        value: Decimal,
        unit: str,
        quality: str,
        equation_code: str,
        input_value_ids: list[int],
        currency: Optional[str] = None,
        comparable_flag: bool = True,
        notes: Optional[str] = None,
    ) -> int:
        """Insert a SOLVED (derived) metric value with the same one-current/
        supersede/audit semantics as insert_metric_value, AND record its
        derivation provenance: `equation_code` plus the exact `input_value_ids`
        (the metric_value rows it was computed from). A derived value is thus a
        citation tree bottoming out in sourced+cited rows -- dispute-proof.
        Returns the new metric_value id."""
        ...

    def get_derivation(self, metric_value_id: int) -> Optional[dict]:
        """Return the derivation for a value as
        {'equation_code': str, 'input_value_ids': list[int]}, or None if the
        value was sourced (no derivation row)."""
        ...

    # --- ranking & feed bookkeeping -----------------------------------------

    def replace_metric_ranks(
        self,
        metric_id: int,
        period_id: int,
        comparison_set: str,
        rows: list[MetricRankRow],
    ) -> None:
        """Replace all core.metric_ranks rows for (metric, period, comparison_set)
        with `rows`. Ranking is always within a single period and scope."""
        ...

    def record_feed_run(
        self,
        feed_code: str,
        status: str,
        rows_fetched: Optional[int] = None,
        message: Optional[str] = None,
    ) -> int:
        """Insert a core.feed_runs row for the feed; return its id."""
        ...

    # --- bulk operations (fast path for trusted feeds) ----------------------

    def bulk_insert_pending(self, rows: list[BulkPendingRow]) -> list[int]:
        """Multi-row INSERT of pre-resolved rows into pending_values.
        Returns the new pending ids in input order. All id fields in each row
        must already be resolved (no further DB lookups). Unlike
        insert_pending_value, this issues a single batched statement per chunk
        rather than one per row."""
        ...

    def promote_approved_bulk(
        self,
        pending_ids: list[int],
        *,
        feed_id: int,
        agency_ids: list[int],
        metric_ids: list[int],
    ) -> BulkPromoteResult:
        """Diff-aware bulk promotion of approved pending rows into metric_values.

        Runs inside a single transaction guarded by pg_advisory_xact_lock(feed_id)
        so concurrent invocations of the same feed serialize, never corrupt.

        For each pending row the current cohort is read once and classified:
          - absent         → INSERT (restatement_of_id = NULL)
          - value or quality changed → supersede old + INSERT new
          - identical      → skip (idempotent re-run produces zero audit rows)

        Invariants upheld: one_current_value partial index, restatement_of_id
        chain, audit trigger fires per-row on INSERT, metric_value_sources link
        inserted for rows that have a source_document_id.
        """
        ...

    def list_current_values_for_metrics_periods(
        self, metric_ids: list[int], period_ids: list[int]
    ) -> list[MetricValue]:
        """All is_current values for a set of metrics across a set of periods.
        One query instead of N×M individual list_current_values_for_metric_period
        calls; used by bulk_refresh_ranks."""
        ...

    def replace_ranks_bulk(
        self,
        metric_ids: list[int],
        period_ids: list[int],
        rank_rows: list[BulkMetricRankRow],
    ) -> None:
        """Set-based rank replacement: one DELETE for all (metric, period) pairs
        then one multi-row INSERT of all computed ranks. Replaces the per-cohort
        replace_metric_ranks loop used by the slow path."""
        ...

    # --- test introspection --------------------------------------------------

    def iter_audit(self) -> list[dict]:
        """Return the metric_value_audit entries in insertion order (for tests)."""
        ...
