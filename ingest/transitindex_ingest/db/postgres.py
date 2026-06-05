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
    BulkPendingRow,
    BulkPromoteResult,
    BulkMetricRankRow,
)


class PostgresRepository:
    """Repository backed by Postgres. Construct with a DATABASE_URL DSN."""

    def __init__(self, dsn: str) -> None:
        import psycopg  # lazy: importing this module must not require psycopg

        # Supabase's connection pooler does not support server-side prepared
        # statements; psycopg auto-prepares a statement after a few reuses, which
        # over the pooler surfaces as "server closed the connection unexpectedly"
        # partway through a multi-hundred-row load. Disabling preparation is the
        # psycopg equivalent of the web app's `prepare: false` (web/src/server/db.ts).
        # TCP keepalives keep the pooler/NAT from dropping an otherwise-busy session.
        # autocommit=True is REQUIRED here, not a tuning choice. Every write method
        # wraps its work in `with self._conn.transaction()` (a real BEGIN/COMMIT under
        # autocommit). Without autocommit, the bare statements below (SET search_path,
        # the cached id SELECTs) open an implicit outer transaction, which turns every
        # `transaction()` block into a nested SAVEPOINT — so the work is only released,
        # never committed, and is rolled back when the process exits. (That is exactly
        # why a load could report "promoted N" yet leave the tables empty.)
        self._conn = psycopg.connect(
            dsn,
            autocommit=True,
            prepare_threshold=None,
            keepalives=1,
            keepalives_idle=30,
            keepalives_interval=10,
            keepalives_count=5,
            connect_timeout=10,                    # fail fast if pooler is dead
            options="-c statement_timeout=30000",  # 30 s cap; kills a half-dead socket
        )
        self._conn.execute("SET search_path TO core, public")
        # Memoize immutable reference-data id lookups (agencies/metrics/modes/feeds)
        # so a multi-hundred-row load isn't ~3 extra round-trips per row.
        self._id_cache: dict[tuple[str, tuple], int] = {}

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
        period_type: str,
        start_date: date,
        end_date: date,
        label: str,
    ) -> int:
        # Periods are shared across agencies (migration 009): identity is
        # (period_type, start_date, end_date). The same calendar period is one row,
        # so all agencies' values for it land in a single rank cohort.
        with self._conn.transaction():
            row = self._conn.execute(
                "SELECT id FROM core.reporting_periods "
                "WHERE period_type = %s AND start_date = %s AND end_date = %s",
                (period_type, start_date, end_date),
            ).fetchone()
            if row is not None:
                return row[0]
            return self._conn.execute(
                "INSERT INTO core.reporting_periods "
                "(period_type, start_date, end_date, label) "
                "VALUES (%s, %s, %s, %s) RETURNING id",
                (period_type, start_date, end_date, label),
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

    def list_reporting_periods(self) -> list[ReportingPeriod]:
        # Periods are shared across agencies (migration 009); the workbook pairs
        # each with an agency's own values via list_current_values_for_agency_period.
        rows = self._conn.execute(
            "SELECT id, period_type, start_date, end_date, label "
            "FROM core.reporting_periods ORDER BY start_date"
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

    # --- bulk operations (fast path for trusted feeds) ----------------------

    _BULK_BATCH = 100  # rows per multi-row INSERT statement

    def bulk_insert_pending(self, rows: list[BulkPendingRow]) -> list[int]:
        if not rows:
            return []
        all_ids: list[int] = []
        with self._conn.transaction():
            for i in range(0, len(rows), self._BULK_BATCH):
                batch = rows[i : i + self._BULK_BATCH]
                ph = ",".join(
                    ["(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"] * len(batch)
                )
                params: list = []
                for r in batch:
                    params.extend([
                        r.agency_id, r.metric_id, r.reporting_period_id, r.mode_id,
                        r.service_scope, r.value, r.unit, r.currency, r.quality,
                        r.comparable_flag, r.crosscheck_value, r.source_document_id,
                        r.page_number, r.table_reference, r.extraction_method,
                        r.confidence, r.review_status, r.flags,
                    ])
                batch_ids = self._conn.execute(
                    "INSERT INTO core.pending_values "
                    "(agency_id, metric_id, reporting_period_id, mode_id, service_scope, "
                    "value, unit, currency, quality, comparable_flag, crosscheck_value, "
                    "source_document_id, page_number, table_reference, extraction_method, "
                    f"confidence, review_status, flags) VALUES {ph} RETURNING id",
                    tuple(params),
                ).fetchall()
                all_ids.extend(r[0] for r in batch_ids)
        return all_ids

    def promote_approved_bulk(
        self,
        pending_ids: list[int],
        *,
        feed_id: int,
        agency_ids: list[int],
        metric_ids: list[int],
    ) -> BulkPromoteResult:
        if not pending_ids:
            return BulkPromoteResult(inserted=0, superseded=0, skipped=0, metric_value_ids=[])

        with self._conn.transaction():
            # (1) Advisory lock: serializes concurrent runs of the same feed.
            self._conn.execute("SELECT pg_advisory_xact_lock(%s)", (feed_id,))

            # (2) Fetch all pending rows we are about to promote in one SELECT.
            pending_rows = self._conn.execute(
                "SELECT id, agency_id, metric_id, reporting_period_id, mode_id, "
                "service_scope, value, unit, currency, quality, comparable_flag, "
                "crosscheck_value, source_document_id, page_number, table_reference, "
                "extraction_method, confidence "
                "FROM core.pending_values WHERE id = ANY(%s)",
                (pending_ids,),
            ).fetchall()
            # idx: 0=id 1=agency 2=metric 3=period 4=mode 5=scope 6=value 7=unit
            #      8=currency 9=quality 10=comparable 11=crosscheck 12=source_doc
            #      13=page 14=table_ref 15=extract_method 16=confidence
            pending_map = {r[0]: r for r in pending_rows}

            # (3) Read current cohort for touched agencies+metrics in one SELECT.
            current_rows = self._conn.execute(
                "SELECT id, agency_id, metric_id, reporting_period_id, mode_id, "
                "service_scope, value, quality "
                "FROM core.metric_values "
                "WHERE is_current AND agency_id = ANY(%s) AND metric_id = ANY(%s)",
                (agency_ids, metric_ids),
            ).fetchall()
            # current_map: natural key → (metric_value_id, value, quality)
            current_map: dict[tuple, tuple] = {
                (r[1], r[2], r[3], r[4], r[5]): (r[0], r[6], r[7])
                for r in current_rows
            }

            # (4) Classify each pending row.
            to_supersede_old_ids: list[int] = []
            to_insert: list[tuple] = []   # (pending_row, restatement_of_id | None)
            to_skip_pids: list[int] = []
            to_promote_pids: list[int] = []  # pending ids actually written

            for pid in pending_ids:
                r = pending_map.get(pid)
                if r is None:
                    continue
                key = (r[1], r[2], r[3], r[4], r[5])
                current = current_map.get(key)
                if current is None:
                    to_insert.append((r, None))
                else:
                    old_id, old_val, old_qual = current
                    if r[6] != old_val or r[9] != old_qual:
                        to_supersede_old_ids.append(old_id)
                        to_insert.append((r, old_id))
                    else:
                        to_skip_pids.append(pid)

            # (5) Supersede changed current rows.
            if to_supersede_old_ids:
                self._conn.execute(
                    "UPDATE core.metric_values SET is_current = false, updated_at = now() "
                    "WHERE id = ANY(%s)",
                    (to_supersede_old_ids,),
                )

            # (6) Bulk INSERT new current rows; collect RETURNING ids for source links.
            new_metric_value_ids: list[int] = []
            source_link_rows: list[tuple] = []

            for i in range(0, len(to_insert), self._BULK_BATCH):
                batch = to_insert[i : i + self._BULK_BATCH]
                ph = ",".join(
                    ["(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,NULL)"] * len(batch)
                )
                params = []
                for r, restatement_id in batch:
                    params.extend([
                        r[1], r[2], r[3], r[4], r[5],   # agency..scope
                        r[6], r[7], r[8], r[9],          # value, unit, currency, quality
                        r[10], r[11],                    # comparable_flag, crosscheck_value
                        restatement_id,                  # restatement_of_id
                    ])
                batch_mv_ids = self._conn.execute(
                    "INSERT INTO core.metric_values "
                    "(agency_id, metric_id, reporting_period_id, mode_id, service_scope, "
                    "value, unit, currency, quality, comparable_flag, crosscheck_value, "
                    f"restatement_of_id, is_current, notes) VALUES {ph} RETURNING id",
                    tuple(params),
                ).fetchall()

                for j, (r, _) in enumerate(batch):
                    new_mv_id = batch_mv_ids[j][0]
                    new_metric_value_ids.append(new_mv_id)
                    to_promote_pids.append(r[0])
                    if r[12] is not None:  # source_document_id
                        source_link_rows.append((new_mv_id, r[12], r[13], r[14], r[15], r[16]))

            # (7) Bulk INSERT provenance links.
            if source_link_rows:
                ph = ",".join(["(%s,%s,%s,%s,%s,%s)"] * len(source_link_rows))
                params = []
                for row in source_link_rows:
                    params.extend(row)
                self._conn.execute(
                    "INSERT INTO core.metric_value_sources "
                    "(metric_value_id, source_document_id, page_number, table_reference, "
                    f"extraction_method, confidence) VALUES {ph} "
                    "ON CONFLICT (metric_value_id, source_document_id) DO NOTHING",
                    tuple(params),
                )

            # (8) Mark all resolved pending rows as approved.
            all_resolved = to_promote_pids + to_skip_pids
            if all_resolved:
                self._conn.execute(
                    "UPDATE core.pending_values SET review_status = 'approved', "
                    "updated_at = now() WHERE id = ANY(%s)",
                    (all_resolved,),
                )

        n_inserted = sum(1 for _, rid in to_insert if rid is None)
        n_superseded = len(to_insert) - n_inserted
        return BulkPromoteResult(
            inserted=n_inserted,
            superseded=n_superseded,
            skipped=len(to_skip_pids),
            metric_value_ids=new_metric_value_ids,
        )

    def list_current_values_for_metrics_periods(
        self, metric_ids: list[int], period_ids: list[int]
    ) -> list[MetricValue]:
        if not metric_ids or not period_ids:
            return []
        rows = self._conn.execute(
            "SELECT " + _MV_COLS + " FROM core.metric_values "
            "WHERE is_current AND metric_id = ANY(%s) AND reporting_period_id = ANY(%s)",
            (metric_ids, period_ids),
        ).fetchall()
        return [MetricValue(*r) for r in rows]

    def replace_ranks_bulk(
        self,
        metric_ids: list[int],
        period_ids: list[int],
        rank_rows: list[BulkMetricRankRow],
    ) -> None:
        with self._conn.transaction():
            self._conn.execute(
                "DELETE FROM core.metric_ranks "
                "WHERE metric_id = ANY(%s) AND reporting_period_id = ANY(%s)",
                (metric_ids, period_ids),
            )
            if rank_rows:
                ph = ",".join(["(%s,%s,%s,%s,%s,%s,%s)"] * len(rank_rows))
                params: list = []
                for r in rank_rows:
                    params.extend([
                        r.agency_id, r.metric_id, r.reporting_period_id,
                        r.comparison_set, r.rank, r.denominator, r.direction,
                    ])
                self._conn.execute(
                    "INSERT INTO core.metric_ranks "
                    "(agency_id, metric_id, reporting_period_id, comparison_set, "
                    f"rank, denominator, direction) VALUES {ph}",
                    tuple(params),
                )

    # --- helpers -------------------------------------------------------------

    def _scalar_id(self, sql: str, params: tuple, what: str) -> int:
        # Reference data (agencies/metrics/modes/feeds) is immutable within a run,
        # so cache the lookup to avoid repeating it once per staged row.
        key = (sql, params)
        cached = self._id_cache.get(key)
        if cached is not None:
            return cached
        row = self._conn.execute(sql, params).fetchone()
        if row is None:
            raise ValueError(f"unknown {what}")
        self._id_cache[key] = row[0]
        return row[0]


_MV_COLS = (
    "id, agency_id, metric_id, reporting_period_id, mode_id, service_scope, value, "
    "unit, currency, quality, comparable_flag, crosscheck_value, restatement_of_id, "
    "is_current, notes"
)
