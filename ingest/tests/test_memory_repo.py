"""Proves the in-memory fake is trustworthy.

Covers the one_current_value supersede chain (with mode_id None as a real key
part), the audit trail, and seed-backed slug/code lookups. Everything else in
the suite leans on this fake, so these guarantees matter.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from transitindex_ingest.db.memory import InMemoryRepository


def test_seed_lookups_resolve(repo):
    # 10 agencies, 21 metrics, 10 modes, 8 feeds all resolve.
    assert repo.agency_id("ttc") > 0
    assert repo.agency_id("burlington-transit") > 0
    assert repo.metric_id("subsidy_per_rider") > 0
    assert repo.mode_id("subway") > 0
    assert repo.mode_id(None) is None
    assert repo.feed_id("statcan_307") > 0
    assert len(repo.list_metrics()) == 21


def test_unknown_lookups_raise(repo):
    with pytest.raises(ValueError):
        repo.agency_id("nope")
    with pytest.raises(ValueError):
        repo.metric_id("nope")
    with pytest.raises(ValueError):
        repo.mode_id("nope")
    with pytest.raises(ValueError):
        repo.feed_id("nope")


def _insert(repo: InMemoryRepository, value: str, mode_id=None):
    a = repo.agency_id("ttc")
    m = repo.metric_id("annual_ridership")
    p = repo.get_or_create_reporting_period(
        a, "monthly", _d(2026, 3, 1), _d(2026, 3, 31), "Mar 2026"
    )
    return repo.insert_metric_value(
        agency_id=a,
        metric_id=m,
        reporting_period_id=p,
        mode_id=mode_id,
        service_scope="system_wide",
        value=Decimal(value),
        unit="count",
        quality="preliminary",
    )


def _d(y, mo, d):
    from datetime import date

    return date(y, mo, d)


def test_second_current_value_supersedes_first(repo):
    first = _insert(repo, "100")
    second = _insert(repo, "200")

    a = repo.agency_id("ttc")
    m = repo.metric_id("annual_ridership")
    p = repo.get_or_create_reporting_period(
        a, "monthly", _d(2026, 3, 1), _d(2026, 3, 31), "Mar 2026"
    )
    current = repo.get_current_metric_value(a, m, p, None, "system_wide")

    assert current.id == second
    assert current.is_current is True
    assert current.value == Decimal("200")
    assert current.restatement_of_id == first

    # exactly one current row for the tuple
    cohort = repo.list_current_values_for_metric_period(m, p)
    assert [v.id for v in cohort] == [second]


def test_audit_row_written_per_insert(repo):
    first = _insert(repo, "100")
    second = _insert(repo, "200")
    audit = repo.iter_audit()
    # one insert audit per metric value (mirrors the SQL trigger).
    inserts = [a for a in audit if a["change_type"] == "insert"]
    assert {a["metric_value_id"] for a in inserts} == {first, second}
    assert any(a["new_value"] == Decimal("200") for a in inserts)


def test_mode_id_participates_in_key(repo):
    # A system-wide row (mode None) and a per-mode row are DISTINCT tuples:
    # both stay current side by side.
    system_wide = _insert(repo, "300", mode_id=None)
    subway = _insert(repo, "120", mode_id=repo.mode_id("subway"))

    a = repo.agency_id("ttc")
    m = repo.metric_id("annual_ridership")
    p = repo.get_or_create_reporting_period(
        a, "monthly", _d(2026, 3, 1), _d(2026, 3, 31), "Mar 2026"
    )
    assert repo.get_current_metric_value(a, m, p, None, "system_wide").id == system_wide
    assert (
        repo.get_current_metric_value(a, m, p, repo.mode_id("subway"), "system_wide").id
        == subway
    )
    assert len(repo.list_current_values_for_metric_period(m, p)) == 2


def test_promote_pending_supersedes_and_approves(repo, sample_record):
    # Stage via pending, then promote -> reaches metric_values + approves pending.
    doc = repo.get_or_create_source_document(sample_record.source, repo.agency_id("ttc"))
    pid = repo.insert_pending_value(sample_record, source_document_id=doc)
    assert repo.get_pending_value(pid).review_status == "pending"

    vid = repo.promote_pending(pid)
    assert repo.get_pending_value(pid).review_status == "approved"

    a = repo.agency_id("ttc")
    m = repo.metric_id("annual_ridership")
    p = repo.get_or_create_reporting_period(
        a, "monthly", _d(2026, 3, 1), _d(2026, 3, 31), "Mar 2026"
    )
    current = repo.get_current_metric_value(a, m, p, None, "system_wide")
    assert current.id == vid
    assert current.value == Decimal("1234567")
