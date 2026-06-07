"""Aggregate per-mode fleet sizes into a rail-weighted `fleet_capacity`.

For one agency + reporting period this sums, per service_scope:

    fleet_capacity = Σ  capacity_weight(mode) × fleet_size(mode)

over the modes that have BOTH a non-null `capacity_weight`
(`refdata.MODE_CAPACITY_WEIGHT`, mirroring core.modes) AND a present per-mode
`fleet_size` value in that (agency, period, scope). A metro car is thus not
equated with a bus; ferry / paratransit / on_demand (NULL weight) are excluded.

The result is written at mode_id = None (a scope-level aggregate, not a per-mode
row) as a DERIVED value via `repo.insert_derived_value` with the summed per-mode
`fleet_size` rows as provenance (equation_code = `mode_weighted_fleet`).

Mirrors `jobs/rollup.py`: per-(scope) partitioning, provenance recording, and the
dispute-proof "write into an EMPTY slot only, NEVER overwrite a sourced value"
rule (a sourced fleet_capacity is left untouched). Re-running is idempotent via
the repo's one-current/supersede chain.
"""

from __future__ import annotations

from decimal import Decimal
from typing import NamedTuple

from ..equations import MODE_WEIGHTED_FLEET
from ..refdata import METRICS, MODE_CAPACITY_WEIGHT
from .derived_recompute import weakest_quality


class FleetCapacityWritten(NamedTuple):
    """The derived fleet_capacity ids written and the service_scopes they covered."""

    value_ids: list[int]
    scopes: list[str]


def fleet_capacity_aggregate(repo, agency_slug: str, period_id: int) -> FleetCapacityWritten:
    """Compute + write `fleet_capacity` for one agency + period.

    Partitions the agency's current per-mode `fleet_size` rows by service_scope and
    sums capacity_weight × fleet_size over the weighted modes present in each scope.
    Writes one derived value per scope (mode_id = None) into an EMPTY slot, citing
    the exact per-mode fleet_size rows; a scope whose fleet_capacity is already
    sourced is left untouched. Returns the ids written and the scopes covered.
    """
    agency_id = repo.agency_id(agency_slug)
    fleet_size_mid = repo.metric_id("fleet_size")
    capacity_mid = repo.metric_id("fleet_capacity")

    # Map each weighted mode's id -> its weight (skip modes with a NULL weight).
    weight_by_mode_id: dict[int, int] = {}
    for code, weight in MODE_CAPACITY_WEIGHT.items():
        weight_by_mode_id[repo.mode_id(code)] = weight

    # Gather per-mode fleet_size rows for this agency+period, grouped by scope.
    by_scope: dict[str, list] = {}
    for v in repo.list_current_values_for_agency_period(agency_id, period_id):
        if v.metric_id != fleet_size_mid or v.mode_id is None:
            continue
        if v.mode_id not in weight_by_mode_id:
            continue  # mode has no capacity_weight -> excluded from the aggregation
        by_scope.setdefault(v.service_scope, []).append(v)

    meta = METRICS["fleet_capacity"]
    value_ids: list[int] = []
    scopes: list[str] = []

    for scope in sorted(by_scope):
        rows = by_scope[scope]
        # Never overwrite a sourced (or any current) fleet_capacity for this scope.
        if repo.get_current_metric_value(
            agency_id, capacity_mid, period_id, None, scope
        ) is not None:
            continue
        total = sum(
            (Decimal(weight_by_mode_id[v.mode_id]) * v.value for v in rows), Decimal(0)
        )
        vid = repo.insert_derived_value(
            agency_id=agency_id,
            metric_id=capacity_mid,
            reporting_period_id=period_id,
            mode_id=None,
            service_scope=scope,
            value=total,
            unit=meta["unit"],
            quality=weakest_quality([v.quality for v in rows]),
            equation_code=MODE_WEIGHTED_FLEET,
            input_value_ids=[v.id for v in rows],
            currency="CAD" if meta["unit_type"] == "currency" else None,
            comparable_flag=True,
        )
        value_ids.append(vid)
        scopes.append(scope)

    return FleetCapacityWritten(value_ids=value_ids, scopes=scopes)
