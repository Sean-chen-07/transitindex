"""Postgres commit-semantics regression test for PostgresRepository.

Runs ONLY when TEST_DATABASE_URL points at a real Postgres with db/migrations
applied (mirroring web/src/server/metrics/access.a1.test.ts, which is likewise
gated on TEST_DATABASE_URL). The rest of the suite uses InMemoryRepository, so
the real backend's transaction handling was never exercised — and a latent bug
slipped through: PostgresRepository connected WITHOUT autocommit, so the bare
statements in __init__ (SET search_path, the cached id SELECTs) opened an
implicit outer transaction. Every `with self._conn.transaction()` then became a
nested SAVEPOINT inside that never-committed outer transaction, so a full load
reported "promoted N" yet left core.* empty once the process exited and the
outer transaction rolled back.

This test proves the fix (autocommit=True) by staging + promoting a value on one
PostgresRepository connection and asserting the row is visible from a SEPARATE
connection — i.e. it was COMMITTED, not merely savepoint-released within the
writer's own session. Everything it writes is in a far-future reporting period
(so it can never collide with real data) and is removed in a finally block.
"""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal

import pytest

from transitindex_ingest import promotion, staging
from transitindex_ingest.contract import MetricValueRecord, SourceRef

TEST_DB = os.environ.get("TEST_DATABASE_URL")

# A far-future period no real StatCan/PDF data will ever occupy, so staging here
# cannot disturb (or be disturbed by) production rows.
_AGENCY = "ttc"
_METRIC = "ridership"
_PERIOD_START = date(2099, 1, 1)
_PERIOD_END = date(2099, 1, 31)
_PERIOD_LABEL = "Jan 2099"
_VALUE = Decimal("424242")


def _no_flags(_record):
    return []


def _record() -> MetricValueRecord:
    return MetricValueRecord(
        agency_slug=_AGENCY,
        metric_code=_METRIC,
        period_type="monthly",
        period_start=_PERIOD_START,
        period_end=_PERIOD_END,
        period_label=_PERIOD_LABEL,
        service_scope="total",
        value=_VALUE,
        unit="count",
        quality="verified",
        mode_code=None,
        currency=None,
        source=SourceRef(
            document_type="statcan_table",
            extraction_method="statcan_passthrough",
            source_url="https://example.test/commit-regression",
            license="statcan_open",
            confidence=Decimal("1.0"),
        ),
    )


@pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL not set")
def test_promoted_value_is_committed_and_visible_to_another_connection():
    import psycopg

    from transitindex_ingest.db.postgres import PostgresRepository

    repo = PostgresRepository(TEST_DB)

    # Resolve ids up front so teardown can target exactly our rows.
    agency_id = repo.agency_id(_AGENCY)
    metric_id = repo.metric_id(_METRIC)

    try:
        pending_ids = staging.stage_records(
            repo, [_record()], tier=0, feed_code="statcan_307", validator=_no_flags
        )
        assert len(pending_ids) == 1
        value_ids = promotion.promote_approved(repo)
        assert len(value_ids) == 1

        # THE PROOF: a brand-new, independent connection must see the row. If the
        # write were only savepoint-released inside the writer's uncommitted outer
        # transaction (the pre-autocommit bug), this separate session would see
        # nothing — the assertion below would fail.
        verifier = psycopg.connect(TEST_DB)
        try:
            row = verifier.execute(
                "SELECT value, is_current FROM core.metric_values "
                "WHERE agency_id = %s AND metric_id = %s AND reporting_period_id = "
                "(SELECT id FROM core.reporting_periods WHERE agency_id = %s "
                " AND period_type = 'monthly' AND start_date = %s)",
                (agency_id, metric_id, agency_id, _PERIOD_START),
            ).fetchone()
        finally:
            verifier.close()

        assert row is not None, (
            "promoted value not visible to a separate connection — it was not "
            "committed (PostgresRepository must connect with autocommit=True)"
        )
        assert row[0] == _VALUE
        assert row[1] is True
    finally:
        _cleanup(repo, agency_id, metric_id)


def _cleanup(repo, agency_id: int, metric_id: int) -> None:
    """Remove everything this test created. metric_value_audit and
    metric_value_sources cascade from metric_values (ON DELETE CASCADE), so
    deleting the values + the pending rows + the far-future period suffices."""
    conn = repo._conn  # autocommit connection
    period = conn.execute(
        "SELECT id FROM core.reporting_periods WHERE agency_id = %s "
        "AND period_type = 'monthly' AND start_date = %s",
        (agency_id, _PERIOD_START),
    ).fetchone()
    if period is None:
        return
    period_id = period[0]
    conn.execute(
        "DELETE FROM core.metric_ranks WHERE reporting_period_id = %s", (period_id,)
    )
    conn.execute(
        "DELETE FROM core.metric_values WHERE reporting_period_id = %s", (period_id,)
    )
    conn.execute(
        "DELETE FROM core.pending_values WHERE reporting_period_id = %s", (period_id,)
    )
    conn.execute("DELETE FROM core.reporting_periods WHERE id = %s", (period_id,))
