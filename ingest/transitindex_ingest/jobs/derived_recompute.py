"""Recompute the 6 derived ratio metrics from same-period source inputs.

A derived metric is computed STRICTLY from other metric values in the *same*
agency and *same* reporting period (never across years, never across agencies).
`compute_derived` is the pure math -- given a `{metric_code: Decimal}` input
map it returns `{derived_code: Decimal}`, skipping any derived metric whose
inputs are missing or whose denominator is zero (so we never divide by zero and
never fabricate a value). `recompute_derived` wires that math to a Repository:
it reads the agency's current system-wide values for the period, computes the
ratios, and writes each via `insert_metric_value`, whose one-current/supersede
semantics make re-running idempotent (a corrected input restates the ratio and
supersedes the stale one).
"""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple

from ..refdata import METRICS

# The 6 derived metrics, as (code, numerator-builder, denominator input).
# Each entry: derived_code -> (callable(inputs) -> Decimal numerator, denom_code).
# Numerators are plain expressions over the input map; denominators are a single
# input code so the zero-check is uniform.
_DERIVED: dict[str, tuple] = {
    "average_fare": (("operating_revenue",), "annual_ridership"),
    "trips_per_revenue_hour": (("annual_ridership",), "revenue_service_hours"),
    "farebox_recovery_ratio": (("operating_revenue",), "operating_expenses"),
    "cost_per_rider": (("operating_expenses",), "annual_ridership"),
    "cost_per_hour": (("operating_expenses",), "revenue_service_hours"),
    "subsidy_per_rider": (("operating_expenses", "operating_revenue"), "annual_ridership"),
}


def _numerator(code: str, inputs: dict[str, Decimal]) -> Decimal:
    """Build a derived metric's numerator from same-period inputs."""
    if code == "subsidy_per_rider":
        return inputs["operating_expenses"] - inputs["operating_revenue"]
    # All other derived metrics use a single source value as the numerator.
    numer_codes, _denom = _DERIVED[code]
    return inputs[numer_codes[0]]


class RecomputeResult(NamedTuple):
    """Outcome of `recompute_derived`: written ids plus non-fatal warnings."""

    ids: list[int]
    warnings: list[str]


def compute_derived(inputs: dict[str, Decimal]) -> dict[str, Decimal]:
    """Compute every derivable ratio from a `{metric_code: Decimal}` map.

    Skips a derived metric when any required input is absent or when its
    denominator is zero. Returns `{derived_code: Decimal}`; never raises on
    missing data, never divides by zero.
    """
    out: dict[str, Decimal] = {}
    for code, (numer_codes, denom_code) in _DERIVED.items():
        required = (*numer_codes, denom_code)
        if any(r not in inputs for r in required):
            continue
        denom = inputs[denom_code]
        if denom == 0:
            continue
        out[code] = _numerator(code, inputs) / denom
    return out


def _warnings_for(results: dict[str, Decimal]) -> list[str]:
    """Sanity checks that flag (not reject) implausible derived values."""
    warnings: list[str] = []
    fr = results.get("farebox_recovery_ratio")
    if fr is not None and fr > Decimal(1):
        warnings.append(f"farebox_recovery_ratio>1.0 ({fr})")
    for code in ("cost_per_rider", "cost_per_hour"):
        val = results.get(code)
        if val is not None and val < 0:
            warnings.append(f"{code} is negative ({val})")
    return warnings


def recompute_derived(repo, agency_slug: str, period_id: int) -> RecomputeResult:
    """Recompute the agency's derived metrics for one period and write them.

    Reads the agency's current system-wide (mode_id None) values in `period_id`,
    derives the ratios from those same-period inputs, and writes each via
    `repo.insert_metric_value` with quality='verified'. The repo's
    one-current/supersede semantics make this idempotent: a re-run after a
    corrected input restates the prior ratio rather than leaving it stale.
    Returns the new metric_value ids and any non-fatal sanity warnings.
    """
    agency_id = repo.agency_id(agency_slug)
    rows = [
        r
        for r in repo.list_current_values_for_agency_period(agency_id, period_id)
        if r.mode_id is None
    ]

    # Source inputs for the formulas, keyed by metric code. Derived metrics that
    # may already be present are ignored as inputs -- ratios feed off sources.
    metric_code = {repo.metric_id(code): code for code in METRICS}
    inputs: dict[str, Decimal] = {}
    scopes: set[str] = set()
    for r in rows:
        code = metric_code.get(r.metric_id)
        if code is None or METRICS[code]["is_derived"]:
            continue
        inputs[code] = r.value
        scopes.add(r.service_scope)

    results = compute_derived(inputs)

    # Write every result under the scope the inputs were reported at. Inputs
    # share one scope in practice (system_wide for StatCan, total for others);
    # fall back to system_wide when there are no inputs to read a scope from.
    scope = scopes.pop() if len(scopes) == 1 else "system_wide"

    ids: list[int] = []
    for code, value in results.items():
        meta = METRICS[code]
        ids.append(
            repo.insert_metric_value(
                agency_id=agency_id,
                metric_id=repo.metric_id(code),
                reporting_period_id=period_id,
                mode_id=None,
                service_scope=scope,
                value=value,
                unit=meta["unit"],
                quality="verified",
                currency="CAD" if meta["unit_type"] == "currency" else None,
            )
        )

    return RecomputeResult(ids=ids, warnings=_warnings_for(results))
