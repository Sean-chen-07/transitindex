"""Offline replay report guard (Plan A step 1.7).

Pins the headline numbers the replay report produces for doc 59 (ttc 2019) from
the FROZEN smoke fixture: it carries 13 recorded conflicts, a TTC
12,060,661,000 / 12,059,032,000 pair that COLLAPSES under the 0.5% merge rule,
and a 525.5M / 530M ridership pair that SURVIVES as a real conflict. The exact
note strings are read out of the committed fixture so the test breaks if the
recording is ever regenerated. Pure stdlib + pytest, no API, no PDF.
"""

from __future__ import annotations

import json
from pathlib import Path

from transitindex_ingest.eval.replay import _conflict_candidates, _replay_doc, replay
from transitindex_ingest.pdf.chunked_hybrid import _within_merge_tolerance

SMOKE = Path(__file__).parent / "fixtures" / "smoke" / "smoke10_2026-06-12.json"
DOC_ID = 59  # ttc 2019 annual_report


def _smoke_entry(doc_id: int) -> dict:
    smoke = json.loads(SMOKE.read_text(encoding="utf-8"))
    return next(e for e in smoke if e["doc_id"] == doc_id)


def _note_for(entry: dict, metric: str, value: str) -> str:
    """The recorded note on the (metric, value) reading, straight from the fixture."""
    return next(
        v["note"] for v in entry["values"]
        if v["metric"] == metric and v["value"] == value
    )


def test_doc59_has_thirteen_recorded_conflicts():
    """The replay counts exactly the 13 conflicts the fixture recorded for doc 59."""
    entry = _smoke_entry(DOC_ID)
    assert entry["conflicts"] == 13  # the recording's own count
    rep = _replay_doc(entry)
    assert rep["conflicts_before"] == 13


def test_ttc_rounded_vs_exact_pair_collapses():
    """12,060,661,000 vs 12,059,032,000 (0.014% apart) collapses out of review."""
    entry = _smoke_entry(DOC_ID)
    # The exact note string the fixture recorded for this reading.
    note = _note_for(entry, "accumulated_surplus", "12060661000")
    assert note == "⚠ chunks disagree — 12060661000, 12059032000, 12060661000 (reviewer confirm)"
    candidates = _conflict_candidates(note)
    assert _within_merge_tolerance(candidates) is True


def test_ridership_scope_pair_survives():
    """525.5M vs 530M (0.86% apart) is a real scope difference -- stays a conflict."""
    entry = _smoke_entry(DOC_ID)
    note = _note_for(entry, "ridership", "525500000.0")
    assert "⚠ chunks disagree — 525500000.0, 530000000 (reviewer confirm)" in note
    candidates = _conflict_candidates(note)
    assert _within_merge_tolerance(candidates) is False


def test_doc59_collapse_and_survive_counts():
    """Across doc 59, some conflicts collapse and the rest survive (sum == 13)."""
    rep = _replay_doc(_smoke_entry(DOC_ID))
    assert rep["collapsed"] > 0
    assert rep["conflicts_after"] == rep["conflicts_before"] - rep["collapsed"]
    assert rep["collapsed"] + rep["conflicts_after"] == 13


def test_replay_totals_aggregate_docs():
    """replay() sums per-doc figures into totals over the whole fixture."""
    report = replay(SMOKE)
    assert len(report["docs"]) == 10
    assert report["totals"]["collapsed"] == sum(d["collapsed"] for d in report["docs"])
    assert report["totals"]["conflicts_before"] > report["totals"]["conflicts_after"]


def test_replay_carries_the_accuracy_report():
    """replay() ships the offline accuracy summary, gold-scored where a confirmed
    fixture matches the recording (doc 59 ttc 2019, doc 13 calgary-transit 2019)."""
    accuracy = replay(SMOKE)["accuracy"]
    assert accuracy["totals"]["values"] == 438
    assert accuracy["totals"]["flags"]["conflict"] > 0
    scored = {(g["slug"], g["year"]) for g in accuracy["gold"]}
    assert scored == {("ttc", 2019), ("calgary-transit", 2019)}
