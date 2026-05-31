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
    Metric,
    MetricRankRow,
    MetricValue,
    PendingValue,
    ReportingPeriod,
    SourceDocument,
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

    # --- period & document upsert -------------------------------------------

    def get_or_create_reporting_period(
        self,
        agency_id: int,
        period_type: str,
        start_date,
        end_date,
        label: str,
    ) -> int:
        """Return the id of the matching core.reporting_periods row, creating it
        if absent. Identity is (agency_id, period_type, start_date)."""
        ...

    def get_or_create_source_document(self, source: SourceRef, agency_id: Optional[int]) -> int:
        """Return the id of the core.source_documents row for `source`, creating
        it if absent. Identity is (source_url, document_type) when a url exists,
        else a per-document new row."""
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

    def list_reporting_periods(self, agency_id: int) -> list[ReportingPeriod]:
        """All core.reporting_periods rows for an agency, ordered by start_date
        (used by the workbook export to enumerate an agency's periods)."""
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

    # --- test introspection --------------------------------------------------

    def iter_audit(self) -> list[dict]:
        """Return the metric_value_audit entries in insertion order (for tests)."""
        ...
