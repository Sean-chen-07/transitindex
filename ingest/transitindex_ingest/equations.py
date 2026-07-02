"""The metric equation graph: the relationships that link metrics, and a pure
solver that propagates known values to a fixpoint.

Every relationship is one of TWO algebraic shapes so any single unknown is
exactly solvable:

  - SUM    `result = Σ sign_i · term_i`   (e.g. operating_expenses =
           total_revenue_excluding_subsidy + subsidy; net_debt =
           total_liabilities − total_financial_assets). Solvable for any one
           missing term.
  - RATIO  `quotient = numerator / denominator`  (e.g. farebox_recovery_ratio =
           farebox_revenue / operating_expenses). Solvable for ANY one of the
           three -- including the denominator, since "farebox + revenue ->
           expenses" (expenses = revenue / farebox) is the flagship goal.

Composites are normalized into named intermediates rather than special-cased:
`subsidy_per_rider` is the RATIO `subsidy / ridership`, and
`subsidy = operating_expenses − total_revenue_excluding_subsidy` is its own
SUM. So a sourced or back-solved subsidy stays mutually consistent.

`solve()` is pure arithmetic over a `{metric_code: Decimal}` map of OBSERVED
values (sourced, or already-current independent observations). It marks every
value it produces as `solved`, records which equation and which operands it
used (provenance), and NEVER fabricates:

  - Dispute-proof rule: a value is written only into an EMPTY slot. A sourced
    value is never overwritten. (This module never sees the DB; the caller
    seeds only observed values, and `solve` returns only the new solved ones.)
  - Cross-check rule: when an equation is fully determined by OBSERVED operands
    only, the residual is checked and a flag raised on disagreement -- a green
    identity therefore means two INDEPENDENT observations agree, never that a
    value agrees with the equation that produced it (no false confidence).
  - Over-determination: if two equations back-solve the same empty slot to
    numbers that disagree beyond tolerance, NOTHING is written and a
    `sum_mismatch` is raised; if they agree, one value is written, citing the
    first equation by sorted code (deterministic).
Agency attributes that are not metric values (e.g. service_area_population for
net_debt_per_capita) appear as operands with an `attr:` prefix; the solver may
READ them but never solves INTO them.

Pure stdlib (Decimal + dataclasses). The DB wiring, provenance rows, and
quality inheritance live in `jobs/derived_recompute.py`.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping, Optional, Union

# --- flag strings (mirror validation/flags.py vocabulary) --------------------

SUM_MISMATCH = "sum_mismatch"
CROSS_SOURCE_DISAGREEMENT = "cross_source_disagreement"

ATTR_PREFIX = "attr:"


def _render(code: str) -> str:
    """Operand label for display: drop the attr: prefix (agency attributes)."""
    return code[len(ATTR_PREFIX):] if code.startswith(ATTR_PREFIX) else code

# --- equation shapes ---------------------------------------------------------


@dataclass(frozen=True)
class SumEquation:
    """`result = Σ sign · term`. Solvable for the result or any single term.

    `defines` names the metric this equation is the canonical *definition* of
    (used for the human formula caption), or None when it is a pure constraint
    among otherwise-sourced metrics (e.g. the operating-expense identities).
    """

    code: str
    result: str
    terms: tuple[tuple[int, str], ...]  # (sign ∈ {+1,-1}, metric_code)
    defines: Optional[str] = None

    @property
    def operands(self) -> frozenset[str]:
        return frozenset({self.result, *(t for _s, t in self.terms)})

    def display(self) -> str:
        parts: list[str] = []
        for i, (sign, term) in enumerate(self.terms):
            op = "-" if sign < 0 else ("+" if i else "")
            label = _render(term)
            parts.append(f"{op} {label}".strip() if op else label)
        return " ".join(parts)


@dataclass(frozen=True)
class RatioEquation:
    """`quotient = numerator / denominator`. The quotient is the metric it
    defines. The denominator may be an `attr:` node."""

    code: str
    quotient: str
    numerator: str
    denominator: str

    @property
    def defines(self) -> str:
        return self.quotient

    @property
    def operands(self) -> frozenset[str]:
        return frozenset({self.quotient, self.numerator, self.denominator})

    def display(self) -> str:
        return f"{_render(self.numerator)} / {_render(self.denominator)}"


Equation = Union[SumEquation, RatioEquation]


# --- the catalog -------------------------------------------------------------
# Source of truth for the relationships. Mirrored to core.metric_equations
# (a read-only display/provenance table) with the same parity discipline as
# refdata.METRICS <-> db/seeds/04_metrics.sql. Balance-sheet equations are
# added with the balance-sheet metric family (see balance-sheet-and-frequency-plan.md).

EQUATIONS: tuple[Equation, ...] = (
    # Income-statement identities (constraints among sourced metrics).
    SumEquation(
        code="expense_revenue_subsidy",
        result="operating_expenses",
        terms=((+1, "total_revenue_excluding_subsidy"), (+1, "subsidy")),
    ),
    SumEquation(
        code="expense_components",
        result="operating_expenses",
        terms=(
            (+1, "labour_cost"),
            (+1, "energy_fuel_cost"),
            (+1, "materials_services_cost"),
            (+1, "amortization"),
            (+1, "other_operating_expenses"),
        ),
    ),
    # Revenue decomposition + enterprise-lens bridges (metric-set-build-plan.md
    # Phase 4). `total_revenue_excluding_subsidy` = the StatCan line (sourced);
    # farebox is sourced from the PDF; `other_revenue` is the broad residual.
    SumEquation(
        code="earned_revenue_components",
        result="total_revenue_excluding_subsidy",
        terms=((+1, "farebox_revenue"), (+1, "other_revenue")),
        defines="other_revenue",
    ),
    # Ties out by construction (total_revenue_excluding_subsidy is DEFINED as
    # total_revenue - subsidy); a pure cross-source constraint when all three
    # are sourced.
    SumEquation(
        code="total_revenue_def",
        result="total_revenue",
        terms=((+1, "total_revenue_excluding_subsidy"), (+1, "subsidy")),
    ),
    SumEquation(
        code="annual_surplus_deficit_def",
        result="annual_surplus_deficit",
        terms=((+1, "total_revenue"), (-1, "total_expenses")),
        defines="annual_surplus_deficit",
    ),
    # Derived ratios (each defines its quotient). The rider-share ratios take
    # farebox_revenue as the numerator, NOT the broad total_revenue_excluding_subsidy
    # (= total_revenue − subsidy), which would inflate them for capital-heavy
    # agencies (metric-set-build-plan.md Phase 3, Decision #4).
    RatioEquation(
        "average_fare_def", "average_fare", "farebox_revenue", "ridership"
    ),
    RatioEquation(
        "cost_per_hour_def", "cost_per_hour", "operating_expenses", "revenue_service_hours"
    ),
    RatioEquation("cost_per_rider_def", "cost_per_rider", "operating_expenses", "ridership"),
    RatioEquation(
        "farebox_recovery_def",
        "farebox_recovery_ratio",
        "farebox_revenue",
        "operating_expenses",
    ),
    RatioEquation(
        "subsidy_per_rider_def", "subsidy_per_rider", "subsidy", "ridership"
    ),
    RatioEquation(
        "trips_per_revenue_hour_def",
        "trips_per_revenue_hour",
        "ridership",
        "revenue_service_hours",
    ),
    # Balance-sheet family (PSAB identities + scale-free ratios). See
    # balance-sheet-and-frequency-plan.md. net_debt is derived for the cross-check;
    # the two ratios are the only ranked balance-sheet metrics.
    SumEquation(
        code="net_debt_def",
        result="net_debt",
        terms=((+1, "total_liabilities"), (-1, "total_financial_assets")),
        defines="net_debt",
    ),
    SumEquation(
        code="total_assets_identity",
        result="total_assets",
        terms=((+1, "total_financial_assets"), (+1, "total_non_financial_assets")),
    ),
    SumEquation(
        code="accumulated_surplus_identity",
        result="accumulated_surplus",
        terms=((+1, "total_assets"), (-1, "total_liabilities")),
    ),
    RatioEquation("debt_to_assets_def", "debt_to_assets", "total_liabilities", "total_assets"),
    RatioEquation(
        "net_debt_per_capita_def",
        "net_debt_per_capita",
        "net_debt",
        "attr:service_area_population",
    ),
    # Balance-sheet component residuals (metric-set-build-plan.md addendum #2):
    # each closes a component + residual to its PSAB total (same pattern as
    # other_revenue), so `assets = liabilities + equity` holds at every level.
    SumEquation(
        code="financial_assets_components",
        result="total_financial_assets",
        terms=((+1, "cash_and_investments"), (+1, "other_financial_assets")),
        defines="other_financial_assets",
    ),
    SumEquation(
        code="liabilities_components",
        result="total_liabilities",
        terms=((+1, "long_term_debt"), (+1, "other_liabilities")),
        defines="other_liabilities",
    ),
    SumEquation(
        code="non_financial_assets_components",
        result="total_non_financial_assets",
        terms=((+1, "tangible_capital_assets"), (+1, "other_non_financial_assets")),
        defines="other_non_financial_assets",
    ),
)


# --- catalog helpers ---------------------------------------------------------


def _all_operands() -> frozenset[str]:
    out: set[str] = set()
    for eq in EQUATIONS:
        out |= eq.operands
    return frozenset(out)


ALL_OPERANDS: frozenset[str] = _all_operands()


def metric_operands(eq: Equation) -> frozenset[str]:
    """Operands that are real metric codes (excludes `attr:` nodes)."""
    return frozenset(o for o in eq.operands if not o.startswith(ATTR_PREFIX))


def defining_equation(metric_code: str) -> Optional[Equation]:
    """The single equation that defines `metric_code` as derived, or None."""
    for eq in EQUATIONS:
        if eq.defines == metric_code:
            return eq
    return None


def display_formula(metric_code: str) -> Optional[str]:
    """Human formula caption for a derived metric (mirrors metrics.formula)."""
    eq = defining_equation(metric_code)
    return eq.display() if eq is not None else None


def derived_codes() -> frozenset[str]:
    """Every metric the catalog defines as derived."""
    return frozenset(eq.defines for eq in EQUATIONS if eq.defines is not None)


def equation_kind(eq: Equation) -> str:
    """'sum' or 'ratio' (mirrors core.metric_equations.kind)."""
    return "sum" if isinstance(eq, SumEquation) else "ratio"


def full_display(eq: Equation) -> str:
    """The full 'lhs = rhs' relation, for the metric_equations display column."""
    lhs = eq.result if isinstance(eq, SumEquation) else eq.quotient
    return f"{lhs} = {eq.display()}"


# A reserved derivation code for the cross-period aggregation (annual = sum of the
# 12 monthly values). Not a within-period SUM/RATIO equation, so it lives outside
# the EQUATIONS catalog but is a valid metric_value_derivations.equation_code.
PERIOD_ROLLUP = "period_rollup"

# A reserved derivation code for fleet_capacity: a cross-MODE weighted aggregation
# (Σ capacity_weight × fleet_size(mode)). Not a within-period SUM/RATIO equation, so it
# lives outside the EQUATIONS catalog but is a valid metric_value_derivations.equation_code.
MODE_WEIGHTED_FLEET = "mode_weighted_fleet"


# --- the solver --------------------------------------------------------------


@dataclass(frozen=True)
class SolvedValue:
    """A value in the working set: either OBSERVED (seeded by the caller) or
    SOLVED (produced this run, with the equation + operand codes that made it)."""

    value: Decimal
    origin: str  # 'observed' | 'solved'
    equation_code: Optional[str] = None  # set only when origin == 'solved'
    inputs: tuple[str, ...] = ()  # operand codes used; empty when observed


@dataclass(frozen=True)
class SolveResult:
    """`values` is the full working map (observed + solved). `solved` is just
    the new values the caller should persist. `flags` are cross-check /
    over-determination findings raised during propagation."""

    values: dict[str, SolvedValue]
    flags: list[str]

    @property
    def solved(self) -> dict[str, SolvedValue]:
        return {c: v for c, v in self.values.items() if v.origin == "solved"}


def _close(a: Decimal, b: Decimal, rel_tol: Decimal, abs_tol: Decimal) -> bool:
    """Relative tolerance with an absolute floor (for rounded currency)."""
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def _all_close(vals: list[Decimal], rel_tol: Decimal, abs_tol: Decimal) -> bool:
    return all(_close(vals[0], v, rel_tol, abs_tol) for v in vals[1:])


def _solve_for(
    eq: Equation, unknown: str, working: Mapping[str, SolvedValue]
) -> Optional[Decimal]:
    """Solve `eq` for its single `unknown`, or None if not permitted/defined."""
    if isinstance(eq, SumEquation):
        if unknown == eq.result:
            return sum(
                (sign * working[term].value for sign, term in eq.terms), Decimal(0)
            )
        # unknown is one term with sign s: result = Σ sign·term
        #   s·unknown = result − Σ_{other} sign·term  →  unknown = s·(rhs)
        for sign, term in eq.terms:
            if term == unknown:
                rhs = working[eq.result].value - sum(
                    (s2 * working[t2].value for s2, t2 in eq.terms if t2 != unknown),
                    Decimal(0),
                )
                return sign * rhs  # sign is ±1, so multiply == divide
        return None
    # RatioEquation: quotient = numerator / denominator. Solvable for any one of
    # the three (back-solving a denominator -- e.g. expenses from farebox +
    # revenue -- is the flagship goal); both division paths guard against /0.
    if unknown == eq.quotient:
        den = working[eq.denominator].value
        if den == 0:
            return None
        return working[eq.numerator].value / den
    if unknown == eq.numerator:
        return working[eq.quotient].value * working[eq.denominator].value
    if unknown == eq.denominator:
        quot = working[eq.quotient].value
        if quot == 0:
            return None
        return working[eq.numerator].value / quot
    return None


def _residual_flag(
    eq: Equation, working: Mapping[str, SolvedValue], rel_tol: Decimal, abs_tol: Decimal
) -> Optional[str]:
    """Cross-check a fully-known equation; return a flag string on disagreement.

    SUM identities raise `sum_mismatch`; a RATIO whose published quotient
    disagrees with the computed one raises `cross_source_disagreement`.
    """
    if isinstance(eq, SumEquation):
        computed = sum((sign * working[t].value for sign, t in eq.terms), Decimal(0))
        actual = working[eq.result].value
        return None if _close(actual, computed, rel_tol, abs_tol) else SUM_MISMATCH
    den = working[eq.denominator].value
    if den == 0:
        return None
    computed = working[eq.numerator].value / den
    actual = working[eq.quotient].value
    return None if _close(actual, computed, rel_tol, abs_tol) else CROSS_SOURCE_DISAGREEMENT


def solve(
    observed: Mapping[str, Decimal],
    *,
    rel_tol: Decimal = Decimal("0.02"),
    abs_tol: Decimal = Decimal("0"),
) -> SolveResult:
    """Propagate observed values to a fixpoint over the equation catalog.

    `observed` maps metric codes (and `attr:` attribute nodes) to their known
    values -- all treated as independent observations. Returns the full working
    map (observed + solved) plus any cross-check / over-determination flags.
    """
    working: dict[str, SolvedValue] = {
        code: SolvedValue(val, "observed") for code, val in observed.items()
    }
    flags: list[str] = []
    eqs = sorted(EQUATIONS, key=lambda e: e.code)

    # Fixpoint: each pass solves every equation with exactly one unknown.
    max_passes = len(ALL_OPERANDS) + 1
    for _ in range(max_passes):
        candidates: dict[str, list[tuple[str, Decimal, tuple[str, ...]]]] = {}
        for eq in eqs:
            ops = eq.operands
            unknown = [o for o in ops if o not in working]
            if len(unknown) != 1:
                continue
            u = unknown[0]
            if u.startswith(ATTR_PREFIX):
                continue  # never infer an agency attribute
            val = _solve_for(eq, u, working)
            if val is None:
                continue
            inputs = tuple(sorted(o for o in ops if o != u))
            candidates.setdefault(u, []).append((eq.code, val, inputs))

        progress = False
        for slot in sorted(candidates):
            if slot in working:
                continue
            cands = candidates[slot]
            vals = [c[1] for c in cands]
            if _all_close(vals, rel_tol, abs_tol):
                eq_code, val, inputs = min(cands, key=lambda c: c[0])
                working[slot] = SolvedValue(val, "solved", eq_code, inputs)
                progress = True
            elif SUM_MISMATCH not in flags:
                flags.append(SUM_MISMATCH)  # disagreeing back-solves: write nothing
        if not progress:
            break
    else:  # pragma: no cover - guards against a non-terminating cycle
        raise RuntimeError("equation solver did not converge")

    # Cross-checks: only over equations whose operands are ALL observed, so a
    # green identity never reflects a value agreeing with its own derivation.
    for eq in eqs:
        ops = eq.operands
        if not all(o in working for o in ops):
            continue
        metric_ops = [o for o in ops if not o.startswith(ATTR_PREFIX)]
        if not metric_ops or any(working[o].origin != "observed" for o in metric_ops):
            continue
        flag = _residual_flag(eq, working, rel_tol, abs_tol)
        if flag is not None and flag not in flags:
            flags.append(flag)

    return SolveResult(values=working, flags=flags)
