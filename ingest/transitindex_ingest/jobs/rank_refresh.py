"""Rank-refresh job -- materializes core.metric_ranks for one metric+period.

`refresh_ranks(repo, metric_code, period_id)` recomputes ranks for BOTH
comparison sets ('all' and 'subdivision') over the current, comparable values
of a single metric in a single reporting period, then writes them via
`repo.replace_metric_ranks`.

Ranking is ALWAYS within one period and one service scope -- never across
years. Direction comes from the metric's `higher_is_better` flag (refdata):
True ranks highest-first, False ranks lowest-first, None (neutral) still ranks
highest-first but the direction is informational. An agency with no current
value for the period is simply absent from the ranking.

Pure stdlib.
"""

from __future__ import annotations

from typing import Optional

from ..db.models import MetricRankRow
from ..refdata import AGENCIES, METRICS


def compute_ranks(values, higher_is_better: Optional[bool]):
    """Rank `values` and return ``[(agency_id, rank, denominator), ...]``.

    `values` is an iterable of objects with ``.agency_id`` and ``.value``
    (e.g. MetricValue rows already restricted to one period/scope and to
    comparable rows). The denominator is the number of ranked entries.

    Ordering: ``higher_is_better is False`` ranks ascending (rank 1 = lowest);
    otherwise (True or None) ranks descending (rank 1 = highest). Ties share a
    rank (competition ranking: 1, 2, 2, 4); agency_id breaks ordering ties so
    the output is deterministic.
    """
    rows = list(values)
    denominator = len(rows)
    descending = higher_is_better is not False
    # Sort by value (asc/desc) with agency_id as a stable tiebreaker.
    rows.sort(key=lambda v: v.agency_id)
    rows.sort(key=lambda v: v.value, reverse=descending)

    result: list[tuple[int, int, int]] = []
    prev_value = None
    prev_rank = 0
    for position, row in enumerate(rows, start=1):
        if prev_value is not None and row.value == prev_value:
            rank = prev_rank  # tie: share the previous rank
        else:
            rank = position
        result.append((row.agency_id, rank, denominator))
        prev_value = row.value
        prev_rank = rank
    return result


def _direction(higher_is_better: Optional[bool]) -> str:
    if higher_is_better is True:
        return "higher"
    if higher_is_better is False:
        return "lower"
    return "neutral"


def refresh_ranks(
    repo,
    metric_code: str,
    period_id: int,
    service_scope: str = "system_wide",
) -> None:
    """Recompute and store ranks for `metric_code` in `period_id`.

    Writes both the 'all' (every included agency together) and 'subdivision'
    (ranked within each province group) comparison sets via
    `repo.replace_metric_ranks`. Only current, comparable values in the given
    service scope and period participate.
    """
    metric_id = repo.metric_id(metric_code)
    higher_is_better = METRICS[metric_code]["higher_is_better"]
    direction = _direction(higher_is_better)

    values = [
        v
        for v in repo.list_current_values_for_metric_period(metric_id, period_id)
        if v.comparable_flag and v.service_scope == service_scope
    ]

    # 'all': one ranking across every included agency.
    all_rows = [
        MetricRankRow(agency_id=aid, rank=rank, denominator=denom, direction=direction)
        for aid, rank, denom in compute_ranks(values, higher_is_better)
    ]
    repo.replace_metric_ranks(metric_id, period_id, "all", all_rows)

    # 'subdivision': rank within each province group separately.
    by_subdivision = _group_by_subdivision(repo, values)
    subdivision_rows: list[MetricRankRow] = []
    for group in by_subdivision.values():
        for aid, rank, denom in compute_ranks(group, higher_is_better):
            subdivision_rows.append(
                MetricRankRow(
                    agency_id=aid, rank=rank, denominator=denom, direction=direction
                )
            )
    repo.replace_metric_ranks(metric_id, period_id, "subdivision", subdivision_rows)


def _group_by_subdivision(repo, values):
    """Group `values` by their agency's subdivision (province) code."""
    agency_subdivision = {
        repo.agency_id(slug): meta["subdivision"] for slug, meta in AGENCIES.items()
    }
    groups: dict[str, list] = {}
    for v in values:
        subdivision = agency_subdivision[v.agency_id]
        groups.setdefault(subdivision, []).append(v)
    return groups
