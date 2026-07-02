"""Offline tests for the chunked hybrid extractor.

The chunker and merge are pure (driven with strings/values). The extractor is run
with monkeypatched `_to_markdown` / `_image_page_batches` seams and a scripted fake
Anthropic client, so it runs end-to-end with no network or third-party deps.
"""

from __future__ import annotations

import types
from decimal import Decimal

from transitindex_ingest.pdf.extractor import ExtractionRequest, Extractor
from transitindex_ingest.pdf.llm import ExtractedValue, value_from_dict
from transitindex_ingest.pdf import chunked_hybrid as ch


def _ev(metric, value, conf=0.9, year=2024, scope="total", basis="actual"):
    return ExtractedValue(
        metric_code=metric, value=Decimal(str(value)), unit="count",
        period_kind="annual", period_year=year, page_number=1, confidence=Decimal(str(conf)),
        service_scope=scope, basis=basis,
    )


# --- chunk_markdown ---------------------------------------------------------


def test_chunks_break_only_at_paragraph_boundaries():
    # 30 three-line paragraphs; with a small target they pack into several chunks,
    # but every paragraph must stay intact in exactly one chunk (never split).
    md = "\n\n".join(f"para{i} a\npara{i} b\npara{i} c" for i in range(30))
    chunks = ch.chunk_markdown(md, target_lines=10)
    assert len(chunks) > 1
    for i in range(30):
        assert any(
            f"para{i} a" in c and f"para{i} b" in c and f"para{i} c" in c for c in chunks
        )


def test_table_is_never_split_across_chunks():
    # A 40-row table with a year header and NO blank lines is one block, so it stays
    # whole even with a tiny target -- the header never gets separated from its rows.
    header = "|  |  | 2024 | 2023 | 2022 |"
    rows = [f"| metric {i} |  | {i}.1 | {i}.2 | {i}.3 |" for i in range(40)]
    md = "intro paragraph\n\n" + "\n".join([header] + rows) + "\n\noutro paragraph"
    chunks = ch.chunk_markdown(md, target_lines=10)

    with_header = [c for c in chunks if "2024 | 2023 | 2022" in c]
    assert len(with_header) == 1                     # header lives in exactly one chunk
    table_chunk = with_header[0]
    for i in range(40):
        assert f"metric {i} " in table_chunk         # and every row rode along with it


def test_no_content_is_duplicated_between_chunks():
    md = "\n\n".join(f"BLOCK{i}" for i in range(10))
    chunks = ch.chunk_markdown(md, target_lines=2)
    seen = [l for c in chunks for l in c.splitlines() if l.strip()]
    assert sorted(seen) == sorted(f"BLOCK{i}" for i in range(10))  # each line appears exactly once


def test_empty_markdown_yields_no_chunks():
    assert ch.chunk_markdown("   \n  \n  ") == []


# --- _page_label ------------------------------------------------------------


def test_page_label_collapses_runs():
    assert ch._page_label([1, 2, 4, 13, 14]) == "1-2, 4, 13-14"


def test_page_label_single_page():
    assert ch._page_label([7]) == "7"


def test_page_label_fully_contiguous():
    assert ch._page_label([3, 4, 5, 6]) == "3-6"


# --- chunk_markdown_with_context --------------------------------------------


def test_scale_declaration_carries_to_next_chunk():
    md = "(in thousands of dollars)\n\n" + "\n\n".join(f"para{i}" for i in range(6))
    out = ch.chunk_markdown_with_context(md, target_lines=1)
    # The scale line is its own first chunk; every later chunk carries it in context.
    assert 'scale declaration: "(in thousands of dollars)"' in out[1][1]
    assert 'scale declaration: "(in thousands of dollars)"' in out[-1][1]


def test_later_scale_declaration_supersedes_earlier():
    md = "(in thousands of dollars)\n\nmiddle para\n\n(in millions)\n\ntail para"
    out = ch.chunk_markdown_with_context(md, target_lines=1)
    tail_ctx = next(ctx for text, ctx in out if "tail para" in text)
    assert 'scale declaration: "(in millions)"' in tail_ctx
    assert "thousands" not in tail_ctx


def test_heading_tracked_independently_of_scale():
    md = "# Financial Statements\n\nbody para one\n\nbody para two"
    out = ch.chunk_markdown_with_context(md, target_lines=1)
    body_ctx = next(ctx for text, ctx in out if "body para two" in text)
    assert 'section: "# Financial Statements"' in body_ctx
    assert "scale declaration" not in body_ctx


def test_no_heading_or_scale_yields_empty_context():
    md = "plain para one\n\nplain para two"
    out = ch.chunk_markdown_with_context(md, target_lines=1)
    assert all(ctx == "" for _, ctx in out)


