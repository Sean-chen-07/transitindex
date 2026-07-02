"""Recompute derived metric values by solving the equation graph.

For one agency + period this:
  1. reads the current values and PARTITIONS them by (mode_id, service_scope) --
     an income-statement ratio at `total` scope must never consume a
     `system_wide` input;
  2. seeds the solver with the OBSERVED values in each partition (current rows
     with NO derivation -- i.e. sourced or independently observed; prior solver
     output is excluded so it can be re-derived and superseded);
  3. solves the equation graph to a fixpoint (`equations.solve`), back-solving
     any unknown the data determines (e.g. expenses from farebox + revenue);
  4. writes every newly SOLVED value via `repo.insert_derived_value`, recording
     the equation + the exact input value rows (provenance) and a `quality`
     inherited from its inputs -- never stronger than its weakest input.

Cross-check and over-determination findings from the solver are returned as
warnings (for the review queue). Re-running is idempotent: a corrected input
restates the affected derived values via the repo's one-current/supersede chain.
"""

from __future__ import annotations

from typing import NamedTuple

from decimal import Decimal

from ..equations import ATTR_PREFIX, EQUATIONS, solve
from ..refdata import METRICS, RATED_METRICS

# Derivation equation codes produced by the WITHIN-PERIOD solver. A current value
# carrying one of these is prior solver output -> excluded from the seed so it is
# re-derived and superseded. Sourced values (no derivation) and cross-period
# aggregations (e.g. the period_rollup annual ridership) ARE valid seed inputs.
_WITHIN_PERIOD_CODES = frozenset(eq.code for eq in EQUATIONS)

# The efficiency ratios must consume the CUTA/NTD *operating* expense basis
# (amortization EXCLUDED), never a PSAB statement-of-operations total. When a
# cohort's operating_expenses is recorded on the 'psab_total' basis we normalize
# it to the operating basis (Phase 3):
#   rule (a) -- PREFERRED: if amortization is present, seed
#              operating = psab_total - amortization (auditable, fully comparable);
#   rule (b) -- fallback: no amortization to subtract, so we still compute the
#              ratios but mark every value that consumed the un-normalized expense
#              comparable_flag=False and flag it (a psab-basis ratio must never be
#              ranked against an operating-basis one).
_MIXED_COST_BASIS = "mixed_cost_basis"

# Weakest-wins ordering: a derived value never claims more certainty than its
# weakest input (rank 0 = strongest).
_QUALITY_RANK = {"verified": 0, "preliminary": 1, "estimated": 2, "imputed": 3}


def weakest_quality(qualities: list[str]) -> str:
    """The weakest (least certain) quality among inputs; 'verified' if none."""
    if not qualities:
        return "verified"
    return max(qualities, key=lambda q: _QUALITY_RANK.get(q, 0))


class RecomputeResult(NamedTuple):
    """Outcome of `recompute_derived`: written ids plus cross-check warnings."""

    ids: list[int]
    warnings: list[str]


def recompute_derived(repo, agency_slug: str, period_id: int) -> RecomputeResult:
    """Solve the equation graph for one agency+period and write the results.

    Partitions current values by (mode_id, service_scope), seeds each partition's
    OBSERVED values, solves to a fixpoint, and writes solved values with
    provenance + inherited quality. Returns the new ids and any cross-check /
    over-determination warnings.
    """
    agency_id = repo.agency_id(agency_slug)
    code_by_mid = {repo.metric_id(code): code for code in METRICS}
    rows = repo.list_current_values_for_agency_period(agency_id, period_id)

    # Partition by (mode_id, service_scope): each cohort solves independently.
    partitions: dict[tuple, list] = {}
    for r in rows:
        partitions.setdefault((r.mode_id, r.service_scope), []).append(r)

    ids: list[int] = []
    warnings: list[str] = []

    for (mode_id, scope), part in partitions.items():
        # Observed seed = current values WITHOUT a derivation row. Prior solver
        # output is skipped so it gets re-derived (and superseded) cleanly.
        observed: dict[str, object] = {}  # code -> MetricValue
        seed: dict[str, object] = {}  # code -> Decimal
        for v in part:
            code = code_by_mid.get(v.metric_id)
            if code is None:
                continue
            deriv = repo.get_derivation(v.id)
            if deriv is not None and deriv["equation_code"] in _WITHIN_PERIOD_CODES:
                continue  # prior within-period solver output; re-derive + supersede
            observed[code] = v
            seed[code] = v.value

        # Normalize operating_expenses to the operating (amortization-excluded)
        # basis before solving any ratio. `basis_tainted` marks the expense value
        # (and everything derived from it) as non-comparable when rule (b) applies.
        basis_tainted = False
        opex = observed.get("operating_expenses")
        if opex is not None and getattr(opex, "cost_basis", "operating") == "psab_total":
            amort = observed.get("amortization")
            if amort is not None:
                # rule (a): operating = psab_total - amortization.
                seed["operating_expenses"] = opex.value - amort.value
            else:
                # rule (b): compute anyway, but the result is not comparable.
                basis_tainted = True
                warnings.append(
                    f"{_MIXED_COST_BASIS}: operating_expenses on psab_total basis "
                    f"with no amortization to normalize ({agency_slug}, period "
                    f"{period_id}, scope {scope}) -- derived ratios not comparable"
                )

        # Agency attributes the solver may READ but never solve into (e.g.
        # net_debt_per_capita = net_debt / service_area_population).
        population = repo.agency_population(agency_id)
        if population is not None:
            seed[ATTR_PREFIX + "service_area_population"] = Decimal(population)

        result = solve(seed)
        for flag in result.flags:
            warnings.append(f"{flag} ({agency_slug}, period {period_id}, scope {scope})")

        # Write solved values in dependency order. res.values preserves insertion
        # order: observed first, then each solved value after its inputs -- so a
        # solved input's id is always known by the time a value that uses it is written.
        code_to_vid: dict[str, int] = {c: v.id for c, v in observed.items()}
        code_to_quality: dict[str, str] = {c: v.quality for c, v in observed.items()}
        # Values (transitively) derived from an un-normalized psab_total expense
        # are not comparable (rule b). res.values is in dependency order, so a
        # single forward pass propagates the taint from operating_expenses.
        tainted: set[str] = {"operating_expenses"} if basis_tainted else set()
        for code, sv in result.values.items():
            if sv.origin != "solved":
                continue
            meta = METRICS.get(code)
            if meta is None:
                continue  # never write an attr: node or an unknown code
            input_ids = [code_to_vid[c] for c in sv.inputs if c in code_to_vid]
            quality = weakest_quality(
                [code_to_quality[c] for c in sv.inputs if c in code_to_quality]
            )
            code_tainted = any(c in tainted for c in sv.inputs)
            if code_tainted:
                tainted.add(code)
            vid = repo.insert_derived_value(
                agency_id=agency_id,
                metric_id=repo.metric_id(code),
                reporting_period_id=period_id,
                mode_id=mode_id,
                service_scope=scope,
                value=sv.value,
                unit=meta["unit"],
                quality=quality,
                equation_code=sv.equation_code,
                input_value_ids=input_ids,
                currency="CAD" if meta["unit_type"] == "currency" else None,
                # Only the five rated hero metrics carry ranks; a value derived from
                # an un-normalized psab_total expense is never comparable (rule b).
                comparable_flag=(code in RATED_METRICS) and not code_tainted,
                notes=_MIXED_COST_BASIS if code_tainted else None,
            )
            ids.append(vid)
            code_to_vid[code] = vid
            code_to_quality[code] = quality

    return RecomputeResult(ids=ids, warnings=warnings)
