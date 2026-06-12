"""Offline tests for the Plan B eval/smoke runner (eval/smoke.py, step 2.6).

Drives `run_smoke` and the `--baseline` delta math with a FakeExtractor and a fake
storage + an InMemoryRepository -- no Anthropic API, no Supabase, no PDF. Asserts the
per-doc shaping, the totals aggregation (review rate / conflicts / dropped counts /
cost), the gold scoring path, and the before/after delta arithmetic. `main()` itself is
the paid step 2.7 and is deliberately not exercised.
"""

from __future__ import annotations

import json
from decimal import Decimal

from transitindex_ingest.db.memory import InMemoryRepository
from transitindex_ingest.eval.smoke import (
    REVIEW_CONFIDENCE,
    aggregate,
    build_doc_result,
    delta_table,
    gold_assessments,
    run_smoke,
)
from transitindex_ingest.pdf.extractor import ExtractionRequest, ExtractionResult
from transitindex_ingest.pdf.llm import ExtractedValue


class FakeStorage:
    """download(key) returns canned bytes (KeyError on a missing key)."""

    def __init__(self, objects):
        self.objects = dict(objects)

    def download(self, key: str) -> bytes:
        return self.objects[key]


class RecordingExtractor:
    """Returns a canned ExtractionResult and records the request it received."""

    def __init__(self, result: ExtractionResult):
        self._result = result
        self.request = None

    def extract(self, request: ExtractionRequest) -> ExtractionResult:
        self.request = request
        return ExtractionResult(values=list(self._result.values), diagnostics=dict(self._result.diagnostics))


def _ev(metric, value, year, *, conf="0.9", scope="total", basis="actual", note=None, kind="annual"):
    return ExtractedValue(
        metric_code=metric,
        value=Decimal(value),
        unit="CAD",
        period_kind=kind,
        period_year=year,
        page_number=1,
        confidence=Decimal(conf),
        note=note,
        service_scope=scope,
        basis=basis,
    )


def _diag(**over):
    base = {
        "segments": 3,
        "md_chunks": 2,
        "image_batches": 1,
        "image_pages": [4, 5],
        "values_raw": 7,
        "dropped_below_floor": 1,
        "dropped_scope": 2,
        "dropped_basis": 1,
        "input_tokens": 50000,
        "est_cost_usd": 0.25,
        "errors": {},
        "segments_raw": [{"label": "md0", "values": [], "input_tokens": 100, "error": None}],
    }
    base.update(over)
    return base


def _catalog(repo, *, year=2024, doc_type="annual_report", author="T", key="ttc/2024.pdf"):
    return repo.upsert_document(
        agency_id=repo.agency_id("ttc"),
        year=year,
        doc_type=doc_type,
        author_label=author,
        storage_key=key,
        file_hash="hash",
        file_bytes=1,
    )


# --- build_doc_result -------------------------------------------------------


def test_build_doc_result_shapes_smoke_fixture_fields():
    repo = InMemoryRepository()
    doc_id = _catalog(repo, year=2019)
    doc = repo.get_document(doc_id)

    values = [
        _ev("ridership", "500000000", 2019),
        _ev("operating_revenue", "1264087000", 2019, conf="0.5",
            note="x; ⚠ chunks disagree — 1264087000, 1253900000 (reviewer confirm)"),
        _ev("operating_expenses", "2921698000", 2010),  # weird (far prior) year
    ]
    result = ExtractionResult(values=values, diagnostics=_diag())

    out = build_doc_result(doc, "ttc", result, elapsed_s=12.34)

    assert out["doc_id"] == doc_id
    assert out["slug"] == "ttc"
    assert out["year"] == 2019
    assert out["doc_type"] == "annual_report"
    assert out["time_s"] == 12.3
    assert out["values_merged"] == 3
    assert out["values_raw"] == 7
    assert out["distinct_metrics"] == 3
    assert out["metrics"] == ["operating_expenses", "operating_revenue", "ridership"]
    assert out["cost_usd"] == 0.25
    assert out["tokens"] == 50000
    assert out["conflicts"] == 1          # only the disagree note
    assert out["lowconf"] == 1            # the conf=0.5 value
    assert out["weird_years"] == [2010]   # 2019 + comparatives normal; 2010 is weird
    assert out["dups"] == []
    assert out["dropped_scope"] == 2
    assert out["dropped_basis"] == 1
    assert out["dropped_below_floor"] == 1
    assert out["segments_raw"] == _diag()["segments_raw"]
    assert {v["metric"] for v in out["values"]} == {"ridership", "operating_revenue", "operating_expenses"}


