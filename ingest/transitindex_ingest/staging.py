"""Stage extracted records into core.pending_values -- the only door inward.

`stage_records` is the single entry point a feed calls after extraction. For
each record it:
  1. upserts the source document (provenance) and reporting period,
  2. runs validation to attach flags,
  3. inserts a core.pending_values row with the right review_status.

Tier auto-approval (Invariant: an unreviewed value never reaches metric_values):
  - Tier 0 (StatCan / open data) auto-approves to 'approved' ONLY when there
    are zero validation flags; any flag -> 'pending'.
  - Tier 2 (PDF) is ALWAYS 'pending' -- never auto-approved.
Approved rows are promoted separately by promotion.promote_approved.

A feed_run row is recorded for the batch via feeds.record_ok.

Pure stdlib.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence

from . import feeds
from .contract import MetricValueRecord
from .db.repository import Repository

# A validator maps a record to its list of flag strings.
Validator = Callable[[MetricValueRecord], list[str]]


def _default_validator() -> Validator:
    """The project validator if present, else a no-op that flags nothing.

    `validation.flags.validate` is built by a sibling component and may not be
    on disk yet; importing it lazily keeps staging usable (and testable) without
    it. When absent, callers can still inject their own validator.
    """
    try:
        from .validation.flags import validate  # type: ignore
    except ImportError:
        return lambda record: list(record.flags)
    return validate


def stage_records(
    repo: Repository,
    records: Sequence[MetricValueRecord],
    *,
    tier: int,
    feed_code: str,
    validator: Optional[Validator] = None,
) -> list[int]:
    """Stage `records` into core.pending_values; return the new pending ids.

    `tier` drives auto-approval (0 may auto-approve, 2 never does). `feed_code`
    names the source feed for the recorded feed_run. `validator` overrides the
    default flag computation.
    """
    validate = validator or _default_validator()
    pending_ids: list[int] = []

    for record in records:
        agency_id = repo.agency_id(record.agency_slug)

        if record.source is not None:
            source_document_id: Optional[int] = repo.get_or_create_source_document(
                record.source, agency_id
            )
        else:
            source_document_id = None

        repo.get_or_create_reporting_period(
            agency_id,
            record.period_type,
            record.period_start,
            record.period_end,
            record.period_label,
        )

        flags = validate(record)
        if tier == 0 and not flags:
            review_status = "approved"
        else:
            review_status = "pending"

        pending_ids.append(
            repo.insert_pending_value(
                record, source_document_id, review_status=review_status, flags=flags
            )
        )

    feeds.record_ok(repo, feed_code, rows_fetched=len(records))
    return pending_ids