def test_chunk_markdown_delegates_to_context_variant():
    md = "(in thousands)\n\n# Heading\n\n" + "\n\n".join(f"BLOCK{i}" for i in range(8))
    assert ch.chunk_markdown(md, target_lines=2) == [
        text for text, _ in ch.chunk_markdown_with_context(md, target_lines=2)
    ]


# --- merge_values -----------------------------------------------------------


def test_merge_dedupes_agreement_keeping_best_confidence():
    out = ch.merge_values([_ev("ridership", 100, 0.7), _ev("ridership", 100, 0.95)])
    assert len(out) == 1
    assert out[0].confidence == Decimal("0.95")


def test_merge_flags_conflicting_values():
    out = ch.merge_values([_ev("ridership", 100, 0.9), _ev("ridership", 101, 0.8)])
    assert len(out) == 1
    assert out[0].confidence <= Decimal("0.5")
    assert "disagree" in out[0].note


def test_merge_keeps_distinct_metrics_and_periods():
    out = ch.merge_values([
        _ev("ridership", 100), _ev("fleet_size", 50), _ev("ridership", 95, year=2023),
    ])
    assert len(out) == 3


def test_merge_collapses_within_tolerance_no_disagree_note():
    # TTC operating_expenses: 12,060,661,000 vs 12,059,032,000 -- 0.014% apart.
    out = ch.merge_values([
        _ev("operating_expenses", 12060661000, 0.8),
        _ev("operating_expenses", 12059032000, 0.95),
    ])
    assert len(out) == 1
    assert "disagree" not in (out[0].note or "")
    assert "agree within 0.5%" in out[0].note
    assert out[0].confidence == Decimal("0.95")   # lifted to the group max


def test_merge_still_conflicts_beyond_tolerance():
    # ~1.2% apart -> a real restatement, must STILL flag for review.
    out = ch.merge_values([
        _ev("capital_expenditure", 1000000000, 0.9),
        _ev("capital_expenditure", 1012000000, 0.8),
    ])
    assert len(out) == 1
    assert out[0].confidence <= Decimal("0.5")
    assert "disagree" in out[0].note


def test_merge_525_5m_vs_530m_still_conflicts():
    # 525,500,000 vs 530,000,000 -- 0.86% apart, a real scope difference: still conflicts.
    out = ch.merge_values([
        _ev("total_revenue_excluding_subsidy", 525500000, 0.9),
        _ev("total_revenue_excluding_subsidy", 530000000, 0.85),
    ])
    assert len(out) == 1
    assert out[0].confidence <= Decimal("0.5")
    assert "disagree" in out[0].note


def test_merge_within_tolerance_keeps_most_precise_reading():
    # Rounded summary (more trailing zeros) loses to the exact reading even though the
    # rounded one has higher confidence: precision wins the value, max wins confidence.
    out = ch.merge_values([
        _ev("operating_expenses", 12060000000, 0.95),   # rounded, 7 trailing zeros
        _ev("operating_expenses", 12059032000, 0.7),    # exact, 3 trailing zeros
    ])
    assert len(out) == 1
    assert out[0].value == Decimal("12059032000")
    assert out[0].confidence == Decimal("0.95")


def test_merge_does_not_collide_scope_variants():
    # TTC: bus-only (mode_subset) 181M vs whole-agency total 420M -- same metric/period
    # but different scope, so the new _key keeps them apart instead of flagging a conflict.
    out = ch.merge_values([
        _ev("ridership", 420000000, scope="total"),
        _ev("ridership", 181000000, scope="mode_subset"),
    ])
    assert len(out) == 2
    assert all("disagree" not in (v.note or "") for v in out)


def test_merge_does_not_collide_basis_variants():
    # Same metric/period, actual result vs a forecast -- different basis -> two values.
    out = ch.merge_values([
        _ev("ridership", 100000000, basis="actual"),
        _ev("ridership", 130000000, basis="forecast"),
    ])
    assert len(out) == 2
    assert all("disagree" not in (v.note or "") for v in out)


# --- _image_page_batches ----------------------------------------------------


def test_image_page_batches_group_without_overlap():
    import pytest

    pytest.importorskip("pypdf")
    from io import BytesIO

    from pypdf import PdfWriter

    w = PdfWriter()
    for _ in range(7):
        w.add_blank_page(width=200, height=200)  # blank => no text layer => all low-text
    buf = BytesIO()
    w.write(buf)
    batches = ch._image_page_batches(buf.getvalue(), threshold=120, batch=3, overlap=0)
    pages = [p for _, p in batches]
    assert pages == [[1, 2, 3], [4, 5, 6], [7]]   # consecutive, no page sent twice


# --- extractor (offline) ----------------------------------------------------


