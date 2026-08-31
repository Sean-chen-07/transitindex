"""Validation / flagging engine.

Pure-stdlib functions that inspect `MetricValueRecord`s and return the
validation flag strings (text[]) the staging layer stores on a pending value.
See `flags` for the individual checks and the `validate` / `validate_cohort`
composers.
"""

from __future__ import annotations

from .flags import (
    DERIVED,
    SUMMED_FROM_COMPONENTS,
    cohorts,
    cross_source_disagreement,
    sum_mismatch,
    sum_mismatch_records,
    unit_mismatch,
    validate,
    validate_cohort,
    validate_cohort_records,
    yoy_spike,
)

__all__ = [
    "DERIVED",
    "SUMMED_FROM_COMPONENTS",
    "yoy_spike",
    "cross_source_disagreement",
    "unit_mismatch",
    "sum_mismatch",
    "sum_mismatch_records",
    "cohorts",
    "validate",
    "validate_cohort",
    "validate_cohort_records",
]
