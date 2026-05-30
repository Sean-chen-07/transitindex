"""Gold-fixture evaluation of the PDF extractor.

`run_eval` scores what an extractor returned against hand-verified gold values
for one agency-year and reports two regression guards:

  * precision   -- of the values the extractor returned *clean* (no
                   low_confidence and no validation flag), the fraction that
                   land within the gold row's relative tolerance.
  * flag_recall -- of the gold rows marked should_flag, the fraction the
                   extractor actually flagged (low_confidence OR a validation
                   flag). Hard rows that slip through unflagged are the
                   regression we care most about.

`run_eval_through_pipeline` wires a `FakeLLMClient` (seeded from a scenario of
ExtractedValues) through the real Tier 2 `run_pdf`, reads the staged
core.pending_values back, and feeds them to `run_eval` -- so the eval exercises
the same extraction -> validation -> staging path production uses.

Pure stdlib. The FakeLLMClient needs no API and no PDF.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Optional

from ..db.memory import InMemoryRepository
from ..pdf.llm import ExtractedValue, FakeLLMClient
from ..pdf.pipeline import SourceRefMeta, Validator, run_pdf

# Flags that disqualify a returned value from the precision pool. low_confidence
# is added by the pipeline below the confidence threshold; the rest are the
# validation vocabulary (validation/flags.py).
_DISQUALIFYING_FLAGS: frozenset[str] = frozenset(
    {
        "low_confidence",
        "yoy_spike",
        "cross_source_disagreement",
        "unit_mismatch",
        "sum_mismatch",
    }
)


@dataclass(frozen=True)
class GoldRecord:
    """One hand-verified true value for a metric in the gold agency-year.

    `tolerance` is relative (|extracted - true| / |true| must not exceed it).
    `should_flag` marks a row a healthy extractor should flag for review
    (ambiguous / restated / unit-confusing figure).
    """

    metric_code: str
    true_value: Decimal
    unit: str
    tolerance: Decimal
    should_flag: bool


@dataclass(frozen=True)
class ExtractedAssessment:
    """The normalized view of what the extractor returned for one metric.

    `flags` carries everything the pipeline attached (low_confidence plus any
    validation flags). A value is 'clean' when it bears none of them.
    """

    metric_code: str
    value: Decimal
    flags: tuple[str, ...] = ()

    @property
    def is_flagged(self) -> bool:
        return any(f in _DISQUALIFYING_FLAGS for f in self.flags)


@dataclass(frozen=True)
class RowResult:
    """Per-gold-row outcome in the eval breakdown."""

    metric_code: str
    matched: bool  # did the extractor return this metric at all?
    extracted_value: Optional[Decimal]
    true_value: Decimal
    within_tolerance: bool
    should_flag: bool
    flagged: bool
    flags: tuple[str, ...]


@dataclass(frozen=True)
class EvalReport:
    """Scored eval result: the two guards plus the per-row breakdown."""

    precision: float
    flag_recall: float
    rows: tuple[RowResult, ...]

    @property
    def clean_count(self) -> int:
        """Number of returned-clean rows that fed the precision computation."""
        return sum(1 for r in self.rows if r.matched and not r.flagged)


def load_gold(path: str | Path) -> list[GoldRecord]:
    """Load a gold fixture JSON into GoldRecords (Decimals parsed from strings)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        GoldRecord(
            metric_code=r["metric_code"],
            true_value=Decimal(str(r["true_value"])),
            unit=r["unit"],
            tolerance=Decimal(str(r["tolerance"])),
            should_flag=bool(r["should_flag"]),
        )
        for r in data["records"]
    ]


def _within(extracted: Decimal, true: Decimal, tolerance: Decimal) -> bool:
    """Relative closeness: |extracted - true| / |true| <= tolerance.

    A zero true value requires an exact match (no relative band defined).
    """
    if true == 0:
        return extracted == 0
    return (extracted - true).copy_abs() / true.copy_abs() <= tolerance


def run_eval(
    gold_records: list[GoldRecord],
    extracted_values: list[ExtractedAssessment],
) -> EvalReport:
    """Score `extracted_values` against `gold_records`.

    Matches by metric_code (one assessment per metric; the last wins if an
    extractor somehow returns duplicates). Computes precision over the
    returned-clean values and flag_recall over the should_flag gold rows.
    """
    by_code = {a.metric_code: a for a in extracted_values}

    rows: list[RowResult] = []
    clean_total = 0
    clean_correct = 0
    flag_total = 0
    flag_caught = 0

    for gold in gold_records:
        assessment = by_code.get(gold.metric_code)
        matched = assessment is not None
        value = assessment.value if matched else None
        flagged = assessment.is_flagged if matched else False
        within = (
            matched and _within(assessment.value, gold.true_value, gold.tolerance)
        )

        # Precision pool: the values the extractor stood behind (clean).
        if matched and not flagged:
            clean_total += 1
            if within:
                clean_correct += 1

        # Flag-recall pool: gold rows we expect to be flagged for review.
        if gold.should_flag:
            flag_total += 1
            if flagged:
                flag_caught += 1

        rows.append(
            RowResult(
                metric_code=gold.metric_code,
                matched=matched,
                extracted_value=value,
                true_value=gold.true_value,
                within_tolerance=within,
                should_flag=gold.should_flag,
                flagged=flagged,
                flags=assessment.flags if matched else (),
            )
        )

    precision = (clean_correct / clean_total) if clean_total else 1.0
    flag_recall = (flag_caught / flag_total) if flag_total else 1.0
    return EvalReport(precision=precision, flag_recall=flag_recall, rows=tuple(rows))


def assessments_from_pending(repo: InMemoryRepository) -> list[ExtractedAssessment]:
    """Read the staged core.pending_values back as ExtractedAssessments.

    Reverse-resolves each pending row's metric_id to its code so gold rows
    (keyed by code) can match.
    """
    code_by_id = {m.id: m.code for m in repo.list_metrics()}
    return [
        ExtractedAssessment(
            metric_code=code_by_id[p.metric_id],
            value=p.value,
            flags=tuple(p.flags),
        )
        for p in repo.list_pending_values()
    ]


def run_eval_through_pipeline(
    gold_records: list[GoldRecord],
    scenario: list[ExtractedValue],
    agency_slug: str,
    pages,
    *,
    source_ref_meta: SourceRefMeta,
    validator: Optional[Validator] = None,
) -> EvalReport:
    """End-to-end: drive `scenario` through run_pdf, then run_eval the result.

    Uses a fresh InMemoryRepository and a FakeLLMClient seeded from `scenario`,
    so the eval covers the real extraction -> validation -> staging path with no
    API and no PDF. `validator` (optional) is the validation hook run_pdf calls;
    its flags merge with the pipeline's low_confidence flag.
    """
    repo = InMemoryRepository()
    run_pdf(
        repo,
        pages,
        agency_slug,
        source_ref_meta=source_ref_meta,
        llm_client=FakeLLMClient(scenario),
        validator=validator,
    )
    return run_eval(gold_records, assessments_from_pending(repo))