class _Block:
    def __init__(self, rows):
        self.type = "tool_use"
        self.name = "record_metrics"
        self.input = {"values": rows}


class _Msg:
    def __init__(self, rows):
        self.content = [_Block(rows)]
        self.usage = types.SimpleNamespace(
            input_tokens=1000, cache_creation_input_tokens=0, cache_read_input_tokens=0
        )


class _Client:
    """Content-driven fake (thread-safe under the GIL): rows come from `handler(text)`."""

    def __init__(self, handler):
        self._handler = handler
        self.calls = []

    @property
    def messages(self):
        return self

    def create(self, **kw):
        self.calls.append(kw)
        text = " ".join(
            b.get("text", "") for b in kw["messages"][0]["content"] if b.get("type") == "text"
        )
        return _Msg(self._handler(text))


_ROW = {
    "metric_code": "ridership", "value": "100", "unit": "trips",
    "period_kind": "annual", "period_year": 2024, "page_number": 1, "confidence": 0.9,
}


def _ext(handler, **over):
    client = _Client(handler)
    return ch.ChunkedHybridExtractor(api_key="x", _client=client, **over), client


def test_extractor_chunks_and_merges(monkeypatch):
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "A\n\nB\n\nC")
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [])
    ext, _ = _ext(lambda text: [_ROW], target_lines=1)
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))
    d = res.diagnostics
    assert d["extractor"] == "chunked_hybrid"
    assert d["md_chunks"] == 3 and d["image_batches"] == 0
    assert d["values_raw"] == 3 and d["values_merged"] == 1   # 3 chunks agree -> 1
    assert len(res.values) == 1


def test_extractor_batches_scanned_pages(monkeypatch):
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "text")
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [("B64A", [5, 6]), ("B64B", [7, 8])])
    ext, client = _ext(lambda text: [])
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))
    d = res.diagnostics
    assert d["image_batches"] == 2
    assert d["image_pages"] == [5, 6, 7, 8]
    doc_calls = [
        c for c in client.calls
        if any(b.get("type") == "document" for b in c["messages"][0]["content"])
    ]
    assert len(doc_calls) == 2


def _is_image_call(call):
    return any(b.get("type") == "document" for b in call["messages"][0]["content"])


def test_text_and_image_segments_route_to_different_models(monkeypatch):
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "A\n\nB")                       # 2 text chunks
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [("B64", [5, 6])])  # 1 image batch
    ext, client = _ext(lambda text: [], target_lines=1)
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))

    text_models = {c["model"] for c in client.calls if not _is_image_call(c)}
    image_models = {c["model"] for c in client.calls if _is_image_call(c)}
    assert ch.DEFAULT_TEXT_MODEL != ch.DEFAULT_IMAGE_MODEL          # the whole point: they differ
    assert text_models == {ch.DEFAULT_TEXT_MODEL}                    # cheap model reads the text
    assert image_models == {ch.DEFAULT_IMAGE_MODEL}                  # strong model reads the scans

    d = res.diagnostics
    assert d["text_model"] == ch.DEFAULT_TEXT_MODEL and d["model"] == ch.DEFAULT_IMAGE_MODEL
    # cost is split by model: 2 text calls + 1 image call, 1000 tok each (the fake's usage).
    assert d["input_tokens_by_model"] == {ch.DEFAULT_TEXT_MODEL: 2000, ch.DEFAULT_IMAGE_MODEL: 1000}


def test_text_model_override_is_used(monkeypatch):
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "A")
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [])
    ext, client = _ext(lambda text: [], text_model="claude-haiku-4-5")
    ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))
    assert {c["model"] for c in client.calls} == {"claude-haiku-4-5"}


def test_extractor_survives_a_segment_error(monkeypatch):
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "A\n\nB")
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [])

    def handler(text):
        if "section 1 of" in text:        # chunk md0 always fails, deterministically
            raise RuntimeError("rate limited")
        return [_ROW]

    ext, _ = _ext(handler, target_lines=1)
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))
    assert res.diagnostics["errors"]      # one segment failed, recorded
    assert len(res.values) == 1           # the other segment's value survived


def test_pages_only_path_still_chunks(monkeypatch):
    def _boom(b):
        raise AssertionError("markitdown must not run without pdf_bytes")

    monkeypatch.setattr(ch, "_to_markdown", _boom)
    ext, _ = _ext(lambda text: [_ROW])
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pages=[(1, "ridership 100")]))
    assert res.diagnostics["image_batches"] == 0
    assert len(res.values) == 1


