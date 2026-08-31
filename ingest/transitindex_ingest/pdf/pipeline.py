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
from ..equations import EQUATIONS, SumEquation, cross_check_failures, metric_operands, solve
from ..jobs.derived_recompute import weakest_quality
from ..periods import annual_period_from_end_year, monthly_period
from ..refdata import METRICS, RATED_METRICS, agency_currency
from ..validation import DERIVED, SUMMED_FROM_COMPONENTS, cohorts, validate_cohort_records
from .extract import Page
from .extractor import Extractor, ExtractionRequest, LegacyTextExtractor
from .llm import (
    COMPONENT_SUM_MARKER,
    EXTRACTION_SYSTEM_PROMPT,
    LOW_CONFIDENCE_THRESHOLD,
    ExtractedValue,
    LLMClient,
)

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
    currency = agency_currency(agency_slug)
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
        # The agency's own reporting currency (USD for the US agencies), never a
        # blanket CAD -- validation.flags checks the unit against it.
        currency=currency if ev.unit == currency else None,
        # Only the five rated hero metrics carry ranks; everything else is view-only.
        comparable_flag=ev.metric_code in RATED_METRICS,
        notes=_notes_for(ev),
        source=source,
    )


# --- deterministic arithmetic over a staged cohort ---------------------------
#
# "The model transcribes, code calculates." Once a period's readings are shaped
# into records, `equations.solve` (a) cross-checks the identities the data fully
# determines and (b) back-solves the values the data determines but the page never
# printed. Both are pure Decimal arithmetic, and the solver never overwrites an
# observed value.

# Identities `validation.flags` already reconciles -- including the subsidy gap,
# which it deliberately checks at a WIDENED tolerance because the identity only
# holds exactly when the annual result is ~0. Re-checking them here at the
# solver's 2% would flag a healthy statement twice, at two different tolerances,
# so the solver cross-check covers only the rest of the catalog.
_FLAGS_OWNED_EQUATIONS: frozenset[str] = frozenset(
    {
        "expense_components",
        "expense_revenue_subsidy",
        "earned_revenue_components",
        "annual_surplus_deficit_def",
        "total_assets_identity",
        "accumulated_surplus_identity",
        "net_debt_def",
        "financial_assets_components",
        "liabilities_components",
        "non_financial_assets_components",
    }
)

# Only SUM back-solves are staged from the PDF path: recovering a printed-but-
# missing total, component, or residual is honest transcription arithmetic. The
# RATIO metrics (average_fare, farebox_recovery_ratio, ...) belong to
# jobs/derived_recompute.py, which recomputes them from APPROVED values -- staging
# them here would duplicate that job and pad the review queue.
_SUM_EQUATION_CODES: frozenset[str] = frozenset(
    eq.code for eq in EQUATIONS if isinstance(eq, SumEquation)
)


def _add_flag(flags_by_row: dict[int, list[str]], record: MetricValueRecord, flag: str) -> None:
    row = flags_by_row.setdefault(id(record), [])
    if flag not in row:
        row.append(flag)


def _derived_record(
    code: str,
    solved,
    cohort: dict[str, MetricValueRecord],
    meta: SourceRefMeta,
    agency_slug: str,
) -> MetricValueRecord:
    """Shape one back-solved value as a clearly-derived pending record.

    Follows `jobs/derived_recompute.py`'s conventions: quality is never stronger
    than the weakest input, only the rated metrics stay comparable, and the
    equation plus its input codes are recorded. The provenance carries no page
    number (nothing was printed) and the note says so in plain words, so the
    reviewer sees "derived, not printed" rather than a phantom reading.
    """
    anchor = next(iter(cohort.values()))
    inputs = [cohort[c] for c in solved.inputs if c in cohort]
    confidences = [
        r.source.confidence for r in inputs if r.source is not None and r.source.confidence is not None
    ]
    currency = agency_currency(agency_slug)
    unit = METRICS[code]["unit"].replace("CAD", currency)
    return MetricValueRecord(
        agency_slug=agency_slug,
        metric_code=code,
        period_type=anchor.period_type,
        period_start=anchor.period_start,
        period_end=anchor.period_end,
        period_label=anchor.period_label,
        service_scope=anchor.service_scope,
        cost_basis=inputs[0].cost_basis if inputs else "operating",
        value=solved.value,
        unit=unit,
        quality=weakest_quality([r.quality for r in inputs]),
        currency=currency if unit == currency else None,
        comparable_flag=code in RATED_METRICS,
        notes=(
            f"derived, not printed: {code} back-solved by `{solved.equation_code}` "
            f"from {', '.join(solved.inputs)}"
        ),
        source=SourceRef(
            document_type=meta.document_type,
            extraction_method="llm_assisted",
            title=meta.title,
            source_url=meta.source_url,
            publication_date=meta.publication_date,
            license=meta.license,
            archive_uri=meta.archive_uri,
            file_hash=meta.file_hash,
            confidence=min(confidences) if confidences else None,
        ),
    )


