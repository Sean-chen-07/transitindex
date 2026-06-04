"""The value contract every component codes against.

`MetricValueRecord` is the single canonical shape a metric observation takes as
it travels through the pipeline: extracted -> validated -> staged in
core.pending_values -> (on approval) promoted to core.metric_values. `SourceRef`
captures the provenance that lands in core.source_documents /
core.metric_value_sources.

Both are pure-stdlib dataclasses. Fields map 1:1 onto the applied Postgres
schema (db/schema.sql). Identifiers are carried as slug/code/period tuples here;
the repository resolves them to integer foreign keys at write time.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

# --- Enum-ish field domains (mirror the CHECK constraints in db/schema.sql) ---

PeriodType = Literal["monthly", "quarterly", "annual_calendar", "annual_fiscal", "ytd"]
ServiceScope = Literal["conventional", "specialized", "total", "system_wide"]
Quality = Literal["verified", "preliminary", "estimated", "imputed"]
ExtractionMethod = Literal["manual", "llm_assisted", "structured_import", "statcan_passthrough"]
License = Literal[
    "statcan_open",
    "ogl_toronto",
    "ogl_ottawa",
    "ogl_calgary",
    "ogl_edmonton",
    "ogl_montreal",
    "ogl_metrovancouver",
    "ogl_mississauga",
    "ogl_hamilton",
    "public_document",
]
DocumentType = Literal[
    "annual_report",
    "quarterly_update",
    "budget",
    "ceo_report",
    "board_report",
    "statcan_table",
    "open_data_csv",
    "gtfs",
    "manual_entry",
    "press_release",
]

# Allowed-value sets, derived from the Literals above so they never drift.
PERIOD_TYPES: frozenset[str] = frozenset(PeriodType.__args__)
SERVICE_SCOPES: frozenset[str] = frozenset(ServiceScope.__args__)
QUALITIES: frozenset[str] = frozenset(Quality.__args__)
EXTRACTION_METHODS: frozenset[str] = frozenset(ExtractionMethod.__args__)
LICENSES: frozenset[str] = frozenset(License.__args__)
DOCUMENT_TYPES: frozenset[str] = frozenset(DocumentType.__args__)


@dataclass
class SourceRef:
    """Provenance for an extracted value: which document, where in it, and how.

    Resolves to a core.source_documents row plus the core.metric_value_sources
    link (page_number / table_reference / extraction_method / confidence).
    `source_url`+`document_type` are enough to identify/create the document;
    the rest is bookkeeping the repository persists.
    """

    document_type: DocumentType
    extraction_method: ExtractionMethod
    title: Optional[str] = None
    source_url: Optional[str] = None
    publication_date: Optional[date] = None
    license: Optional[License] = None
    archive_uri: Optional[str] = None
    file_hash: Optional[str] = None
    page_number: Optional[int] = None
    table_reference: Optional[str] = None
    confidence: Optional[Decimal] = None

    def __post_init__(self) -> None:
        _require(self.document_type, DOCUMENT_TYPES, "document_type")
        _require(self.extraction_method, EXTRACTION_METHODS, "extraction_method")
        if self.license is not None:
            _require(self.license, LICENSES, "license")
        if self.confidence is not None:
            self.confidence = _as_decimal(self.confidence, "confidence")
            if not (Decimal(0) <= self.confidence <= Decimal(1)):
                raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

    def to_dict(self) -> dict:
        """Plain-dict view (Decimal->str, date->ISO) for JSON/logging."""
        return _normalize(asdict(self))


@dataclass(frozen=True)
class MetricValueRecord:
    """One metric observation for (agency, metric, period[, mode], scope).

    Frozen: a record is an immutable extraction result. Identifiers are the
    stable business keys (agency_slug, metric_code, mode_code) plus a fully
    specified reporting period; the repository maps them to integer ids. `value`
    and `crosscheck_value` are Decimal; period bounds are `date`. `mode_code`
    None means a system-wide value (no mode breakdown) -- this is a concrete
    part of the uniqueness key, not "unknown".
    """

    agency_slug: str
    metric_code: str
    period_type: PeriodType
    period_start: date
    period_end: date
    period_label: str
    service_scope: ServiceScope
    value: Decimal
    unit: str
    quality: Quality
    mode_code: Optional[str] = None
    currency: Optional[str] = None
    comparable_flag: bool = True
    crosscheck_value: Optional[Decimal] = None
    notes: Optional[str] = None
    source: Optional[SourceRef] = None
    flags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        _require(self.period_type, PERIOD_TYPES, "period_type")
        _require(self.service_scope, SERVICE_SCOPES, "service_scope")
        _require(self.quality, QUALITIES, "quality")
        if not isinstance(self.period_start, date) or not isinstance(self.period_end, date):
            raise ValueError("period_start and period_end must be datetime.date")
        if self.period_end < self.period_start:
            raise ValueError("period_end must not precede period_start")
        # Coerce numerics to Decimal (frozen -> object.__setattr__).
        object.__setattr__(self, "value", _as_decimal(self.value, "value"))
        if self.crosscheck_value is not None:
            object.__setattr__(
                self, "crosscheck_value", _as_decimal(self.crosscheck_value, "crosscheck_value")
            )

    def to_dict(self) -> dict:
        """Plain-dict view (Decimal->str, date->ISO, nested source expanded)."""
        return _normalize(asdict(self))


# --- helpers ---


def _require(value: object, allowed: frozenset[str], field_name: str) -> None:
    if value not in allowed:
        raise ValueError(
            f"{field_name}={value!r} is not one of {sorted(allowed)}"
        )


def _as_decimal(value: object, field_name: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):  # bool is an int subclass; reject it explicitly
        raise ValueError(f"{field_name} must be numeric, got bool")
    if isinstance(value, (int, str)):
        try:
            return Decimal(value)
        except Exception as exc:  # noqa: BLE001 - re-raise as ValueError
            raise ValueError(f"{field_name} is not a valid Decimal: {value!r}") from exc
    if isinstance(value, float):
        # Avoid binary-float surprises: go through str.
        return Decimal(str(value))
    raise ValueError(f"{field_name} must be Decimal/int/str, got {type(value).__name__}")


def _normalize(obj: object) -> object:
    """Recursively convert Decimal->str and date->ISO for serialization."""
    if isinstance(obj, dict):
        return {k: _normalize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_normalize(v) for v in obj]
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, date):
        return obj.isoformat()
    return obj