# --- run_smoke aggregation --------------------------------------------------


def test_run_smoke_aggregates_per_doc_and_totals():
    repo = InMemoryRepository()
    id_a = _catalog(repo, year=2019, key="ttc/a.pdf")
    id_b = _catalog(repo, year=2024, doc_type="budget", key="ttc/b.pdf")
    storage = FakeStorage({"ttc/a.pdf": b"%PDF a", "ttc/b.pdf": b"%PDF b"})

    res_a = ExtractionResult(
        values=[
            _ev("ridership", "1", 2019, conf="0.9"),
            _ev("operating_revenue", "2", 2019, conf="0.4"),  # low-conf review item
        ],
        diagnostics=_diag(est_cost_usd=0.2, input_tokens=1000, dropped_scope=1, dropped_basis=0),
    )
    res_b = ExtractionResult(
        values=[_ev("ridership", "3", 2024, conf="0.5",
                    note="⚠ chunks disagree — 3, 4 (reviewer confirm)")],
        diagnostics=_diag(est_cost_usd=0.3, input_tokens=2000, dropped_scope=0, dropped_basis=2),
    )

    factory = iter([RecordingExtractor(res_a), RecordingExtractor(res_b)])
    report = run_smoke(repo, storage, [id_a, id_b], lambda: next(factory))

    t = report["totals"]
    assert t["docs"] == 2
    assert t["values_merged"] == 3
    assert t["lowconf"] == 2                       # 0.4 (doc a) + 0.5 (doc b, <=0.5)
    assert abs(t["review_rate"] - 2 / 3) < 1e-9
    assert t["conflicts"] == 1                     # only doc b's disagree note
    assert t["dropped_scope"] == 1
    assert t["dropped_basis"] == 2
    assert t["cost_usd"] == 0.5
    assert t["tokens"] == 3000
    # aggregate() over the raw doc list agrees with the embedded totals.
    assert aggregate(report["docs"]) == t


def test_run_smoke_passes_doc_context_into_request():
    repo = InMemoryRepository()
    doc_id = _catalog(repo, year=2024, doc_type="budget", author="C", key="ttc/c.pdf")
    storage = FakeStorage({"ttc/c.pdf": b"%PDF"})
    rec = RecordingExtractor(ExtractionResult(values=[], diagnostics=_diag()))

    run_smoke(repo, storage, [doc_id], lambda: rec)

    assert rec.request.agency_slug == "ttc"
    assert rec.request.pdf_bytes == b"%PDF"
    assert rec.request.doc_type == "budget"
    assert rec.request.author_label == "C"
    assert rec.request.doc_year == 2024


def test_run_smoke_unknown_doc_raises():
    repo = InMemoryRepository()
    storage = FakeStorage({})
    try:
        run_smoke(repo, storage, [999], lambda: RecordingExtractor(ExtractionResult(values=[])))
    except ValueError as exc:
        assert "unknown document" in str(exc)
    else:  # pragma: no cover - the call must raise
        raise AssertionError("expected ValueError for an unknown doc id")


# --- gold scoring -----------------------------------------------------------


