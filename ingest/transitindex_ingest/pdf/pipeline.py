"""The PDF -> pending pipeline (Tier 2).

`run_pdf` ties extraction, the LLM, validation, and staging together. Every
value it produces lands in core.pending_values as review_status='pending':
Tier 2 NEVER auto-approves, so human review stays the only door into
core.metric_values (Invariant #1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Optional

from ..contract import DocumentType, License, MetricValueRecord, SourceRef
from ..db.repository import Repository
from ..periods import annual_period, monthly_period
from .extract import Page, extract_pages
from .llm import LOW_CONFIDENCE_THRESHOLD, EXTRACTION_SYSTEM_PROMPT, ExtractedValue, LLMClient

# A validator inspects the record and returns the flag strings it earned
# (e.g. 'yoy_spike', 'unit_mismatch'). Owned by the validation component; the
# pipeline just calls it if supplied.
Validator = Callable[[Repository, MetricValueRecord], list[str]]


@dataclass(frozen=True)
class SourceRefMeta:
    """The per-document provenance the caller knows up front (not per-value).

    document_type is the kind of PDF ('annual_report' / 'budget' / ...); the
    rest pins down the source_documents row. extraction_method, license, and
    confidence/page are filled per-value by the pipeline.
    """

    document_type: DocumentType
    title: Optional[str] = None
    source_url: Optional[str] = None
    publication_date: Optional[date] = None
    archive_uri: Optional[str] = None
    file_hash: Optional[str] = None
    license: License = "public_document"


def _period_for(agency_slug: str, ev: ExtractedValue):
    """Resolve an ExtractedValue's period_kind/year/month into a Period."""
    if ev.period_kind == "monthly":
        if ev.period_month is None:
            raise ValueError("monthly value missing period_month")
        return monthly_period(ev.period_year, ev.period_month)
    if ev.period_kind == "annual":
        return annual_period(agency_slug, ev.period_year)
    raise ValueError(f"unsupported period_kind: {ev.period_kind!r}")


def _to_record(agency_slug: str, ev: ExtractedValue, meta: SourceRefMeta) -> MetricValueRecord:
    """Map one ExtractedValue + document meta onto a MetricValueRecord."""
    period = _period_for(agency_slug, ev)
    source = SourceRef(
        document_type=meta.document_type,
        extraction_method="llm_assisted",
        title=meta.title,
        source_url=meta.source_url,
        publication_date=meta.publication_date,
        license=meta.license,
        archive_uri=meta.archive_uri,
        file_hash=meta.file_hash,
        page_number=ev.page_number,
        confidence=ev.confidence,
    )
    return MetricValueRecord(
        agency_slug=agency_slug,
        metric_code=ev.metric_code,
        period_type=period.period_type,
        period_start=period.start,
        period_end=period.end,
        period_label=period.label,
        service_scope="total",
        value=ev.value,
        unit=ev.unit,
        quality="preliminary",
        currency="CAD" if ev.unit == "CAD" else None,
        notes=ev.note,
        source=source,
    )


def run_pdf(
    repo: Repository,
    pdf_path_or_pages: str | Path | list[Page],
    agency_slug: str,
    *,
    source_ref_meta: SourceRefMeta,
    llm_client: LLMClient,
    validator: Optional[Validator] = None,
) -> list[int]:
    """Run the Tier 2 pipeline; return the staged pending_value ids.

    Accepts either a PDF path (extracted via pdfplumber) or pre-extracted pages
    [(page_number, text), ...]. Resolves the agency up front so a bad slug fails
    fast. Each extracted value becomes a 'pending' core.pending_values row,
    carrying validator flags plus 'low_confidence' when confidence is below the
    threshold. Nothing here promotes to metric_values.
    """
    repo.agency_id(agency_slug)  # fail fast on unknown agency

    if isinstance(pdf_path_or_pages, (str, Path)):
        pages = extract_pages(pdf_path_or_pages)
    else:
        pages = pdf_path_or_pages
    document_text = "\n\n".join(text for _, text in pages)

    extracted = llm_client.extract(EXTRACTION_SYSTEM_PROMPT, document_text, agency_slug)

    pending_ids: list[int] = []
    for ev in extracted:
        record = _to_record(agency_slug, ev, source_ref_meta)

        flags = validator(repo, record) if validator is not None else []
        flags = list(flags)
        if ev.confidence < LOW_CONFIDENCE_THRESHOLD and "low_confidence" not in flags:
            flags.append("low_confidence")

        source_document_id = repo.get_or_create_source_document(
            record.source, repo.agency_id(agency_slug)
        )
        pending_id = repo.insert_pending_value(
            record,
            source_document_id=source_document_id,
            review_status="pending",
            flags=flags,
        )
        pending_ids.append(pending_id)

    return pending_ids
