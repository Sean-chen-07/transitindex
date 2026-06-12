"""Offline tests for scan_document (the Scan-button integration point).

Uses a FakeExtractor (canned ExtractedValues) and a FakeStorage so no Anthropic
API, no network, no creds. Asserts a successful scan stages values into
core.pending_values and flips the catalog row to 'scanned' with a staged_count;
that nothing reaches metric_values (Tier 2 invariant holds); and that a storage
failure is recorded as scan_status='failed' without raising.
"""

from __future__ import annotations

from decimal import Decimal

from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.pdf.extractor import (
    ExtractionRequest,
    ExtractionResult,
    FakeExtractor,
)
from transitindex_ingest.pdf.llm import ExtractedValue
from transitindex_ingest.scan import scan_document


class FakeStorage:
    def __init__(self, objects=None):
        self.objects = objects or {}

    def download(self, key: str) -> bytes:
        return self.objects[key]  # KeyError -> recorded as a failed scan


def _catalog_one(repo) -> int:
    return repo.upsert_document(
        agency_id=repo.agency_id("ttc"),
        year=2024,
        doc_type="annual_report",
        author_label="T",
        storage_key="ttc/ttc-2024.pdf",
        file_hash="deadbeef",
        file_bytes=10,
    )


def _values():
    return [
        ExtractedValue(
            metric_code="ridership",
            value=Decimal("250000000"),
            unit="count",
            period_kind="annual",
            period_year=2024,
            page_number=2,
            confidence=Decimal("0.95"),
        ),
        ExtractedValue(
            metric_code="operating_expenses",
            value=Decimal("2100000000"),
            unit="CAD",
            period_kind="annual",
            period_year=2024,
            page_number=5,
            confidence=Decimal("0.9"),
        ),
    ]


def test_successful_scan_stages_pending_and_marks_scanned():
    repo = InMemoryRepository()
    doc_id = _catalog_one(repo)
    storage = FakeStorage({"ttc/ttc-2024.pdf": b"%PDF-1.4 fake"})

    result = scan_document(
        repo, storage, doc_id, extractor=FakeExtractor(_values())
    )

    assert result == {"ok": True, "staged_count": 2, "error": None}
    assert len(repo.list_pending_values("pending")) == 2

    doc = repo.get_document(doc_id)
    assert doc.scan_status == "scanned"
    assert doc.staged_count == 2
    assert doc.scanned_at is not None

    # Tier 2 invariant: nothing promoted to metric_values by a scan.
    assert len(repo._values) == 0  # noqa: SLF001 - test introspection


def test_scan_failure_is_recorded_not_raised():
    repo = InMemoryRepository()
    doc_id = _catalog_one(repo)
    storage = FakeStorage(objects={})  # download() raises KeyError

    result = scan_document(repo, storage, doc_id, extractor=FakeExtractor(_values()))

    assert result["ok"] is False
    assert result["error"]  # a message was captured
    doc = repo.get_document(doc_id)
    assert doc.scan_status == "failed"
    assert doc.last_error
    assert len(repo.list_pending_values()) == 0


def test_unknown_document_id_is_reported():
    repo = InMemoryRepository()
    result = scan_document(repo, FakeStorage(), 999, extractor=FakeExtractor(_values()))
    assert result["ok"] is False
    assert "unknown document" in result["error"]


class _RecordingExtractor:
    """Captures the ExtractionRequest it receives, then returns canned values."""

    def __init__(self, values):
        self._values = list(values)
        self.request = None

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        self.request = request
        return ExtractionResult(values=list(self._values))


def test_scan_passes_catalog_doc_context_to_extractor():
    repo = InMemoryRepository()
    doc_id = _catalog_one(repo)  # doc_type='annual_report', author 'T', year 2024
    storage = FakeStorage({"ttc/ttc-2024.pdf": b"%PDF-1.4 fake"})
    extractor = _RecordingExtractor(_values())

    result = scan_document(repo, storage, doc_id, extractor=extractor)

    assert result["ok"] is True
    assert extractor.request is not None
    assert extractor.request.doc_type == "annual_report"
    assert extractor.request.author_label == "T"
    assert extractor.request.doc_year == 2024
