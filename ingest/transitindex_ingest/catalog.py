"""The PDF catalog: classify collected PDFs and sync them to cloud storage.

`classify_filename` maps a local PDF filename to its (agency, year, doc_type,
author_label) using rules derived from pdfs/MANIFEST.md. `sync_local_pdfs`
uploads each launch-relevant PDF to Supabase Storage and upserts a
core.documents row. Files that aren't part of the launch set (no year, or an
agency that isn't seeded) are skipped, not errors.

Pure stdlib here; the storage client and repository are injected.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .storage import sha256_hex

# Catalog doc_type -> the narrower core.source_documents.document_type the scan
# pipeline must use (that column has its own CHECK constraint). City audited
# financials and community reports ride in as 'annual_report'; forward-looking
# service/business plans as 'budget'.
DOC_TYPE_TO_SOURCE = {
    "annual_report": "annual_report",
    "financial_statement": "annual_report",
    "service_plan": "budget",
    "business_plan": "budget",
    "community_report": "annual_report",
}


@dataclass(frozen=True)
class DocSpec:
    """The classification of one PDF filename."""

    agency_slug: str
    year: int
    doc_type: str
    author_label: str  # 'T' transit-own / 'C' city


# (stem prefix -> (agency_slug, doc_type, author_label)). The LONGEST matching
# prefix wins, so 'edmonton-ets-service-plan' beats 'edmonton-ets'. Derived from
# pdfs/MANIFEST.md's labeled inventory.
_PREFIX_RULES: list[tuple[str, tuple[str, str, str]]] = [
    ("ttc",                       ("ttc",                "annual_report",       "T")),
    ("translink",                 ("translink",          "annual_report",       "T")),
    ("metrolinx",                 ("metrolinx",          "annual_report",       "T")),
    ("bc-transit",                ("bc-transit",         "annual_report",       "T")),
    ("calgary-transit",           ("calgary-transit",    "financial_statement", "C")),
    ("burlington-transit",        ("burlington-transit", "financial_statement", "C")),
    ("oc-transpo",                ("oc-transpo",         "financial_statement", "C")),
    ("edmonton-ets-service-plan", ("edmonton-ets",       "service_plan",        "T")),
    ("edmonton-ets",              ("edmonton-ets",       "financial_statement", "C")),
    # STM authors its own reports [T]: stm-activity-<year> is the activity/annual
    # report; the shorter 'stm' is its audited "Rapport financier annuel".
    ("stm-activity",              ("stm",                "annual_report",       "T")),
    ("stm",                       ("stm",                "financial_statement", "T")),
    ("miway-business-plan",       ("miway",              "business_plan",       "T")),
    ("miway",                     ("miway",              "financial_statement", "C")),
]

# MiWay's "Report to the Community" files are MiWay-authored [T] community
# reports, not the city's [C] financial report -- matched by exact stem so the
# generic 'miway' rule doesn't mislabel them (MANIFEST).
_COMMUNITY_REPORT_STEMS = {"miway-2024-community-report", "miway-2025"}

_YEAR_RE = re.compile(r"(?:19|20)\d{2}")


def classify_filename(filename: str) -> Optional[DocSpec]:
    """Classify a PDF filename, or return None if it isn't a launch-set file.

    None means: no 4-digit year in the name (e.g. brampton-transit.pdf) -- those
    are the pre-existing non-launch files the manifest leaves as-is.
    """
    stem = filename[:-4] if filename.lower().endswith(".pdf") else filename
    m = _YEAR_RE.search(stem)
    if m is None:
        return None
    year = int(m.group(0))

    if stem in _COMMUNITY_REPORT_STEMS:
        return DocSpec("miway", year, "community_report", "T")

    best: Optional[tuple[str, tuple[str, str, str]]] = None
    for prefix, spec in _PREFIX_RULES:
        if stem.startswith(prefix) and (best is None or len(prefix) > len(best[0])):
            best = (prefix, spec)
    if best is None:
        return None
    slug, doc_type, author = best[1]
    return DocSpec(slug, year, doc_type, author)


def storage_key_for(agency_slug: str, filename: str) -> str:
    """The object path within the bucket, e.g. 'ttc/ttc-2019.pdf'."""
    return f"{agency_slug}/{filename}"


def plan_local_pdfs(pdf_dir) -> tuple[list[tuple[str, DocSpec]], list[tuple[str, str]]]:
    """Classify every *.pdf in pdf_dir without uploading anything.

    Returns (recognised, skipped) where recognised is [(filename, DocSpec), ...]
    and skipped is [(filename, reason), ...].
    """
    recognised: list[tuple[str, DocSpec]] = []
    skipped: list[tuple[str, str]] = []
    for path in sorted(Path(pdf_dir).glob("*.pdf")):
        spec = classify_filename(path.name)
        if spec is None:
            skipped.append((path.name, "no launch year in name (not a launch-set file)"))
        else:
            recognised.append((path.name, spec))
    return recognised, skipped


def sync_local_pdfs(
    repo,
    storage,
    pdf_dir,
    *,
    ensure_bucket: bool = True,
    source_urls: Optional[dict[str, str]] = None,
) -> dict:
    """Upload each launch-relevant PDF to storage and upsert its catalog row.

    Idempotent: re-uploading overwrites the object and refreshes the catalog
    row's hash/size without touching its scan_status. Returns a summary dict.
    """
    if ensure_bucket:
        storage.ensure_bucket()

    source_urls = source_urls or {}
    uploaded = 0
    skipped: list[tuple[str, str]] = []
    rows: list[dict] = []

    for path in sorted(Path(pdf_dir).glob("*.pdf")):
        spec = classify_filename(path.name)
        if spec is None:
            skipped.append((path.name, "no launch year in name (not a launch-set file)"))
            continue
        try:
            agency_id = repo.agency_id(spec.agency_slug)
        except ValueError:
            skipped.append((path.name, f"agency {spec.agency_slug!r} not seeded"))
            continue

        data = path.read_bytes()
        key = storage_key_for(spec.agency_slug, path.name)
        storage.upload(key, data)
        doc_id = repo.upsert_document(
            agency_id=agency_id,
            year=spec.year,
            doc_type=spec.doc_type,
            author_label=spec.author_label,
            storage_key=key,
            source_url=source_urls.get(path.name),
            file_hash=sha256_hex(data),
            file_bytes=len(data),
        )
        uploaded += 1
        rows.append(
            {
                "id": doc_id,
                "filename": path.name,
                "agency": spec.agency_slug,
                "year": spec.year,
                "doc_type": spec.doc_type,
                "author": spec.author_label,
                "storage_key": key,
                "bytes": len(data),
            }
        )

    return {"uploaded": uploaded, "skipped": skipped, "rows": rows}


def verify_uploads(repo, storage) -> dict:
    """Download every cataloged file and confirm its bytes hash to the stored
    file_hash. Returns {ok, checked, mismatches:[...], missing_hash:[...]}.

    Used before deleting local copies: do not delete unless ok is True.
    """
    mismatches: list[str] = []
    missing_hash: list[str] = []
    checked = 0
    for doc in repo.list_documents():
        if not doc.file_hash:
            missing_hash.append(doc.storage_key)
            continue
        data = storage.download(doc.storage_key)
        checked += 1
        if sha256_hex(data) != doc.file_hash:
            mismatches.append(doc.storage_key)
    return {
        "ok": not mismatches and not missing_hash,
        "checked": checked,
        "mismatches": mismatches,
        "missing_hash": missing_hash,
    }
