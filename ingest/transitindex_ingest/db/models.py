"""Lightweight read-model dataclasses returned by the repository.

These are plain views of the corresponding core.* rows -- what queries hand
back, distinct from the write-side `MetricValueRecord` in contract.py. Pure
stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True)
class Metric:
    """A row of core.metrics."""

    id: int
    code: str
    display_name: str
    unit: str
    unit_type: Optional[str]
    is_derived: bool
    formula: Optional[str]
    higher_is_better: Optional[bool]


@dataclass(frozen=True)
class ReportingPeriod:
    """A row of core.reporting_periods."""

    id: int
    agency_id: int
    period_type: str
    start_date: date
    end_date: date
    label: str


@dataclass(frozen=True)
class SourceDocument:
    """A row of core.source_documents."""

    id: int
    agency_id: Optional[int]
    document_type: str
    title: Optional[str]
    publication_date: Optional[date]
    source_url: Optional[str]
    archive_uri: Optional[str]
    file_hash: Optional[str]
    license: Optional[str]


@dataclass(frozen=True)
class MetricValue:
    """A row of core.metric_values (the promoted, current-or-superseded value)."""

    id: int
    agency_id: int
    metric_id: int
    reporting_period_id: int
    mode_id: Optional[int]
    service_scope: str
    value: Decimal
    unit: str
    currency: Optional[str]
    quality: str
    comparable_flag: bool
    crosscheck_value: Optional[Decimal]
    restatement_of_id: Optional[int]
    is_current: bool
    notes: Optional[str]


@dataclass(frozen=True)
class PendingValue:
    """A row of core.pending_values (the staging door before metric_values)."""

    id: int
    agency_id: int
    metric_id: int
    reporting_period_id: int
    mode_id: Optional[int]
    service_scope: str
    value: Decimal
    unit: str
    currency: Optional[str]
    quality: str
    comparable_flag: bool
    crosscheck_value: Optional[Decimal]
    source_document_id: Optional[int]
    page_number: Optional[int]
    table_reference: Optional[str]
    extraction_method: Optional[str]
    confidence: Optional[Decimal]
    review_status: str
    flags: list[str]
    reviewer_notes: Optional[str]


@dataclass(frozen=True)
class MetricRankRow:
    """A row of core.metric_ranks (materialized, single-period ranking)."""

    agency_id: int
    rank: int
    denominator: int
    direction: str