def test_run_smoke_scores_gold_when_fixture_present(tmp_path):
    repo = InMemoryRepository()
    doc_id = _catalog(repo, year=2024, key="ttc/g.pdf")
    storage = FakeStorage({"ttc/g.pdf": b"%PDF"})

    gold_dir = tmp_path / "gold"
    gold_dir.mkdir()
    (gold_dir / "ttc_annual_2024.json").write_text(json.dumps({
        "agency_slug": "ttc",
        "period_year": 2024,
        "period_kind": "annual",
        "records": [
            {"metric_code": "ridership", "true_value": "256900000", "unit": "count",
             "tolerance": "0.01", "should_flag": False},
        ],
    }), encoding="utf-8")

    result = ExtractionResult(values=[_ev("ridership", "256900000", 2024, conf="0.95")], diagnostics=_diag())
    report = run_smoke(repo, storage, [doc_id], lambda: RecordingExtractor(result), gold_dir=gold_dir)

    g = report["gold"][doc_id]
    assert g["fixture"] == "ttc_annual_2024.json"
    assert g["precision"] == 1.0     # the clean value lands within tolerance
    assert g["clean_count"] == 1


def test_gold_assessments_filter_scope_basis_and_flag():
    gold_meta = {"agency_slug": "ttc", "period_year": 2024, "period_kind": "annual"}
    values = [
        _ev("ridership", "100", 2024, conf="0.9"),                 # kept, clean
        _ev("operating_revenue", "200", 2024, conf="0.5"),         # kept, low_confidence
        _ev("fleet_size", "10", 2024, conf="0.9", scope="city_wide"),  # dropped: scope
        _ev("labour_cost", "5", 2024, conf="0.9", basis="forecast"),   # dropped: basis
        _ev("operating_expenses", "9", 2023, conf="0.9"),          # dropped: wrong year
    ]
    out = gold_assessments(values, gold_meta)

    by_code = {a.metric_code: a for a in out}
    assert set(by_code) == {"ridership", "operating_revenue"}
    assert by_code["ridership"].flags == ()
    assert by_code["operating_revenue"].flags == ("low_confidence",)


# --- baseline delta math ----------------------------------------------------


def test_delta_table_before_after_delta():
    baseline = [{
        "values_merged": 10, "values_raw": 12, "lowconf": 4, "conflicts": 3,
        "dropped_below_floor": 0, "dropped_scope": 0, "dropped_basis": 0,
        "cost_usd": 0.50, "tokens": 100,
    }]
    current = [{
        "values_merged": 12, "values_raw": 14, "lowconf": 1, "conflicts": 1,
        "dropped_below_floor": 2, "dropped_scope": 5, "dropped_basis": 2,
        "cost_usd": 0.20, "tokens": 80,
    }]

    table = delta_table(baseline, current)

    assert table["values_merged"] == {"before": 10, "after": 12, "delta": 2}
    assert table["lowconf"] == {"before": 4, "after": 1, "delta": -3}
    assert table["conflicts"] == {"before": 3, "after": 1, "delta": -2}
    assert table["dropped_scope"] == {"before": 0, "after": 5, "delta": 5}
    assert table["cost_usd"]["delta"] == -0.30
    # review_rate is derived in aggregate(): 4/10 -> 1/12.
    assert abs(table["review_rate"]["before"] - 0.4) < 1e-9
    assert abs(table["review_rate"]["after"] - 1 / 12) < 1e-9


def test_delta_table_accepts_full_report_shape():
    """A prior result file is {'docs': [...], 'totals': {...}}; delta reads totals."""
    baseline = {"docs": [], "totals": {"values_merged": 5, "lowconf": 2, "review_rate": 0.4,
                                       "conflicts": 1, "dropped_scope": 0, "dropped_basis": 0,
                                       "cost_usd": 1.0}}
    current = {"docs": [], "totals": {"values_merged": 8, "lowconf": 1, "review_rate": 0.125,
                                      "conflicts": 0, "dropped_scope": 3, "dropped_basis": 1,
                                      "cost_usd": 0.4}}
    table = delta_table(baseline, current)
    assert table["values_merged"]["delta"] == 3
    assert table["cost_usd"]["delta"] == -0.6