def test_extractor_drops_below_floor_and_counts(monkeypatch):
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "A\n\nB\n\nC")
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [])

    def handler(text):
        if "section 1 of" in text:
            return [{**_ROW, "value": "100", "confidence": 0.2}]   # below floor -> dropped
        if "section 2 of" in text:
            return [{**_ROW, "metric_code": "fleet_size", "value": "50", "confidence": 0.3}]  # exactly 0.3 survives
        return [{**_ROW, "metric_code": "revenue_service_hours", "value": "7", "confidence": 0.9}]

    ext, _ = _ext(handler, target_lines=1)
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))
    assert res.diagnostics["dropped_below_floor"] == 1
    metrics = {v.metric_code for v in res.values}
    assert metrics == {"fleet_size", "revenue_service_hours"}   # the 0.2 reading is gone, 0.3 stays


def test_segments_raw_round_trips_per_label(monkeypatch):
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "A\n\nB")
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [])

    def handler(text):
        if "section 1 of" in text:
            return [_ROW]
        return [{**_ROW, "metric_code": "fleet_size", "value": "50"}]

    ext, _ = _ext(handler, target_lines=1)
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))
    raw = res.diagnostics["segments_raw"]
    assert [s["label"] for s in raw] == ["md0", "md1"]   # one entry per segment, in order
    # Each recorded segment's values round-trip back to the metrics the fake returned.
    assert [value_from_dict(d).metric_code for d in raw[0]["values"]] == ["ridership"]
    assert [value_from_dict(d).metric_code for d in raw[1]["values"]] == ["fleet_size"]
    assert all(s["error"] is None for s in raw)
    assert all(s["input_tokens"] == 1000 for s in raw)


def test_extractor_filters_out_of_scope_after_merge(monkeypatch):
    # One chunk returns a total/actual, a restated actual, a forecast, and a city_wide
    # row. After merge, the forecast + city_wide are dropped (and counted); the total
    # and the restated actual survive (restated stays -- it is an actual, just restated).
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "only one chunk")
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [])

    rows = [
        {**_ROW, "metric_code": "ridership", "value": "100"},  # total / actual (default)
        {**_ROW, "metric_code": "total_revenue_excluding_subsidy", "value": "200", "basis": "restated"},
        {**_ROW, "metric_code": "ridership", "value": "130", "basis": "forecast", "period_year": 2027},
        {**_ROW, "metric_code": "accumulated_surplus", "value": "9999", "service_scope": "city_wide"},
    ]
    ext, _ = _ext(lambda text: rows)
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))

    assert res.diagnostics["dropped_scope"] == 1   # the city_wide row
    assert res.diagnostics["dropped_basis"] == 1   # the forecast row
    kept = {(v.metric_code, v.basis) for v in res.values}
    assert kept == {("ridership", "actual"), ("total_revenue_excluding_subsidy", "restated")}


def test_doc_aware_intro_lines_for_city_budget_request(monkeypatch):
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "body text")
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [])
    ext, client = _ext(lambda text: [])
    ext.extract(ExtractionRequest(
        agency_slug="ttc", pdf_bytes=b"%PDF",
        doc_type="budget", author_label="C", doc_year=2025,
    ))
    intro = client.calls[0]["messages"][0]["content"][0]["text"]
    assert "Document: budget for 2025, published by the CITY government" in intro
    assert "service_scope='city_wide'" in intro                # [C] city-wide guidance
    assert "This is a plan/budget document" in intro           # budget basis guidance
    assert "figures for 2025 and later" in intro


def test_doc_aware_intro_absent_for_bare_request(monkeypatch):
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "body text")
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [])
    ext, client = _ext(lambda text: [])
    ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))
    intro = client.calls[0]["messages"][0]["content"][0]["text"]
    assert intro.startswith("Agency: ttc")
    assert "Document:" not in intro
    assert "city_wide" not in intro
    assert "plan/budget document" not in intro


def test_system_prompt_carries_definition_canon(monkeypatch):
    import pytest

    pytest.importorskip("yaml")  # the canon is YAML-backed; skip in the stdlib-only env
    monkeypatch.setattr(ch, "_to_markdown", lambda b: "body text")
    monkeypatch.setattr(ch, "_image_page_batches", lambda b, t, **k: [])
    ext, client = _ext(lambda text: [])
    ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))
    system_text = client.calls[0]["system"][0]["text"]
    assert "Metric definitions (the canon" in system_text
    assert "unlinked" in system_text.lower()   # a known phrase from the dictionary guidance


def test_is_extractor_protocol():
    assert isinstance(ch.ChunkedHybridExtractor(api_key="x", _client=_Client(lambda t: [])), Extractor)


def test_module_imports_without_third_party():
    import transitindex_ingest.pdf.chunked_hybrid as m  # must not raise

    assert hasattr(m, "ChunkedHybridExtractor")
    assert hasattr(m, "chunk_markdown")
    assert hasattr(m, "merge_values")
