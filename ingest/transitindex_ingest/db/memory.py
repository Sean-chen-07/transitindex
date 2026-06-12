"""In-memory Repository implementation -- the offline workhorse for all tests.

Backed by plain dicts with auto-increment ids. Seeded on construction from
refdata (10 agencies, 20 metrics, 10 modes, 8 feeds) so slug/code lookups
resolve exactly as against the live DB. Faithfully enforces the
one_current_value invariant (mode_id None is a concrete key part), the
supersede/restatement chain, and the audit trail on every metric_value write.
Pure stdlib.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Optional

from ..contract import MetricValueRecord, SourceRef
from ..refdata import AGENCIES, METRICS, MODES, SOURCE_FEEDS
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

# Tuple key for the one_current_value index. mode_id None is a real key part.
_CurrentKey = tuple[int, int, int, Optional[int], str]


class InMemoryRepository:
    """Dict-backed Repository. See module docstring for invariants."""

    def __init__(self) -> None:
        # name -> id maps (seeded below)
        self._agency_ids: dict[str, int] = {}
        self._metric_ids: dict[str, int] = {}
        self._mode_ids: dict[str, int] = {}
        self._feed_ids: dict[str, int] = {}
        # agency_id -> static service_area_population (None unless set; tests may
        # write this directly to exercise net_debt_per_capita).
        self._agency_population: dict[int, Decimal] = {}

        # tables keyed by id
        self._metrics: dict[int, Metric] = {}
        self._periods: dict[int, ReportingPeriod] = {}
        self._documents: dict[int, SourceDocument] = {}
        self._pending: dict[int, PendingValue] = {}
        self._values: dict[int, MetricValue] = {}
        # (metric_value_id, source_document_id) -> link bookkeeping
        self._value_sources: dict[tuple[int, int], dict] = {}
        # metric_value_id -> {'equation_code': str, 'input_value_ids': list[int]}
        self._derivations: dict[int, dict] = {}
        # (metric_id, period_id, comparison_set) -> list[MetricRankRow]
        self._ranks: dict[tuple[int, int, str], list[MetricRankRow]] = {}
        self._feed_runs: list[dict] = []
        self._audit: list[dict] = []

        # index for one_current_value: current key -> metric_value id
        self._current_index: dict[_CurrentKey, int] = {}

        # secondary identity index for documents: (source_url, document_type) -> id
        self._doc_by_url: dict[tuple[str, str], int] = {}

        # the PDF catalog (core.documents): id -> Document, plus storage_key -> id
        self._catalog: dict[int, Document] = {}
        self._catalog_by_key: dict[str, int] = {}

        # auto-increment counters
        self._seq: dict[str, int] = {}

        self._seed()

    # --- seeding -------------------------------------------------------------

    def _seed(self) -> None:
        for slug in AGENCIES:
            self._agency_ids[slug] = self._next("agency")
        for code in MODES:
            self._mode_ids[code] = self._next("mode")
        for code, m in METRICS.items():
            mid = self._next("metric")
            self._metric_ids[code] = mid
            self._metrics[mid] = Metric(
                id=mid,
                code=code,
                display_name=code,  # display_name not needed offline; mirror code
                unit=m["unit"],
                unit_type=m["unit_type"],
                is_derived=m["is_derived"],
                formula=m["formula"],
                higher_is_better=m["higher_is_better"],
            )
        for code in SOURCE_FEEDS:
            self._feed_ids[code] = self._next("feed")

    def _next(self, name: str) -> int:
        self._seq[name] = self._seq.get(name, 0) + 1
        return self._seq[name]

    # --- id resolution -------------------------------------------------------

    def agency_id(self, slug: str) -> int:
        try:
            return self._agency_ids[slug]
        except KeyError:
            raise ValueError(f"unknown agency slug: {slug!r}") from None

    def metric_id(self, code: str) -> int:
        try:
            return self._metric_ids[code]
        except KeyError:
            raise ValueError(f"unknown metric code: {code!r}") from None

    def mode_id(self, code: Optional[str]) -> Optional[int]:
        if code is None:
            return None
        try:
            return self._mode_ids[code]
        except KeyError:
            raise ValueError(f"unknown mode code: {code!r}") from None

    def feed_id(self, code: str) -> int:
        try:
            return self._feed_ids[code]
        except KeyError:
            raise ValueError(f"unknown feed code: {code!r}") from None

    def list_metrics(self) -> list[Metric]:
        return list(self._metrics.values())

    def agency_population(self, agency_id: int) -> Optional[Decimal]:
        return self._agency_population.get(agency_id)

    # --- period & document upsert -------------------------------------------

    def get_or_create_reporting_period(
        self,
        period_type: str,
        start_date: date,
        end_date: date,
        label: str,
    ) -> int:
        # Shared across agencies (migration 009): identity (period_type, start_date, end_date).
        for period in self._periods.values():
            if (
                period.period_type == period_type
                and period.start_date == start_date
                and period.end_date == end_date
            ):
                return period.id
        pid = self._next("period")
        self._periods[pid] = ReportingPeriod(
            id=pid,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date,
            label=label,
        )
        return pid

    def get_or_create_source_document(
        self, source: SourceRef, agency_id: Optional[int]
    ) -> int:
        if source.source_url is not None:
            key = (source.source_url, source.document_type)
            existing = self._doc_by_url.get(key)
            if existing is not None:
                return existing
        did = self._next("document")
        self._documents[did] = SourceDocument(
            id=did,
            agency_id=agency_id,
            document_type=source.document_type,
            title=source.title,
            publication_date=source.publication_date,
            source_url=source.source_url,
            archive_uri=source.archive_uri,
            file_hash=source.file_hash,
            license=source.license,
        )
        if source.source_url is not None:
            self._doc_by_url[(source.source_url, source.document_type)] = did
        return did

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
        from dataclasses import replace

        existing_id = self._catalog_by_key.get(storage_key)
        if existing_id is not None:
            # Re-upload: refresh hash/size/source_url; leave scan state untouched.
            self._catalog[existing_id] = replace(
                self._catalog[existing_id],
                agency_id=agency_id,
                year=year,
                doc_type=doc_type,
                author_label=author_label,
                source_url=source_url,
                file_hash=file_hash,
                file_bytes=file_bytes,
            )
            return existing_id
        did = self._next("catalog")
        self._catalog[did] = Document(
            id=did,
            agency_id=agency_id,
            year=year,
            doc_type=doc_type,
            author_label=author_label,
            storage_key=storage_key,
            source_url=source_url,
            file_hash=file_hash,
            file_bytes=file_bytes,
            scan_status="unscanned",
            scanned_at=None,
            staged_count=None,
            last_error=None,
            source_document_id=None,
        )
        self._catalog_by_key[storage_key] = did
        return did

    def list_documents(self, status: Optional[str] = None) -> list[Document]:
        rows = [d for d in self._catalog.values() if status is None or d.scan_status == status]
        # unscanned first (the work queue), then by agency, year, doc_type.
        order = {"unscanned": 0, "failed": 1, "scanned": 2}
        return sorted(
            rows,
            key=lambda d: (order.get(d.scan_status, 9), d.agency_id, d.year, d.doc_type),
        )

    def get_document(self, document_id: int) -> Optional[Document]:
        return self._catalog.get(document_id)

    def mark_document_scanned(
        self, document_id: int, *, source_document_id: Optional[int], staged_count: int
    ) -> None:
        from dataclasses import replace
        from datetime import datetime, timezone

        self._catalog[document_id] = replace(
            self._catalog[document_id],
            scan_status="scanned",
            scanned_at=datetime.now(timezone.utc),
            staged_count=staged_count,
            last_error=None,
            source_document_id=source_document_id,
        )

    def mark_document_failed(self, document_id: int, *, error: str) -> None:
        from dataclasses import replace

        self._catalog[document_id] = replace(
            self._catalog[document_id], scan_status="failed", last_error=error
        )

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
        pid = self._next("pending")
        self._pending[pid] = PendingValue(
            id=pid,
            agency_id=agency_id,
            metric_id=metric_id,
            reporting_period_id=period_id,
            mode_id=mode_id,
            service_scope=record.service_scope,
            value=record.value,
            unit=record.unit,
            currency=record.currency,
            quality=record.quality,
            comparable_flag=record.comparable_flag,
            crosscheck_value=record.crosscheck_value,
            source_document_id=source_document_id,
            page_number=src.page_number if src else None,
            table_reference=src.table_reference if src else None,
            extraction_method=src.extraction_method if src else None,
            confidence=src.confidence if src else None,
            review_status=review_status,
            flags=list(flags) if flags is not None else list(record.flags),
            reviewer_notes=None,
        )
        return pid

    def list_pending_values(self, status: Optional[str] = None) -> list[PendingValue]:
        rows = list(self._pending.values())
        if status is not None:
            rows = [r for r in rows if r.review_status == status]
        return rows

    def get_pending_value(self, pending_id: int) -> Optional[PendingValue]:
        return self._pending.get(pending_id)

    def update_pending(
        self,
        pending_id: int,
        value: Optional[Decimal] = None,
        review_status: Optional[str] = None,
        reviewer_notes: Optional[str] = None,
    ) -> None:
        current = self._pending[pending_id]
        from dataclasses import replace

        self._pending[pending_id] = replace(
            current,
            value=current.value if value is None else value,
            review_status=(
                current.review_status if review_status is None else review_status
            ),
            reviewer_notes=(
                current.reviewer_notes if reviewer_notes is None else reviewer_notes
            ),
        )

    # --- current-value reads -------------------------------------------------

    def list_reporting_periods(self) -> list[ReportingPeriod]:
        # Shared across agencies (migration 009); the workbook pairs each period
        # with an agency's own values via list_current_values_for_agency_period.
        return sorted(self._periods.values(), key=lambda p: p.start_date)

    def get_current_metric_value(
        self,
        agency_id: int,
        metric_id: int,
        period_id: int,
        mode_id: Optional[int],
        service_scope: str,
    ) -> Optional[MetricValue]:
        key: _CurrentKey = (agency_id, metric_id, period_id, mode_id, service_scope)
        vid = self._current_index.get(key)
        return self._values[vid] if vid is not None else None

    def list_current_values_for_metric_period(
        self, metric_id: int, period_id: int
    ) -> list[MetricValue]:
        return [
            v
            for v in self._values.values()
            if v.is_current and v.metric_id == metric_id and v.reporting_period_id == period_id
        ]

    def list_current_values_for_agency_period(
        self, agency_id: int, period_id: int
    ) -> list[MetricValue]:
        return [
            v
            for v in self._values.values()
            if v.is_current and v.agency_id == agency_id and v.reporting_period_id == period_id
        ]

    def current_value_sources(
        self, agency_id: int, period_id: int
    ) -> dict[int, list[str]]:
        current_ids = {
            v.id
            for v in self._values.values()
            if v.is_current and v.agency_id == agency_id and v.reporting_period_id == period_id
        }
        out: dict[int, list[str]] = {vid: [] for vid in current_ids}
        for (mv_id, doc_id) in self._value_sources:
            if mv_id in current_ids and doc_id in self._documents:
                out[mv_id].append(self._documents[doc_id].document_type)
        return out

    # --- promotion & direct writes ------------------------------------------

    def promote_pending(self, pending_id: int) -> int:
        pending = self._pending[pending_id]
        vid = self._write_metric_value(
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
        # link source provenance (core.metric_value_sources)
        if pending.source_document_id is not None:
            self._value_sources[(vid, pending.source_document_id)] = {
                "metric_value_id": vid,
                "source_document_id": pending.source_document_id,
                "page_number": pending.page_number,
                "table_reference": pending.table_reference,
                "extraction_method": pending.extraction_method,
                "confidence": pending.confidence,
            }
        self.update_pending(pending_id, review_status="approved")
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
        return self._write_metric_value(
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
        vid = self._write_metric_value(
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
            crosscheck_value=None,
            notes=notes,
        )
        self._derivations[vid] = {
            "equation_code": equation_code,
            "input_value_ids": list(input_value_ids),
        }
        return vid

    def get_derivation(self, metric_value_id: int) -> Optional[dict]:
        return self._derivations.get(metric_value_id)

    def _write_metric_value(
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
        """Insert one metric value enforcing one_current_value + audit.

        If a current row exists for the tuple, flip it to is_current=False
        (an UPDATE, audited) and link the new row to it via restatement_of_id.
        """
        from dataclasses import replace

        key: _CurrentKey = (agency_id, metric_id, reporting_period_id, mode_id, service_scope)
        superseded_id = self._current_index.get(key)

        if superseded_id is not None:
            old = self._values[superseded_id]
            self._values[superseded_id] = replace(old, is_current=False)
            # is_current change is an UPDATE; value unchanged so audit logs no
            # value delta -- mirror the SQL trigger (only value changes audit on
            # UPDATE). We record the supersede UPDATE without a value delta.

        vid = self._next("metric_value")
        self._values[vid] = MetricValue(
            id=vid,
            agency_id=agency_id,
            metric_id=metric_id,
            reporting_period_id=reporting_period_id,
            mode_id=mode_id,
            service_scope=service_scope,
            value=value,
            unit=unit,
            currency=currency,
            quality=quality,
            comparable_flag=comparable_flag,
            crosscheck_value=crosscheck_value,
            restatement_of_id=superseded_id,
            is_current=True,
            notes=notes,
        )
        self._current_index[key] = vid
        self._audit.append(
            {
                "metric_value_id": vid,
                "change_type": "insert",
                "old_value": None,
                "new_value": value,
            }
        )
        return vid

    # --- ranking & feed bookkeeping -----------------------------------------

    def replace_metric_ranks(
        self,
        metric_id: int,
        period_id: int,
        comparison_set: str,
        rows: list[MetricRankRow],
    ) -> None:
        self._ranks[(metric_id, period_id, comparison_set)] = list(rows)

    def record_feed_run(
        self,
        feed_code: str,
        status: str,
        rows_fetched: Optional[int] = None,
        message: Optional[str] = None,
    ) -> int:
        feed_id = self.feed_id(feed_code)
        run_id = self._next("feed_run")
        self._feed_runs.append(
            {
                "id": run_id,
                "feed_id": feed_id,
                "status": status,
                "rows_fetched": rows_fetched,
                "message": message,
            }
        )
        return run_id

    # --- bulk operations (fast path for trusted feeds) ----------------------

    def bulk_insert_pending(self, rows: list[BulkPendingRow]) -> list[int]:
        ids: list[int] = []
        for r in rows:
            pid = self._next("pending")
            self._pending[pid] = PendingValue(
                id=pid,
                agency_id=r.agency_id,
                metric_id=r.metric_id,
                reporting_period_id=r.reporting_period_id,
                mode_id=r.mode_id,
                service_scope=r.service_scope,
                value=r.value,
                unit=r.unit,
                currency=r.currency,
                quality=r.quality,
                comparable_flag=r.comparable_flag,
                crosscheck_value=r.crosscheck_value,
                source_document_id=r.source_document_id,
                page_number=r.page_number,
                table_reference=r.table_reference,
                extraction_method=r.extraction_method,
                confidence=r.confidence,
                review_status=r.review_status,
                flags=list(r.flags),
                reviewer_notes=None,
            )
            ids.append(pid)
        return ids

    def promote_approved_bulk(
        self,
        pending_ids: list[int],
        *,
        feed_id: int,
        agency_ids: list[int],
        metric_ids: list[int],
    ) -> BulkPromoteResult:
        agency_id_set = set(agency_ids)
        metric_id_set = set(metric_ids)
        # Snapshot the current index for the touched agencies+metrics so we can
        # classify each incoming row (absent / changed / identical).
        current_snap: dict[tuple, int] = {
            k: v
            for k, v in self._current_index.items()
            if k[0] in agency_id_set and k[1] in metric_id_set
        }

        inserted = superseded = skipped = 0
        new_ids: list[int] = []

        for pid in pending_ids:
            pending = self._pending.get(pid)
            if pending is None:
                continue
            key = (
                pending.agency_id, pending.metric_id, pending.reporting_period_id,
                pending.mode_id, pending.service_scope,
            )
            current_vid = current_snap.get(key)
            if current_vid is not None:
                cv = self._values[current_vid]
                if pending.value == cv.value and pending.quality == cv.quality:
                    skipped += 1
                    # Stamp the 'promoted' sentinel (= promotion._PROMOTED_NOTE) so a
                    # later slow promote_approved() skips this bulk row.
                    self.update_pending(
                        pid, review_status="approved", reviewer_notes="promoted"
                    )
                    continue
                else:
                    superseded += 1
            else:
                inserted += 1

            vid = self._write_metric_value(
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
                self._value_sources[(vid, pending.source_document_id)] = {
                    "metric_value_id": vid,
                    "source_document_id": pending.source_document_id,
                    "page_number": pending.page_number,
                    "table_reference": pending.table_reference,
                    "extraction_method": pending.extraction_method,
                    "confidence": pending.confidence,
                }
            # Stamp 'promoted' (= promotion._PROMOTED_NOTE) so a later slow
            # promote_approved() does not re-promote this bulk row.
            self.update_pending(pid, review_status="approved", reviewer_notes="promoted")
            new_ids.append(vid)
            # Keep local snapshot current so subsequent rows see the new state.
            current_snap[key] = vid

        return BulkPromoteResult(
            inserted=inserted,
            superseded=superseded,
            skipped=skipped,
            metric_value_ids=new_ids,
        )

    def list_current_values_for_metrics_periods(
        self, metric_ids: list[int], period_ids: list[int]
    ) -> list[MetricValue]:
        mid_set = set(metric_ids)
        pid_set = set(period_ids)
        return [
            v
            for v in self._values.values()
            if v.is_current and v.metric_id in mid_set and v.reporting_period_id in pid_set
        ]

    def replace_ranks_bulk(
        self,
        metric_ids: list[int],
        period_ids: list[int],
        rank_rows: list[BulkMetricRankRow],
    ) -> None:
        mid_set = set(metric_ids)
        pid_set = set(period_ids)
        for key in [k for k in self._ranks if k[0] in mid_set and k[1] in pid_set]:
            del self._ranks[key]
        for r in rank_rows:
            key = (r.metric_id, r.reporting_period_id, r.comparison_set)
            self._ranks.setdefault(key, []).append(
                MetricRankRow(
                    agency_id=r.agency_id,
                    rank=r.rank,
                    denominator=r.denominator,
                    direction=r.direction,
                )
            )

    def wipe_feed_data(
        self,
        *,
        agency_ids: list[int],
        source_document_id: int,
        metric_ids: list[int],
        dry_run: bool = False,
    ) -> dict[int, tuple[int, int, int]]:
        from dataclasses import replace

        aid_set = set(agency_ids)
        mid_set = set(metric_ids)

        # metric_values whose provenance is this feed's source document.
        value_ids = {
            vid
            for (vid, doc) in self._value_sources
            if doc == source_document_id
            and vid in self._values
            and self._values[vid].agency_id in aid_set
        }
        # pending_values carry source_document_id directly.
        pending_ids = {
            pid
            for pid, p in self._pending.items()
            if p.source_document_id == source_document_id and p.agency_id in aid_set
        }

        # Per-agency counts (the blast radius the caller prints).
        counts: dict[int, list[int]] = {}

        def bump(agency_id: int, slot: int) -> None:
            counts.setdefault(agency_id, [0, 0, 0])[slot] += 1

        # ranks: this feed's metrics, for the feed's agencies (pure derived).
        rank_survivors: dict[tuple, list] = {}
        for key, rows in self._ranks.items():
            if key[0] not in mid_set:
                continue
            survivors = []
            for r in rows:
                if r.agency_id in aid_set:
                    bump(r.agency_id, 0)
                else:
                    survivors.append(r)
            if len(survivors) != len(rows):
                rank_survivors[key] = survivors
        for vid in value_ids:
            bump(self._values[vid].agency_id, 1)
        for pid in pending_ids:
            bump(self._pending[pid].agency_id, 2)

        result = {a: tuple(c) for a, c in counts.items()}
        if dry_run:
            return result

        # Apply ranks.
        for key, survivors in rank_survivors.items():
            if survivors:
                self._ranks[key] = survivors
            else:
                del self._ranks[key]
        # Null inbound restatement_of_id refs so nothing dangles after delete.
        for vid, mv in list(self._values.items()):
            if mv.restatement_of_id in value_ids:
                self._values[vid] = replace(mv, restatement_of_id=None)
        # Delete the values + their provenance links + audit (cascade) + current index.
        for vid in value_ids:
            mv = self._values.pop(vid)
            key = (
                mv.agency_id, mv.metric_id, mv.reporting_period_id,
                mv.mode_id, mv.service_scope,
            )
            if self._current_index.get(key) == vid:
                del self._current_index[key]
            self._derivations.pop(vid, None)
        for link_key in [k for k in self._value_sources if k[0] in value_ids]:
            del self._value_sources[link_key]
        self._audit = [a for a in self._audit if a["metric_value_id"] not in value_ids]
        # Delete the pending rows.
        for pid in pending_ids:
            del self._pending[pid]
        return result

    # --- test introspection --------------------------------------------------

    def iter_audit(self) -> list[dict]:
        return list(self._audit)
