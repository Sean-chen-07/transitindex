"""Thin helpers around `Repository.record_feed_run` for feed-health bookkeeping.

Each helper records one core.feed_runs row with the right status. When column
names from the fetched payload are supplied, a stable schema_fingerprint is
computed from them so a later run can detect a schema break by comparison.

Pure stdlib.
"""

from __future__ import annotations

import hashlib
from typing import Optional, Sequence

from .db.repository import Repository


def schema_fingerprint(columns: Sequence[str]) -> str:
    """A stable fingerprint of a feed's column set (order-insensitive)."""
    joined = "\n".join(sorted(columns))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _message(message: Optional[str], columns: Optional[Sequence[str]]) -> Optional[str]:
    if columns is None:
        return message
    fp = schema_fingerprint(columns)
    return f"{message} ({fp})" if message else fp


def record_ok(
    repo: Repository,
    feed_code: str,
    rows_fetched: Optional[int] = None,
    columns: Optional[Sequence[str]] = None,
    message: Optional[str] = None,
) -> int:
    """Record a successful feed run."""
    return repo.record_feed_run(
        feed_code, "ok", rows_fetched=rows_fetched, message=_message(message, columns)
    )


def record_stalled(
    repo: Repository, feed_code: str, message: Optional[str] = None
) -> int:
    """Record a feed that produced no fresh data this run."""
    return repo.record_feed_run(feed_code, "stalled", message=message)


def record_schema_break(
    repo: Repository,
    feed_code: str,
    columns: Optional[Sequence[str]] = None,
    message: Optional[str] = None,
) -> int:
    """Record a feed whose source layout changed (its columns no longer match)."""
    return repo.record_feed_run(
        feed_code, "schema_break", message=_message(message, columns)
    )
