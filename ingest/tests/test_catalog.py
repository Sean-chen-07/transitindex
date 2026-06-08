"""Offline tests for the PDF catalog: filename classification + storage sync.

A FakeStorage stands in for Supabase Storage so no network/creds are needed.
Asserts the manifest-derived classification (incl. the tricky supplement and
community-report cases), that non-launch files are skipped not errored, that the
sync is idempotent and does not reset scan state, and that verify_uploads
catches a hash mismatch.
"""

from __future__ import annotations

from transitindex_ingest import catalog
from transitindex_ingest.catalog import DOC_TYPE_TO_SOURCE, classify_filename
from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.storage import sha256_hex


class FakeStorage:
    """In-memory stand-in for SupabaseStorage: dict of key -> bytes."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.bucket = "annual-reports"
        self.bucket_created = False

    def ensure_bucket(self, *, public: bool = False) -> None:
        self.bucket_created = True

    def upload(self, key: str, data: bytes, *, content_type: str = "application/pdf") -> None:
        self.objects[key] = data

    def download(self, key: str) -> bytes:
        return self.objects[key]


# --- classification ---------------------------------------------------------


def test_classify_basic_transit_and_city():
    assert classify_filename("ttc-2019.pdf") == catalog.DocSpec("ttc", 2019, "annual_report", "T")
    assert classify_filename("calgary-transit-2022.pdf") == catalog.DocSpec(
        "calgary-transit", 2022, "financial_statement", "C"
    )


def test_classify_supplements_beat_parent_prefix():
    # 'edmonton-ets-service-plan' must win over the shorter 'edmonton-ets'.
    assert classify_filename("edmonton-ets-service-plan-2021.pdf") == catalog.DocSpec(
        "edmonton-ets", 2021, "service_plan", "T"
    )
    assert classify_filename("edmonton-ets-2021.pdf") == catalog.DocSpec(
        "edmonton-ets", 2021, "financial_statement", "C"
    )
    assert classify_filename("miway-business-plan-2020.pdf") == catalog.DocSpec(
        "miway", 2020, "business_plan", "T"
    )


def test_classify_community_reports_special_cased():
    assert classify_filename("miway-2024-community-report.pdf") == catalog.DocSpec(
        "miway", 2024, "community_report", "T"
    )
    assert classify_filename("miway-2025.pdf") == catalog.DocSpec(
        "miway", 2025, "community_report", "T"
    )
    # plain miway-<year> is the city's financial statement
    assert classify_filename("miway-2022.pdf") == catalog.DocSpec(
        "miway", 2022, "financial_statement", "C"
    )


def test_non_launch_files_are_skipped():
    for fn in ("brampton-transit.pdf", "halifax-transit.pdf", "york-region-transit.pdf"):
        assert classify_filename(fn) is None


def test_every_doc_type_maps_to_a_source_document_type():
    # Each catalog doc_type the classifier can emit must map to a valid
    # core.source_documents.document_type for the scan path.
    emitted = {
        "annual_report", "financial_statement", "service_plan",
        "business_plan", "community_report",
    }
    assert emitted <= set(DOC_TYPE_TO_SOURCE)


# --- sync + verify (with FakeStorage and a temp PDF dir) --------------------


def _write_pdfs(tmp_path, names):
    for n in names:
        (tmp_path / n).write_bytes(b"%PDF-1.4 " + n.encode())


def test_sync_uploads_recognised_and_skips_others(tmp_path):
    _write_pdfs(tmp_path, ["ttc-2019.pdf", "miway-2025.pdf", "brampton-transit.pdf"])
    repo = InMemoryRepository()
    storage = FakeStorage()

    summary = catalog.sync_local_pdfs(repo, storage, tmp_path)

    assert summary["uploaded"] == 2
    assert storage.bucket_created is True
    assert set(storage.objects) == {"ttc/ttc-2019.pdf", "miway/miway-2025.pdf"}
    assert [s[0] for s in summary["skipped"]] == ["brampton-transit.pdf"]

    docs = repo.list_documents()
    assert len(docs) == 2
    ttc = next(d for d in docs if d.storage_key == "ttc/ttc-2019.pdf")
    assert ttc.file_hash == sha256_hex((tmp_path / "ttc-2019.pdf").read_bytes())
    assert ttc.scan_status == "unscanned"


def test_sync_is_idempotent_and_preserves_scan_state(tmp_path):
    _write_pdfs(tmp_path, ["ttc-2019.pdf"])
    repo = InMemoryRepository()
    storage = FakeStorage()

    catalog.sync_local_pdfs(repo, storage, tmp_path)
    doc = repo.list_documents()[0]
    repo.mark_document_scanned(doc.id, source_document_id=None, staged_count=5)

    # Re-sync the same folder: must not create a duplicate or reset the scan.
    catalog.sync_local_pdfs(repo, storage, tmp_path)
    docs = repo.list_documents()
    assert len(docs) == 1
    assert docs[0].scan_status == "scanned"
    assert docs[0].staged_count == 5


def test_verify_uploads_detects_mismatch(tmp_path):
    _write_pdfs(tmp_path, ["ttc-2019.pdf"])
    repo = InMemoryRepository()
    storage = FakeStorage()
    catalog.sync_local_pdfs(repo, storage, tmp_path)

    assert catalog.verify_uploads(repo, storage)["ok"] is True

    # Corrupt the cloud copy -> verify must fail (and so we must NOT delete locals).
    storage.objects["ttc/ttc-2019.pdf"] = b"%PDF-corrupted"
    result = catalog.verify_uploads(repo, storage)
    assert result["ok"] is False
    assert result["mismatches"] == ["ttc/ttc-2019.pdf"]
