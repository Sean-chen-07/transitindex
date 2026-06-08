"""Offline tests for the documents console mounted on the review app.

Skips when fastapi is absent. Uses TestClient over an InMemoryRepository with a
cataloged document and a stub scanner (no real extraction). Asserts the page
lists the document with a Scan button, that posting Scan invokes the scanner and
the row reflects the outcome, and that without a scanner the page degrades to a
"scanning unavailable" notice instead of offering a dead button.
"""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from transitindex_ingest.db.memory import InMemoryRepository  # noqa: E402
from transitindex_ingest.review.app import create_app  # noqa: E402


def _repo_with_doc() -> InMemoryRepository:
    repo = InMemoryRepository()
    repo.upsert_document(
        agency_id=repo.agency_id("ttc"),
        year=2024,
        doc_type="annual_report",
        author_label="T",
        storage_key="ttc/ttc-2024.pdf",
    )
    return repo


def test_documents_page_lists_unscanned_with_scan_button():
    repo = _repo_with_doc()
    client = TestClient(create_app(repo, token="t", scanner=lambda i: {"ok": True}))
    html = client.get("/documents").text
    assert "ttc" in html
    assert "annual_report" in html
    assert "unscanned" in html
    assert "/documents/1/scan" in html  # the Scan form action


def test_scan_button_invokes_scanner_and_marks_row():
    repo = _repo_with_doc()
    called = {}

    def scanner(document_id):
        called["id"] = document_id
        repo.mark_document_scanned(document_id, source_document_id=None, staged_count=3)
        return {"ok": True, "staged_count": 3, "error": None}

    client = TestClient(create_app(repo, token="t", scanner=scanner))
    # 303 redirect back to the listing; don't auto-follow so we can read the status.
    resp = client.post("/documents/1/scan", follow_redirects=False)
    assert resp.status_code == 303
    assert called["id"] == 1
    assert repo.get_document(1).scan_status == "scanned"

    # The refreshed page shows the scanned state.
    page = client.get("/documents").text
    assert "scanned" in page
    assert "3 staged" in page


def test_failed_scan_surfaces_message():
    repo = _repo_with_doc()

    def scanner(document_id):
        repo.mark_document_failed(document_id, error="boom while extracting")
        return {"ok": False, "staged_count": 0, "error": "boom while extracting"}

    client = TestClient(create_app(repo, token="t", scanner=scanner))
    client.post("/documents/1/scan", follow_redirects=False)
    assert repo.get_document(1).scan_status == "failed"
    page = client.get("/documents").text
    assert "failed" in page


def test_without_scanner_shows_unavailable_notice():
    repo = _repo_with_doc()
    client = TestClient(create_app(repo, token="t"))  # no scanner
    html = client.get("/documents").text
    assert "unavailable" in html.lower()
    assert "/documents/1/scan" not in html  # no dead button offered
