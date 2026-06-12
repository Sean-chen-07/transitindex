"""Offline tests for the chunked hybrid extractor.

The chunker and merge are pure (driven with strings/values). The extractor is run
with monkeypatched `_to_markdown` / `_image_page_batches` seams and a scripted fake
Anthropic client, so it runs end-to-end with no network or third-party deps.
"""

from __future__ import annotations

import types
from decimal import Decimal

from transitindex_ingest.pdf.extractor import ExtractionRequest, Extractor
from transitindex_ingest.pdf.llm import ExtractedValue
from transitindex_ingest.pdf import chunked_hybrid as ch


def _ev(metric, value, conf=0.9, year=2024):
    return ExtractedValue(
        metric_code=metric, value=Decimal(str(value)), unit="count",
        period_kind="annual", period_year=year, page_number=1, confidence=Decimal(str(conf)),
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


def test_is_extractor_protocol():
    assert isinstance(ch.ChunkedHybridExtractor(api_key="x", _client=_Client(lambda t: [])), Extractor)


def test_module_imports_without_third_party():
    import transitindex_ingest.pdf.chunked_hybrid as m  # must not raise

    assert hasattr(m, "ChunkedHybridExtractor")
    assert hasattr(m, "chunk_markdown")
    assert hasattr(m, "merge_values")
