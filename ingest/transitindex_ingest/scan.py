"""Scan one cataloged PDF: fetch from cloud storage -> extract -> stage.

This is the integration point the "Scan" button calls. It reuses the existing
Tier-2 pipeline (pdf.pipeline.run_pdf) unchanged -- the only new work is pulling
the PDF from storage into a temp file and recording the outcome on the
core.documents row. Nothing here promotes; extracted values land in
core.pending_values for human review, exactly as a local `pdf` run would.

The PDF never persists on local disk: it is written to a temp file only for the
duration of the call, then deleted (fetch -> scan -> discard).
"""

from __future__ import annotations

import os
import tempfile
from typing import Optional

from .catalog import DOC_TYPE_TO_SOURCE
from .config import load_config
from .refdata import AGENCIES


def _slug_for_agency_id(repo, agency_id: int) -> Optional[str]:
    """Reverse the seeded slug->id map (same approach as the review app)."""
    for slug in AGENCIES:
        try:
            if repo.agency_id(slug) == agency_id:
                return slug
        except ValueError:
            continue
    return None


def scan_document(repo, storage, document_id: int, *, extractor=None, cfg=None) -> dict:
    """Scan the cataloged document, staging values into core.pending_values.

    Returns {"ok": bool, "staged_count": int, "error": str|None}. On any
    failure the catalog row is flipped to scan_status='failed' with the message
    and ok=False is returned (this never raises, so a UI caller stays alive).
    """
    doc = repo.get_document(document_id)
    if doc is None:
        return {"ok": False, "staged_count": 0, "error": f"unknown document id {document_id}"}

    cfg = cfg or load_config()

    try:
        # Lazy imports: the heavy real-PDF path (anthropic/markitdown/pypdf) loads only here.
        from .pdf.chunked_hybrid import ChunkedHybridExtractor
        from .pdf.pipeline import SourceRefMeta, run_pdf

        agency_slug = _slug_for_agency_id(repo, doc.agency_id)
        if agency_slug is None:
            raise RuntimeError(f"could not resolve a slug for agency_id {doc.agency_id}")

        if extractor is None:
            if not cfg.anthropic_api_key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set -- the extractor calls the Anthropic API."
                )
            # Default scan: chunked hybrid -- markitdown text (split into <=500-line,
            # table-safe chunks) + the scanned pages as batched images. Never sends
            # the whole PDF at once (see pdf/chunked_hybrid.py).
            extractor = ChunkedHybridExtractor(cfg.anthropic_api_key)

        data = storage.download(doc.storage_key)

        meta = SourceRefMeta(
            document_type=DOC_TYPE_TO_SOURCE.get(doc.doc_type, "annual_report"),
            title=doc.storage_key,
            source_url=doc.source_url,
            archive_uri=doc.storage_key,  # the cloud key IS the archived location
            file_hash=doc.file_hash,
        )

        # Write to a temp file so the unchanged run_pdf path reads it, then delete.
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            tmp.write(data)
            tmp.close()
            pending_ids = run_pdf(
                repo,
                tmp.name,
                agency_slug,
                source_ref_meta=meta,
                extractor=extractor,
                doc_type=doc.doc_type,
                author_label=doc.author_label,
                doc_year=doc.year,
            )
        finally:
            os.unlink(tmp.name)
    except Exception as exc:  # surface as a recorded failure, never crash the caller
        msg = f"{type(exc).__name__}: {exc}"
        repo.mark_document_failed(document_id, error=msg[:500])
        return {"ok": False, "staged_count": 0, "error": msg}

    # source_document_id linkage is left to a later enhancement: run_pdf creates
    # the source_documents row internally and doesn't return it, and our PDFs
    # often lack a source_url to dedupe on. The pending_values it staged already
    # carry that provenance.
    repo.mark_document_scanned(
        document_id, source_document_id=None, staged_count=len(pending_ids)
    )
    return {"ok": True, "staged_count": len(pending_ids), "error": None}
