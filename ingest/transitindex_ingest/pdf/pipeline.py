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

from ..contract import COST_BASES, SERVICE_SCOPES, DocumentType, License, MetricValueRecord, SourceRef
from ..db.repository import Repository
from ..periods import annual_period_from_end_year, monthly_period
from ..refdata import RATED_METRICS
from ..validation import validate_cohort
from .extract import Page
from .extractor import Extractor, ExtractionRequest, LegacyTextExtractor
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
        # The extractor names an annual figure by the year its reporting period
        # ENDS in (a fiscal agency's "year ending March 2024" comes back as
        # 2024). annual_period_from_end_year translates that to the right fiscal
        # span (FY2023-24) for the two fiscal agencies and is a no-op for the
        # 19 calendar agencies.
        return annual_period_from_end_year(agency_slug, ev.period_year)
    raise ValueError(f"unsupported period_kind: {ev.period_kind!r}")


def _notes_for(ev: ExtractedValue) -> Optional[str]:
    """Combine the value's note, printed line label, and verbatim source_quote."""
    parts: list[str] = []
    if ev.note:
        parts.append(ev.note)
    if ev.printed_label:
        parts.append(f'label: "{ev.printed_label}"')
    if ev.source_quote:
        parts.append(f'quote: "{ev.source_quote}"')
    return " | ".join(parts) if parts else None


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
        table_reference=ev.table_reference,
        confidence=ev.confidence,
    )
    return MetricValueRecord(
        agency_slug=agency_slug,
        metric_code=ev.metric_code,
        period_type=period.period_type,
        period_start=period.start,
        period_end=period.end,
        period_label=period.label,
        # Extraction-only scopes (mode_subset/city_wide) are filtered upstream;
        # anything else not contract-valid falls back to 'total'.
        service_scope=ev.service_scope if ev.service_scope in SERVICE_SCOPES else "total",
        # Expense-line accounting basis (Phase 3); anything unrecognized -> 'operating'.
        cost_basis=ev.cost_basis if ev.cost_basis in COST_BASES else "operating",
        value=ev.value,
        unit=ev.unit,
        quality="preliminary",
        currency="CAD" if ev.unit == "CAD" else None,
        # Only the five rated hero metrics carry ranks; everything else is view-only.
        comparable_flag=ev.metric_code in RATED_METRICS,
        notes=_notes_for(ev),
        source=source,
    )


def run_pdf(
    repo: Repository,
    pdf_path_or_pages: str | Path | list[Page],
    agency_slug: str,
    *,
    source_ref_meta: SourceRefMeta,
    extractor: Optional[Extractor] = None,
    llm_client: Optional[LLMClient] = None,
    validator: Optional[Validator] = None,
    doc_type: Optional[str] = None,
    author_label: Optional[str] = None,
    doc_year: Optional[int] = None,
) -> list[int]:
    """Run the Tier 2 pipeline; return the staged pending_value ids.

    Pass an `extractor=` (the default real path is ClaudePdfExtractor) or, for
    the legacy text-only path, an `llm_client=` -- exactly one of the two. A PDF
    path is read as raw bytes (handed to the extractor); a pre-extracted page
    list [(page_number, text), ...] flows through as `pages`. Resolves the
    agency up front so a bad slug fails fast. Each extracted value becomes a
    'pending' core.pending_values row, carrying validator flags, the per-period
    cohort reconciliation flags (validate_cohort), plus 'low_confidence' when
    confidence is below the threshold. Nothing here promotes to metric_values.
    """
    if extractor is not None and llm_client is not None:
        raise ValueError("pass either extractor= or llm_client=, not both")
    if extractor is None and llm_client is None:
        raise ValueError("run_pdf needs an extractor= (or a legacy llm_client=)")
    if extractor is None:
        extractor = LegacyTextExtractor(llm_client, EXTRACTION_SYSTEM_PROMPT)

    repo.agency_id(agency_slug)  # fail fast on unknown agency

    if isinstance(pdf_path_or_pages, (str, Path)):
        pdf_bytes = Path(pdf_path_or_pages).read_bytes()
        pages = None
    else:
        pdf_bytes = None
        pages = pdf_path_or_pages  # pre-extracted pages (offline / legacy)

    request = ExtractionRequest(
        agency_slug=agency_slug,
        pdf_bytes=pdf_bytes,
        pages=pages,
        doc_type=doc_type,
        author_label=author_label,
        doc_year=doc_year,
    )
    extracted = extractor.extract(request).values

    records = [(ev, _to_record(agency_slug, ev, source_ref_meta)) for ev in extracted]

    # Set-level reconciliation: group the batch by reporting period and run the
    # cohort identities (validate_cohort / sum_mismatch) over each group. A
    # cohort flag lands on EVERY record in its group, so the reviewer sees the
    # whole period that failed to reconcile.
    by_period: dict[tuple, list[MetricValueRecord]] = {}
    for _, record in records:
        key = (record.period_start, record.period_end, record.period_type)
        by_period.setdefault(key, []).append(record)
    cohort_flags = {key: validate_cohort(group) for key, group in by_period.items()}

    pending_ids: list[int] = []
    for ev, record in records:
        flags = validator(repo, record) if validator is not None else []
        flags = list(flags)
        for flag in cohort_flags[(record.period_start, record.period_end, record.period_type)]:
            if flag not in flags:
                flags.append(flag)
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