def _reconcile_period(
    records: list[MetricValueRecord], meta: SourceRefMeta, agency_slug: str
) -> tuple[dict[int, list[str]], list[MetricValueRecord]]:
    """Row-scoped cohort flags plus the values the solver can back-solve.

    Returns `({id(record): flags}, [derived records])`. Flags land ONLY on the
    records that took part in a failing identity -- a broken balance-sheet split
    no longer stamps `sum_mismatch` on an unrelated ridership row in the same
    period.
    """
    flags_by_row = dict(validate_cohort_records(records))
    derived: list[MetricValueRecord] = []

    for cohort in cohorts(records):
        result = solve({code: rec.value for code, rec in cohort.items()})

        # (i) cross-check the identities validation.flags does not already own.
        for eq, flag in cross_check_failures(result.values):
            if eq.code in _FLAGS_OWNED_EQUATIONS:
                continue
            for code in metric_operands(eq):
                rec = cohort.get(code)
                if rec is not None:
                    _add_flag(flags_by_row, rec, flag)

        # (ii) stage what the data determines but the page never printed.
        for code, solved in result.values.items():
            if solved.origin != "solved" or solved.equation_code not in _SUM_EQUATION_CODES:
                continue
            if code not in METRICS:
                continue
            derived.append(_derived_record(code, solved, cohort, meta, agency_slug))

    return flags_by_row, derived


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
    'pending' core.pending_values row, carrying validator flags, the ROW-SCOPED
    cohort reconciliation flags (only the records that took part in a failing
    identity), plus 'low_confidence' when confidence is below the threshold.
    `equations.solve` then back-solves whatever the readings determine but the
    page never printed; those land as extra pending rows whose notes say
    "derived, not printed". Nothing here promotes to metric_values.
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

    # Set-level reconciliation: group the batch by reporting period, then run the
    # cohort identities and the deterministic solver over each period's consistent
    # (service_scope, cost_basis) cohorts. Flags land ONLY on the records that took
    # part in a failing identity, and the solver's back-solved values are staged
    # afterwards as clearly-derived rows.
    by_period: dict[tuple, list[MetricValueRecord]] = {}
    for _, record in records:
        key = (record.period_start, record.period_end, record.period_type)
        by_period.setdefault(key, []).append(record)

    row_flags: dict[int, list[str]] = {}
    derived: list[MetricValueRecord] = []
    for group in by_period.values():
        group_flags, group_derived = _reconcile_period(group, source_ref_meta, agency_slug)
        row_flags.update(group_flags)
        derived.extend(group_derived)

    agency_id = repo.agency_id(agency_slug)
    pending_ids: list[int] = []

    def _stage(record: MetricValueRecord, flags: list[str]) -> None:
        source_document_id = repo.get_or_create_source_document(record.source, agency_id)
        pending_ids.append(
            repo.insert_pending_value(
                record,
                source_document_id=source_document_id,
                review_status="pending",
                flags=flags,
            )
        )

    for ev, record in records:
        flags = list(validator(repo, record)) if validator is not None else []
        for flag in row_flags.get(id(record), ()):
            if flag not in flags:
                flags.append(flag)
        if ev.confidence < LOW_CONFIDENCE_THRESHOLD and "low_confidence" not in flags:
            flags.append("low_confidence")
        # A staged row keeps no notes, so "code added the printed sub-lines" has to
        # reach the reviewer as a flag.
        if ev.note and COMPONENT_SUM_MARKER in ev.note and SUMMED_FROM_COMPONENTS not in flags:
            flags.append(SUMMED_FROM_COMPONENTS)
        _stage(record, flags)

    for record in derived:
        flags = list(validator(repo, record)) if validator is not None else []
        flags.append(DERIVED)
        confidence = record.source.confidence if record.source is not None else None
        if confidence is not None and confidence < LOW_CONFIDENCE_THRESHOLD:
            if "low_confidence" not in flags:
                flags.append("low_confidence")
        _stage(record, flags)

    return pending_ids
