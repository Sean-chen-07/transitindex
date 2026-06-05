"""Offline tests for the FastAPI human review queue.

Skips cleanly when fastapi/httpx are absent. Uses TestClient over an
InMemoryRepository pre-loaded with 'pending' rows, and asserts Invariant #1
across HTTP: approving promotes exactly one value and flips review_status;
rejecting promotes nothing; an unreviewed value is absent from metric_values
until approved.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from transitindex_ingest.contract import MetricValueRecord, SourceRef  # noqa: E402
from transitindex_ingest.db.memory import InMemoryRepository  # noqa: E402
from transitindex_ingest.review.app import create_app  # noqa: E402


def _record(metric_code: str, value: str) -> MetricValueRecord:
    return MetricValueRecord(
        agency_slug="ttc",
        metric_code=metric_code,
        period_type="monthly",
        period_start=date(2026, 3, 1),
        period_end=date(2026, 3, 31),
        period_label="Mar 2026",
        service_scope="system_wide",
        value=Decimal(value),
        unit="count",
        quality="preliminary",
        source=SourceRef(
            document_type="statcan_table",
            extraction_method="statcan_passthrough",
            source_url="https://example.test/307",
            license="statcan_open",
            confidence=Decimal("1.0"),
        ),
    )


@pytest.fixture
def loaded_repo() -> InMemoryRepository:
    """A repo with two distinct 'pending' rows staged."""
    repo = InMemoryRepository()
    doc_id = repo.get_or_create_source_document(
        _record("annual_ridership", "1").source, repo.agency_id("ttc")
    )
    repo.insert_pending_value(
        _record("annual_ridership", "1234567"), source_document_id=doc_id
    )
    repo.insert_pending_value(
        _record("operating_revenue", "999"), source_document_id=doc_id, flags=["yoy_spike"]
    )
    return repo


#: Bearer token the test app is built with; the client sends it by default.
TOKEN = "test-secret-token"


@pytest.fixture
def client(loaded_repo) -> TestClient:
    return TestClient(
        create_app(loaded_repo, token=TOKEN),
        headers={"Authorization": f"Bearer {TOKEN}"},
    )


def test_list_returns_pending_rows(client):
    rows = client.get("/pending").json()
    assert len(rows) == 2
    codes = {r["metric_code"] for r in rows}
    assert codes == {"annual_ridership", "operating_revenue"}
    spike = next(r for r in rows if r["metric_code"] == "operating_revenue")
    assert spike["flags"] == ["yoy_spike"]
    assert spike["agency_slug"] == "ttc"
    assert all(r["review_status"] == "pending" for r in rows)


def test_detail_returns_full_row(client):
    pid = client.get("/pending").json()[0]["id"]
    detail = client.get(f"/pending/{pid}").json()
    assert detail["id"] == pid
    assert detail["service_scope"] == "system_wide"
    assert detail["quality"] == "preliminary"


def test_unknown_pending_is_404(client):
    assert client.get("/pending/99999").status_code == 404


def test_pending_value_absent_until_approved(loaded_repo, client):
    """Invariant #1 over HTTP: nothing in metric_values until approve."""
    pid = client.get("/pending").json()[0]["id"]
    metric_id = loaded_repo.metric_id("annual_ridership")
    agency_id = loaded_repo.agency_id("ttc")
    pending = loaded_repo.get_pending_value(pid)
    assert (
        loaded_repo.get_current_metric_value(
            agency_id, metric_id, pending.reporting_period_id, None, "system_wide"
        )
        is None
    )


def test_approve_promotes_exactly_one_and_flips_status(loaded_repo, client):
    pid = client.get("/pending").json()[0]["id"]
    before = len(loaded_repo._values)  # noqa: SLF001 - test introspection

    resp = client.post(f"/pending/{pid}/approve")
    assert resp.status_code == 200
    mv_id = resp.json()["metric_value_id"]

    after = len(loaded_repo._values)  # noqa: SLF001
    assert after == before + 1

    pending = loaded_repo.get_pending_value(pid)
    assert pending.review_status == "approved"

    promoted = loaded_repo._values[mv_id]  # noqa: SLF001
    assert promoted.is_current is True
    assert promoted.metric_id == loaded_repo.metric_id("annual_ridership")

    # Exactly one current row for the tuple, and it is reachable.
    current = loaded_repo.get_current_metric_value(
        loaded_repo.agency_id("ttc"),
        loaded_repo.metric_id("annual_ridership"),
        pending.reporting_period_id,
        None,
        "system_wide",
    )
    assert current is not None and current.id == mv_id


def test_reject_promotes_nothing(loaded_repo, client):
    pid = client.get("/pending").json()[0]["id"]
    before = len(loaded_repo._values)  # noqa: SLF001

    resp = client.post(f"/pending/{pid}/reject", json={"reason": "bad scan"})
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "rejected"

    assert len(loaded_repo._values) == before  # noqa: SLF001
    assert loaded_repo.get_pending_value(pid).reviewer_notes == "bad scan"


def test_edit_then_approve_uses_corrected_value(loaded_repo, client):
    pid = client.get("/pending").json()[0]["id"]

    patched = client.patch(f"/pending/{pid}", json={"value": "7777"}).json()
    assert patched["value"] == "7777"
    assert patched["review_status"] == "needs_edit"

    mv_id = client.post(f"/pending/{pid}/approve").json()["metric_value_id"]
    assert loaded_repo._values[mv_id].value == Decimal("7777")  # noqa: SLF001


def test_mutations_require_token(loaded_repo):
    """Mutating endpoints reject a missing/wrong token; reads stay open; nothing
    reaches metric_values without a valid token (the door that defeats Invariant #1)."""
    app = create_app(loaded_repo, token=TOKEN)
    anon = TestClient(app)  # no Authorization header

    # Reads are open: discovering a pending id needs no token.
    pid = anon.get("/pending").json()[0]["id"]

    # Each mutating verb is rejected without a token...
    assert anon.post(f"/pending/{pid}/approve").status_code == 401
    assert anon.post(f"/pending/{pid}/reject", json={"reason": "x"}).status_code == 401
    assert anon.patch(f"/pending/{pid}", json={"value": "1"}).status_code == 401

    # ...and with the wrong token.
    bad = TestClient(app, headers={"Authorization": "Bearer wrong"})
    assert bad.post(f"/pending/{pid}/approve").status_code == 401

    # No rejected request promoted anything.
    assert len(loaded_repo._values) == 0  # noqa: SLF001
