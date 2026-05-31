"""PostgresRepository -- the real backend, writing core.* via psycopg (v3).

psycopg is imported lazily inside __init__, so importing this module never
fails without the dependency. The class only runs when DATABASE_URL is set; no
test depends on it executing. SQL is parameterized against the applied schema
(db/schema.sql). The supersede/restatement and audit semantics are enforced in
the DB itself (the one_current_value unique index + metric_values_audit
trigger), so this layer issues the corresponding statements in a transaction.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from ..contract import MetricValueRecord, SourceRef
from .models import (
    Metric,
    MetricRankRow,
    MetricValue,
    PendingValue,
    ReportingPeriod,
    SourceDocument,
)


class PostgresRepository:
    """Repository backed by Postgres. Construct with a DATABASE_URL DSN."""

    def __init__(self, dsn: str) -> None:
        import psycopg  # lazy: importing this module must not require psycopg

        self._conn = psycopg.connect(dsn)
        self._conn.execute("SET search_path TO core, public")

    # --- id resolution -------------------------------------------------------

    def agency_id(self, slug: str) -> int:
        return self._scalar_id(
            "SELECT id FROM core.agencies WHERE slug = %s", (slug,), f"agency slug {slug!r}"
        )

    def metric_id(self, code: str) -> int:
        return self._scalar_id(
            "SELECT id FROM core.metrics WHERE code = %s", (code,), f"metric code {code!r}"
        )

    def mode_id(self, code: Optional[str]) -> Optional[int]:
        if code is None:
            return None
        return self._scalar_id(
            "SELECT id FROM core.modes WHERE code = %s", (code,), f"mode code {code!r}"
        )

    def feed_id(self, code: str) -> int:
        return self._scalar_id(
            "SELECT id FROM core.source_feeds WHERE code = %s", (code,), f"feed code {code!r}"
        )

    def list_metrics(self) -> list[Metric]:
        rows = self._conn.execute(
            "SELECT id, code, display_name, unit, unit_type, is_derived, formula, "
            "higher_is_better FROM core.metrics ORDER BY id"
        ).fetchall()
        return [Metric(*r) for r in rows]

    # --- period & document upsert -------------------------------------------

    def get_or_create_reporting_period(
        self,
        agency_id: int,
        period_type: str,
        start_date: date,
        end_date: date,
        label: str,
    ) -> int:
        with self._conn.transaction():
            row = self._conn.execute(
                "SELECT id FROM core.reporting_periods "
                "WHERE agency_id = %s AND period_type = %s AND start_date = %s",
                (agency_id, period_type, start_date),
            ).fetchone()
            if row is not None:
                return row[0]
            return self._conn.execute(
                "INSERT INTO core.reporting_periods "
                "(agency_id, period_type, start_date, end_date, label) "
                "VALUES (%s, %s, %s, %s, %s) RETURNING id",
                (agency_id, period_type, start_date, end_date, label),
            ).fetchone()[0]

    def get_or_create_source_document(
        self, source: SourceRef, agency_id: Optional[int]
    ) -> int:
        with self._conn.transaction():
            if source.source_url is not None:
                row = self._conn.execute(
                    "SELECT id FROM core.source_documents "
                    "WHERE source_url = %s AND document_type = %s",
                    (source.source_url, source.document_type),
                ).fetchone()
                if row is not None:
                    return row[0]
            return self._conn.execute(
                "INSERT INTO core.source_documents "
                "(agency_id, document_type, title, publication_date, source_url, "
                " archive_uri, file_hash, license) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                (
                    agency_id,
                    source.document_type,
                    source.title,
                    source.publication_date,
                    source.source_url,
                    source.archive_uri,
                    source.file_hash,
                    source.license,
                ),
            ).fetchone()[0]

    # --- staging -------------------------------------------------------------

    def insert_pending_value(
        self,
        record: MetricValueRecord,
        source_document_id: Optional[int],
        review_status: str = "pending",
        flags: Optional[list[str]] = None,
    ) -> int:
        agency_id = self.agency_id(record.agency_slug)
        metric_id = self.metric_id(record.metric_code)
        mode_id = self.mode_id(record.mode_code)
        period_id = self.get_or_create_reporting_period(
            agency_id,
            record.period_type,
            record.period_start,
            record.period_end,
            record.period_label,
        )
        src = record.source
        with self._conn.transaction():
            return self._conn.execute(
                "INSERT INTO core.pending_values "
                "(agency_id, metric_id, reporting_period_id, mode_id, service_scope, "
                " value, unit, currency, quality, comparable_flag, crosscheck_value, "
                " source_document_id, page_number, table_reference, extraction_method, "
                " confidence, review_status, flags) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                "%s, %s) RETURNING id",
                (
                    agency_id,
                    metric_id,
                    period_id,
                    mode_id,
                    record.service_scope,
                    record.value,
                    record.unit,
                    record.currency,
                    record.quality,
                    record.comparable_flag,
                    record.crosscheck_value,
                    source_document_id,
                    src.page_number if src else None,
                    src.table_reference if src else None,
                    src.extraction_method if src else None,
                    src.confidence if src else None,
                    review_status,
                    flags if flags is not None else list(record.flags),
                ),
            ).fetchone()[0]

    def list_pending_values(self, status: Optional[str] = None) -> list[PendingValue]:
        sql = (
            "SELECT id, agency_id, metric_id, reporting_period_id, mode_id, service_scope, "
            "value, unit, currency, quality, comparable_flag, crosscheck_value, "
            "source_document_id, page_number, table_reference, extraction_method, "
            "confidence, review_status, flags, reviewer_notes FROM core.pending_values"
        )
        params: tuple = ()
        if status is not None:
            sql += " WHERE review_status = %s"
            params = (status,)
        sql += " ORDER BY id"
        return [PendingValue(*r) for r in self._conn.execute(sql, params).fetchall()]

    def get_pending_value(self, pending_id: int) -> Optional[PendingValue]:
        row = self._conn.execute(
            "SELECT id, agency_id, metric_id, reporting_period_id, mode_id, service_scope, "
            "value, unit, currency, quality, comparable_flag, crosscheck_value, "
            "source_document_id, page_number, table_reference, extraction_method, "
            "confidence, review_status, flags, reviewer_notes "
            "FROM core.pending_values WHERE id = %s",
            (pending_id,),
        ).fetchone()
        return PendingValue(*row) if row is not None else None

    def update_pending(
        self,
        pending_id: int,
        value: Optional[Decimal] = None,
        review_status: Optional[str] = None,
        reviewer_notes: Optional[str] = None,
    ) -> None:
        sets, params = [], []
        if value is not None:
            sets.append("value = %s")
            params.append(value)
        if review_status is not None:
            sets.append("review_status = %s")
            params.append(review_status)
        if reviewer_notes is not None:
            sets.append("reviewer_notes = %s")
            params.append(reviewer_notes)
        if not sets:
            return
        sets.append("updated_at = now()")
        params.append(pending_id)
        with self._conn.transaction():
            self._conn.execute(
                f"UPDATE core.pending_values SET {', '.join(sets)} WHERE id = %s",
                tuple(params),
            )

    # --- current-value reads -------------------------------------------------

    def list_reporting_periods(self, agency_id: int) -> list[ReportingPeriod]:
        rows = self._conn.execute(
            "SELECT id, agency_id, period_type, start_date, end_date, label "
            "FROM core.reporting_periods WHERE agency_id = %s ORDER BY start_date",
            (agency_id,),
        ).fetchall()
        return [ReportingPeriod(*r) for r in rows]

    def get_current_metric_value(
        self,
        agency_id: int,
        metric_id: int,
        period_id: int,
        mode_id: Optional[int],
        service_scope: str,
    ) -> Optional[MetricValue]:
        row = self._conn.execute(
            "SELECT " + _MV_COLS + " FROM core.metric_values "
            "WHERE is_current AND agency_id = %s AND metric_id = %s "
            "AND reporting_period_id = %s AND mode_id IS NOT DISTINCT FROM %s "
            "AND service_scope = %s",
            (agency_id, metric_id, period_id, mode_id, service_scope),
        ).fetchone()
        return MetricValue(*row) if row is not None else None

    def list_current_values_for_metric_period(
        self, metric_id: int, period_id: int
    ) -> list[MetricValue]:
        rows = self._conn.execute(
            "SELECT " + _MV_COLS + " FROM core.metric_values "
            "WHERE is_current AND metric_id = %s AND reporting_period_id = %s",
            (metric_id, period_id),
        ).fetchall()
        return [MetricValue(*r) for r in rows]

    def list_current_values_for_agency_period(
        self, agency_id: int, period_id: int
    ) -> list[MetricValue]:
        rows = self._conn.execute(
            "SELECT " + _MV_COLS + " FROM core.metric_values "
            "WHERE is_current AND agency_id = %s AND reporting_period_id = %s",
            (agency_id, period_id),
        ).fetchall()
        return [MetricValue(*r) for r in rows]

    # --- promotion & direct writes ------------------------------------------

    def promote_pending(self, pending_id: int) -> int:
        pending = self.get_pending_value(pending_id)
        if pending is None:
            raise ValueError(f"no pending value with id {pending_id}")
        with self._conn.transaction():
            vid = self._insert_value_locked(
                agency_id=pending.agency_id,
                metric_id=pending.metric_id,
                reporting_period_id=pending.reporting_period_id,
                mode_id=pending.mode_id,
                service_scope=pending.service_scope,
                value=pending.value,
                unit=pending.unit,
                quality=pending.quality,
                currency=pending.currency,
                comparable_flag=pending.comparable_flag,
                crosscheck_value=pending.crosscheck_value,
                notes=None,
            )
            if pending.source_document_id is not None:
                self._conn.execute(
                    "INSERT INTO core.metric_value_sources "
                    "(metric_value_id, source_document_id, page_number, table_reference, "
                    " extraction_method, confidence) VALUES (%s, %s, %s, %s, %s, %s)",
                    (
                        vid,
                        pending.source_document_id,
                        pending.page_number,
                        pending.table_reference,
                        pending.extraction_method,
                        pending.confidence,
                    ),
                )
            self._conn.execute(
                "UPDATE core.pending_values SET review_status = 'approved', "
                "updated_at = now() WHERE id = %s",
                (pending_id,),
            )
        return vid

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
        with self._conn.transaction():
            return self._insert_value_locked(
                agency_id=agency_id,
                metric_id=metric_id,
                reporting_period_id=reporting_period_id,
                mode_id=mode_id,
                service_scope=service_scope,
                value=value,
                unit=unit,
                quality=quality,
                currency=currency,
                comparable_flag=comparable_flag,
                crosscheck_value=crosscheck_value,
                notes=notes,
            )

    def _insert_value_locked(
        self,
        *,
        agency_id: int,
        metric_id: int,
        reporting_period_id: int,
        mode_id: Optional[int],
        service_scope: str,
        value: Decimal,
        unit: str,
        quality: str,
        currency: Optional[str],
        comparable_flag: bool,
        crosscheck_value: Optional[Decimal],
        notes: Optional[str],
    ) -> int:
        """Supersede any current row, then insert the new current row.

        Runs inside a caller-opened transaction. The one_current_value index
        guarantees at most one is_current row; the audit trigger fires on both
        the UPDATE and the INSERT.
        """
        old = self._conn.execute(
            "SELECT id FROM core.metric_values "
            "WHERE is_current AND agency_id = %s AND metric_id = %s "
            "AND reporting_period_id = %s AND mode_id IS NOT DISTINCT FROM %s "
            "AND service_scope = %s",
            (agency_id, metric_id, reporting_period_id, mode_id, service_scope),
        ).fetchone()
        superseded_id = old[0] if old is not None else None
        if superseded_id is not None:
            self._conn.execute(
                "UPDATE core.metric_values SET is_current = false, updated_at = now() "
                "WHERE id = %s",
                (superseded_id,),
            )
        return self._conn.execute(
            "INSERT INTO core.metric_values "
            "(agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, "
            " unit, currency, quality, comparable_flag, crosscheck_value, "
            " restatement_of_id, is_current, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, %s) RETURNING id",
            (
                agency_id,
                metric_id,
                reporting_period_id,
                mode_id,
                service_scope,
                value,
                unit,
                currency,
                quality,
                comparable_flag,
                crosscheck_value,
                superseded_id,
                notes,
            ),
        ).fetchone()[0]

    # --- ranking & feed bookkeeping -----------------------------------------

    def replace_metric_ranks(
        self,
        metric_id: int,
        period_id: int,
        comparison_set: str,
        rows: list[MetricRankRow],
    ) -> None:
        with self._conn.transaction():
            self._conn.execute(
                "DELETE FROM core.metric_ranks "
                "WHERE metric_id = %s AND reporting_period_id = %s AND comparison_set = %s",
                (metric_id, period_id, comparison_set),
            )
            for r in rows:
                self._conn.execute(
                    "INSERT INTO core.metric_ranks "
                    "(agency_id, metric_id, reporting_period_id, comparison_set, rank, "
                    " denominator, direction) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        r.agency_id,
                        metric_id,
                        period_id,
                        comparison_set,
                        r.rank,
                        r.denominator,
                        r.direction,
                    ),
                )

    def record_feed_run(
        self,
        feed_code: str,
        status: str,
        rows_fetched: Optional[int] = None,
        message: Optional[str] = None,
    ) -> int:
        feed_id = self.feed_id(feed_code)
        with self._conn.transaction():
            return self._conn.execute(
                "INSERT INTO core.feed_runs (feed_id, status, rows_fetched, message, "
                "started_at, finished_at) VALUES (%s, %s, %s, %s, now(), now()) RETURNING id",
                (feed_id, status, rows_fetched, message),
            ).fetchone()[0]

    # --- test introspection --------------------------------------------------

    def iter_audit(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT metric_value_id, change_type, old_value, new_value "
            "FROM core.metric_value_audit ORDER BY id"
        ).fetchall()
        return [
            {
                "metric_value_id": r[0],
                "change_type": r[1],
                "old_value": r[2],
                "new_value": r[3],
            }
            for r in rows
        ]

    # --- helpers -------------------------------------------------------------

    def _scalar_id(self, sql: str, params: tuple, what: str) -> int:
        row = self._conn.execute(sql, params).fetchone()
        if row is None:
            raise ValueError(f"unknown {what}")
        return row[0]


_MV_COLS = (
    "id, agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, "
    "unit, currency, quality, comparable_flag, crosscheck_value, restatement_of_id, "
    "is_current, notes"
)
