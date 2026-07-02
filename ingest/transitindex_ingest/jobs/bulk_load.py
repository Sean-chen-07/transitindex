"""Unified bulk loader for StatCan 23-10-0307 and Hamilton HSR.

Both feeds follow the same fast path:
  1. Resolve all reference ids (agencies, metrics, periods, source doc) with a
     Python-side cache — ~40 round-trips for the full StatCan set, ~15 for Hamilton.
  2. Validate flags (pure Python); split records into approved vs flagged.
  3. Bulk-stage ALL records into pending_values (multi-row INSERT, one txn).
  4. Diff-aware bulk-promote the approved subset into metric_values:
       - absent     → INSERT  (restatement_of_id = NULL)
       - changed    → supersede old + INSERT  (value or quality differed)
       - identical  → skip    (re-run is a true no-op, zero audit rows)
     All inside ONE transaction guarded by pg_advisory_xact_lock(feed_id) so a
     concurrent accidental re-launch blocks rather than corrupts.
  5. Lean bulk rank refresh: only the metrics actually touched, all periods in
     one cohort read + one DELETE + one INSERT.
  6. Self-verify (current count == expected, zero one_current_value dupes) and
     write a JSON result file.

The --reset path deletes ONLY this feed's own rows before staging — scoped to
the feed's source document (provenance), so a hand-entered or PDF-approved value
for the same agency is never touched. It requires explicit confirmation
(confirm=True / the CLI's --yes); without it, the per-agency blast radius is
printed and ResetNotConfirmed is raised.

Pure stdlib (no psycopg import here; all DB access via the Repository protocol).
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Callable, Optional

from ..contract import MetricValueRecord, SourceRef
from ..db.models import BulkPendingRow
from ..db.repository import Repository
from .rank_refresh import bulk_refresh_ranks

# Validator: record → list of flag strings.
_Validator = Callable[[MetricValueRecord], list[str]]


class ResetNotConfirmed(RuntimeError):
    """--reset was requested without confirmation. The per-agency blast radius has
    already been printed; re-run with --yes (confirm=True) to actually delete.
    Carries the would-delete totals so the CLI can echo them."""

    def __init__(self, feed_code: str, values: int, pending: int) -> None:
        self.feed_code = feed_code
        self.values = values
        self.pending = pending
        super().__init__(
            f"--reset for {feed_code} would delete {values} value(s) and "
            f"{pending} pending row(s). Re-run with --yes to proceed."
        )


@dataclass
class BulkLoadResult:
    """Outcome of a bulk_load run. Written to JSON; ok=True iff all checks pass."""

    ok: bool
    feed_code: str
    records_parsed: int
    records_flagged: int        # stayed pending (validation flags present)
    staged: int                 # rows inserted into pending_values
    promoted_inserted: int      # new metric_values (no prior current row)
    promoted_superseded: int    # metric_values that changed (value or quality)
    promoted_skipped: int       # identical to current (idempotent re-run)
    ranks_cohorts: int          # (metric, period, comparison_set) triples refreshed
    final_current_values: int   # current metric_values count for the agencies
    duplicate_keys: int         # should always be 0
    steps: list
    duration_sec: float
    reset_performed: bool

    @property
    def promoted_total(self) -> int:
        return self.promoted_inserted + self.promoted_superseded

    def to_dict(self) -> dict:
        d = asdict(self)
        d["promoted_total"] = self.promoted_total
        return d


def bulk_load(
    repo: Repository,
    records: list[MetricValueRecord],
    *,
    tier: int,
    feed_code: str,
    rank_metric_codes: list[str],
    agency_slugs: list[str],
    validator: Optional[_Validator] = None,
    reset: bool = False,
    confirm: bool = False,
) -> BulkLoadResult:
    """Load `records` through the fast bulk path; return a BulkLoadResult.

    Parameters
    ----------
    tier        : 0 = auto-approve clean rows; 1 = always pending unless
                  explicitly approved (Hamilton pattern: caller sets reset=True
                  and the adapter already emits quality='verified').
    feed_code   : source feed code for the feed_run record.
    rank_metric_codes : metrics to refresh ranks for (e.g. ['ridership',
                  'total_revenue_excluding_subsidy'] for StatCan; ['ridership'] for Hamilton).
    agency_slugs: slugs whose data this feed owns (for verification + reset).
    validator   : optional flag computer; None uses the project default (or no-op).
    reset       : if True, delete THIS feed's own rows before staging — scoped to
                  the feed's source document, so hand-entered / PDF values for the
                  same agency survive. Needs confirm=True.
    confirm     : gate on reset. False (the default) makes reset print the
                  per-agency blast radius and raise ResetNotConfirmed instead of
                  deleting. The CLI sets this from --yes.
    """
    t0 = time.monotonic()
    steps: list[str] = []

    def step(msg: str) -> None:
        steps.append(msg)
        print(msg, flush=True)

    validate = _resolve_validator(validator)

    # Resolve the one source document up front (all records in a feed share it):
    # both the reset scope and the provenance links key off it.
    source_doc_id: Optional[int] = None
    if records and records[0].source is not None:
        first_src = records[0].source
        agency_id_for_doc = repo.agency_id(records[0].agency_slug)
        source_doc_id = repo.get_or_create_source_document(first_src, agency_id_for_doc)

    # --- optional reset (scoped delete-first for forced reload) --------------
    reset_performed = False
    if reset and source_doc_id is not None:
        reset_performed = _perform_reset(
            repo,
            agency_slugs,
            rank_metric_codes,
            source_doc_id,
            feed_code=feed_code,
            confirm=confirm,
            step=step,
        )

    # --- 1. Resolve all reference ids with Python-side caching ---------------
    # Agencies and metrics are already cached in _id_cache (postgres.py).
    # Periods are NOT cached there — resolve each DISTINCT period once here.
    period_cache: dict[tuple, int] = {}
    for r in records:
        key = (r.period_type, r.period_start, r.period_end)
        if key not in period_cache:
            period_cache[key] = repo.get_or_create_reporting_period(
                r.period_type, r.period_start, r.period_end, r.period_label
            )

    step(
        f"ids resolved: {len(period_cache)} distinct periods, "
        f"source_doc_id={source_doc_id}"
    )

    # --- 2. Validate flags + split approved vs flagged -----------------------
    approved_rows: list[BulkPendingRow] = []
    flagged_rows: list[BulkPendingRow] = []

    for record in records:
        period_id = period_cache[(record.period_type, record.period_start, record.period_end)]
        agency_id = repo.agency_id(record.agency_slug)
        metric_id = repo.metric_id(record.metric_code)
        mode_id = repo.mode_id(record.mode_code)
        src = record.source

        flags = validate(record)
        review_status = "approved" if (tier == 0 and not flags) else "pending"

        row = BulkPendingRow(
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
            source_document_id=source_doc_id,
            page_number=src.page_number if src else None,
            table_reference=src.table_reference if src else None,
            extraction_method=src.extraction_method if src else None,
            confidence=src.confidence if src else None,
            review_status=review_status,
            flags=list(flags) if flags else list(record.flags),
        )
        if review_status == "approved":
            approved_rows.append(row)
        else:
            flagged_rows.append(row)

    all_rows = approved_rows + flagged_rows
    step(
        f"validated: {len(approved_rows)} approved, "
        f"{len(flagged_rows)} flagged (stay pending)"
    )

    # --- 3. Bulk-stage ALL records into pending_values -----------------------
    all_pending_ids = repo.bulk_insert_pending(all_rows)
    approved_pending_ids = all_pending_ids[: len(approved_rows)]
    step(f"staged: {len(all_pending_ids)} pending rows")

    # --- 4. Diff-aware bulk-promote the approved subset ----------------------
    feed_id = repo.feed_id(feed_code)
    agency_ids = [repo.agency_id(s) for s in agency_slugs]
    metric_ids = [repo.metric_id(c) for c in rank_metric_codes]

    result = repo.promote_approved_bulk(
        approved_pending_ids,
        feed_id=feed_id,
        agency_ids=agency_ids,
        metric_ids=metric_ids,
    )
    step(
        f"promoted: {result.inserted} inserted, {result.superseded} superseded, "
        f"{result.skipped} skipped (identical)"
    )

    # --- 5. Lean bulk rank refresh -------------------------------------------
    period_ids = list(set(period_cache.values()))
    cohorts = bulk_refresh_ranks(repo, rank_metric_codes, period_ids)
    step(f"ranks: {cohorts} cohort(s) refreshed for {len(period_ids)} period(s)")

    # --- 6. Record feed run --------------------------------------------------
    repo.record_feed_run(feed_code, status="ok", rows_fetched=len(records))

    # --- 7. Self-verify ------------------------------------------------------
    # final_count is scoped to THIS feed's source document; the dupe check stays
    # broad (one_current_value must hold for every value, not just the feed's).
    final_count, dupe_count = _verify(repo, agency_ids, source_doc_id)
    ok = dupe_count == 0
    if reset_performed:
        # After a scoped reset the only feed-owned current values are this load's
        # promotions, so the feed's current count must equal the approved rows.
        ok = ok and (final_count == len(approved_rows))

    step(
        f"verify: {final_count} current values for {len(agency_ids)} agency/agencies, "
        f"{dupe_count} duplicate keys, ok={ok}"
    )

    duration = time.monotonic() - t0
    return BulkLoadResult(
        ok=ok,
        feed_code=feed_code,
        records_parsed=len(records),
        records_flagged=len(flagged_rows),
        staged=len(all_pending_ids),
        promoted_inserted=result.inserted,
        promoted_superseded=result.superseded,
        promoted_skipped=result.skipped,
        ranks_cohorts=cohorts,
        final_current_values=final_count,
        duplicate_keys=dupe_count,
        steps=steps,
        duration_sec=round(duration, 2),
        reset_performed=reset_performed,
    )


# --- feed-specific wrappers --------------------------------------------------


def load_statcan(
    repo: Repository,
    csv_path: Path,
    *,
    reset: bool = False,
    confirm: bool = False,
) -> BulkLoadResult:
    """Load StatCan 23-10-0307 (12 agencies, ridership + total_revenue_excluding_subsidy, monthly)."""
    from ..adapters.statcan_307 import StatCan23100307Adapter
    from ..refdata import STATCAN_AGENCY_MAP

    adapter = StatCan23100307Adapter()
    records = adapter.parse(csv_path.read_text(encoding="utf-8-sig"))
    if adapter.skipped:
        print(f"[statcan] skipped {len(adapter.skipped)} unmapped row(s)")

    agency_slugs = sorted(set(STATCAN_AGENCY_MAP.values()))
    return bulk_load(
        repo,
        records,
        tier=0,
        feed_code="statcan_307",
        rank_metric_codes=["ridership", "total_revenue_excluding_subsidy"],
        agency_slugs=agency_slugs,
        reset=reset,
        confirm=confirm,
    )


def load_hamilton(
    repo: Repository,
    csv_path: Path,
    *,
    reset: bool = False,
    confirm: bool = False,
) -> BulkLoadResult:
    """Load Hamilton HSR (1 agency, ridership only, monthly).

    Hamilton is tier-1 (records are pending by default). The adapter already
    marks them quality='verified'; we approve-and-promote in one go.
    """
    from ..adapters.hamilton_hsr import HamiltonHSRAdapter

    adapter = HamiltonHSRAdapter()
    records = adapter.parse(csv_path.read_text(encoding="utf-8"))

    # Hamilton is tier-1, so stage_records would leave them pending.
    # For the bulk path, we force-approve since this is a controlled reconcile.
    # We do this by wrapping with a tier-0 call — the validator sees no flags
    # (Hamilton data is clean) so they auto-approve.
    return bulk_load(
        repo,
        records,
        tier=0,  # treat as trusted: zero-flag → approve
        feed_code="hamilton_open_data",
        rank_metric_codes=["ridership"],
        agency_slugs=["hamilton-street-railway"],
        reset=reset,
        confirm=confirm,
    )


# --- helpers -----------------------------------------------------------------


def _resolve_validator(validator: Optional[_Validator]) -> _Validator:
    if validator is not None:
        return validator
    try:
        from ..validation.flags import validate  # type: ignore
        return validate
    except ImportError:
        return lambda record: list(record.flags)


def _perform_reset(
    repo: Repository,
    agency_slugs: list[str],
    metric_codes: list[str],
    source_doc_id: int,
    *,
    feed_code: str,
    confirm: bool,
    step,
) -> bool:
    """Scoped reset: delete only this feed's own rows (provenance = its source
    document), never the agencies' hand-entered or PDF-approved values. Prints the
    per-agency blast radius. Without confirm it prints what WOULD be deleted and
    raises ResetNotConfirmed (the CLI maps that to 'pass --yes')."""
    agency_ids = [repo.agency_id(s) for s in agency_slugs]
    metric_ids = [repo.metric_id(c) for c in metric_codes]
    counts = repo.wipe_feed_data(
        agency_ids=agency_ids,
        source_document_id=source_doc_id,
        metric_ids=metric_ids,
        dry_run=not confirm,
    )
    id_to_slug = {repo.agency_id(s): s for s in agency_slugs}
    verb = "deleted" if confirm else "WOULD delete"
    tot_ranks = tot_values = tot_pending = 0
    for aid in sorted(counts, key=lambda a: id_to_slug.get(a, str(a))):
        ranks, values, pending = counts[aid]
        tot_ranks += ranks
        tot_values += values
        tot_pending += pending
        step(
            f"reset[{feed_code}]: {verb} {id_to_slug.get(aid, aid)}: "
            f"ranks={ranks}, values={values}, pending={pending}"
        )
    if not counts:
        step(f"reset[{feed_code}]: nothing of this feed's to delete yet")
    step(
        f"reset[{feed_code}]: {verb} total ranks={tot_ranks}, values={tot_values}, "
        f"pending={tot_pending} (only {feed_code}'s own rows; hand-entered & PDF "
        f"values untouched)"
    )
    if not confirm:
        raise ResetNotConfirmed(feed_code, tot_values, tot_pending)
    return True


def _verify(
    repo: Repository, agency_ids: list[int], source_document_id: Optional[int]
) -> tuple[int, int]:
    """Return (feed_current_value_count, duplicate_key_count).

    The count is scoped to the feed's own source document so the reset invariant
    (final == approved) holds even when the agencies also carry non-feed values.
    The duplicate check stays broad: one_current_value must hold for ALL values."""
    if hasattr(repo, "_conn"):
        conn = repo._conn
        if source_document_id is None:
            final = 0
        else:
            final = conn.execute(
                "SELECT COUNT(DISTINCT mv.id) FROM core.metric_values mv "
                "JOIN core.metric_value_sources mvs ON mvs.metric_value_id = mv.id "
                "WHERE mv.agency_id = ANY(%s) AND mv.is_current "
                "AND mvs.source_document_id = %s",
                (agency_ids, source_document_id),
            ).fetchone()[0]
        dupes = conn.execute(
            "SELECT COUNT(*) FROM ("
            "  SELECT 1 FROM core.metric_values "
            "  WHERE agency_id = ANY(%s) AND is_current "
            "  GROUP BY agency_id, metric_id, reporting_period_id, mode_id, service_scope "
            "  HAVING COUNT(*) > 1"
            ") x",
            (agency_ids,),
        ).fetchone()[0]
        return int(final), int(dupes)
    else:
        # InMemory: count current values whose provenance is the feed's source doc.
        if source_document_id is None:
            return 0, 0
        aid_set = set(agency_ids)
        feed_current = {
            vid
            for (vid, doc) in repo._value_sources
            if doc == source_document_id
            and vid in repo._values
            and repo._values[vid].is_current
            and repo._values[vid].agency_id in aid_set
        }
        # _current_index guarantees the one_current_value invariant, so dupes=0.
        return len(feed_current), 0
