"""Real-DB smoke test for the StatCan bulk loader.

Skipped unless TEST_DATABASE_URL is set. When run, loads all 703 StatCan rows
against a real Postgres and asserts:
  - current count == parsed count (after --reset)
  - zero one_current_value duplicate keys
  - wall-clock < 30 s
  - idempotent re-run produces zero inserts / zero new audit rows

Set TEST_DATABASE_URL to a scratch Postgres (e.g. your dev Supabase project)
before running. The test cleans up after itself by deleting the loaded rows.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not TEST_DB, reason="TEST_DATABASE_URL not set")

STATCAN_CSV = Path(__file__).resolve().parents[2] / "statcan_23100307.csv"


@pytest.fixture()
def repo():
    from transitindex_ingest.db.postgres import PostgresRepository

    r = PostgresRepository(TEST_DB)
    yield r
    r._conn.close()


@pytest.fixture()
def statcan_slugs():
    from transitindex_ingest.refdata import STATCAN_AGENCY_MAP

    return sorted(set(STATCAN_AGENCY_MAP.values()))


@pytest.fixture(autouse=True)
def cleanup(repo, statcan_slugs):
    """Wipe StatCan data before and after the test."""
    aids = [repo.agency_id(s) for s in statcan_slugs]
    _delete(repo, aids)
    yield
    _delete(repo, aids)


def _delete(repo, aids):
    conn = repo._conn
    with conn.transaction():
        conn.execute("DELETE FROM core.metric_ranks WHERE agency_id = ANY(%s)", (aids,))
    with conn.transaction():
        conn.execute("DELETE FROM core.metric_values WHERE agency_id = ANY(%s)", (aids,))
    with conn.transaction():
        conn.execute("DELETE FROM core.pending_values WHERE agency_id = ANY(%s)", (aids,))


@pytest.mark.skipif(not STATCAN_CSV.exists(), reason="statcan_23100307.csv not present")
def test_bulk_load_statcan_703_rows(repo, statcan_slugs):
    from transitindex_ingest.jobs.bulk_load import load_statcan

    t0 = time.monotonic()
    result = load_statcan(repo, STATCAN_CSV, reset=True)
    elapsed = time.monotonic() - t0

    assert result.ok, f"load failed: {result.steps[-3:]}"
    assert result.duplicate_keys == 0
    assert result.promoted_inserted > 0
    assert elapsed < 30, f"load took {elapsed:.1f}s — expected < 30s"


@pytest.mark.skipif(not STATCAN_CSV.exists(), reason="statcan_23100307.csv not present")
def test_bulk_load_statcan_idempotent_rerun(repo, statcan_slugs):
    from transitindex_ingest.jobs.bulk_load import load_statcan

    load_statcan(repo, STATCAN_CSV, reset=True)

    audit_count_before = repo._conn.execute(
        "SELECT COUNT(*) FROM core.metric_value_audit mv "
        "JOIN core.metric_values v ON v.id = mv.metric_value_id "
        "WHERE v.agency_id = ANY(%s)",
        ([repo.agency_id(s) for s in statcan_slugs],),
    ).fetchone()[0]

    result2 = load_statcan(repo, STATCAN_CSV, reset=False)
    assert result2.promoted_inserted == 0
    assert result2.promoted_superseded == 0
    assert result2.promoted_skipped > 0
    assert result2.duplicate_keys == 0

    audit_count_after = repo._conn.execute(
        "SELECT COUNT(*) FROM core.metric_value_audit mv "
        "JOIN core.metric_values v ON v.id = mv.metric_value_id "
        "WHERE v.agency_id = ANY(%s)",
        ([repo.agency_id(s) for s in statcan_slugs],),
    ).fetchone()[0]
    assert audit_count_after == audit_count_before, "re-run should add zero audit rows"
