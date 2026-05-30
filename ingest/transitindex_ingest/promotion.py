"""Promote approved pending rows into core.metric_values.

Invariant #1 (the staging door): a pending row with review_status
'pending', 'rejected', or 'needs_edit' NEVER reaches metric_values. Only
'approved' rows are promoted. The repository's promote_pending enforces the
rest -- one_current_value (supersede + restatement_of_id), the
metric_value_sources link, and the audit entry.

Both promote_pending (staging auto-approval -> approved) and the repo leave a
promoted pending row at review_status='approved', so review_status alone can't
say whether a row was already promoted. We stamp reviewer_notes with a sentinel
on promotion and skip already-stamped rows, making promote_approved idempotent.

Pure stdlib.
"""

from __future__ import annotations

from .db.repository import Repository

_PROMOTED_NOTE = "promoted"


def promote_one(repo: Repository, pending_id: int) -> int:
    """Promote a single approved pending row; return the new metric_value id.

    Raises ValueError if the row is not approved (guarding the staging door).
    """
    pending = repo.get_pending_value(pending_id)
    if pending is None:
        raise ValueError(f"unknown pending id: {pending_id}")
    if pending.review_status != "approved":
        raise ValueError(
            f"pending {pending_id} is {pending.review_status!r}, not 'approved'"
        )
    metric_value_id = repo.promote_pending(pending_id)
    repo.update_pending(pending_id, reviewer_notes=_PROMOTED_NOTE)
    return metric_value_id


def promote_approved(repo: Repository) -> list[int]:
    """Promote every approved-but-not-yet-promoted pending row.

    Returns the new metric_value ids in promotion order. Idempotent: rows
    already promoted (stamped) are skipped.
    """
    metric_value_ids: list[int] = []
    for pending in repo.list_pending_values("approved"):
        if pending.reviewer_notes == _PROMOTED_NOTE:
            continue
        metric_value_ids.append(promote_one(repo, pending.id))
    return metric_value_ids
