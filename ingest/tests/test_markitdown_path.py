"""Offline tests for the markitdown hybrid path.

No network, no markitdown install, no real Anthropic. `_to_markdown` /
`_image_pages_pdf` are module seams (monkeypatched) and the Anthropic client is a
scripted fake injected via `_client`, so the extractor runs end-to-end offline.
"""

from __future__ import annotations

import types
from decimal import Decimal

from transitindex_ingest.pdf.extractor import ExtractionRequest, Extractor
from transitindex_ingest.pdf import markitdown_path


class _Block:
    def __init__(self, rows):
        self.type = "tool_use"
        self.name = "record_metrics"
        self.input = {"values": rows}


class _Msg:
    def __init__(self, rows, input_tokens=5000, stop_reason="tool_use"):
        self.content = [_Block(rows)]
        self.usage = types.SimpleNamespace(
            input_tokens=input_tokens, cache_creation_input_tokens=0, cache_read_input_tokens=0
        )
        self.stop_reason = stop_reason


class _Client:
    def __init__(self, msg):
        self._msg = msg
        self.calls = []

    @property
    def messages(self):
        return self

    def create(self, **kw):
        self.calls.append(kw)
        return self._msg


_ROW = {
    "metric_code": "ridership", "value": "419.9", "unit": "trips",
    "period_kind": "annual", "period_year": 2024, "page_number": 68,
    "confidence": 0.95, "printed_scale": "millions",
}


def _ext(rows=(_ROW,), **over):
    client = _Client(_Msg(list(rows)))
    return markitdown_path.MarkitdownExtractor(api_key="x", _client=client, **over), client


def test_clean_pdf_sends_markdown_only(monkeypatch):
    monkeypatch.setattr(markitdown_path, "_to_markdown", lambda b: "| ridership | 419.9 |")
    monkeypatch.setattr(markitdown_path, "_image_pages_pdf", lambda b, t: (None, []))
    ext, client = _ext()
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))

    assert res.values[0].metric_code == "ridership"
    assert res.values[0].value == Decimal("419900000")     # 419.9 * millions, applied in code
    d = res.diagnostics
    assert d["extractor"] == "markitdown_hybrid"
    assert d["image_page_count"] == 0
    assert d["stop_reason"] == "tool_use"
    assert d["input_tokens"] == 5000
    assert d["est_cost_usd"] > 0
    content = client.calls[0]["messages"][0]["content"]
    assert all(b["type"] == "text" for b in content)        # no document block


def test_scanned_pages_attached_as_document(monkeypatch):
    monkeypatch.setattr(markitdown_path, "_to_markdown", lambda b: "narrative text")
    monkeypatch.setattr(markitdown_path, "_image_pages_pdf", lambda b, t: ("BASE64PDF", [66, 67]))
    ext, client = _ext()
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))

    assert res.diagnostics["image_pages"] == [66, 67]
    docs = [b for b in client.calls[0]["messages"][0]["content"] if b["type"] == "document"]
    assert len(docs) == 1
    assert docs[0]["source"]["data"] == "BASE64PDF"


def test_include_image_pages_false_skips_detection(monkeypatch):
    monkeypatch.setattr(markitdown_path, "_to_markdown", lambda b: "text")

    def _boom(b, t):
        raise AssertionError("image-page detection should be skipped")

    monkeypatch.setattr(markitdown_path, "_image_pages_pdf", _boom)
    ext, _ = _ext(include_image_pages=False)
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))
    assert res.diagnostics["image_page_count"] == 0


def test_pages_only_skips_markitdown(monkeypatch):
    def _boom(b):
        raise AssertionError("markitdown must not run without pdf_bytes")

    monkeypatch.setattr(markitdown_path, "_to_markdown", _boom)
    ext, client = _ext()
    res = ext.extract(ExtractionRequest(agency_slug="ttc", pages=[(1, "ridership 419.9 million")]))
    assert res.values[0].metric_code == "ridership"
    md_block = client.calls[0]["messages"][0]["content"][1]
    assert "419.9" in md_block["text"]


def test_max_tokens_passed_through(monkeypatch):
    monkeypatch.setattr(markitdown_path, "_to_markdown", lambda b: "t")
    monkeypatch.setattr(markitdown_path, "_image_pages_pdf", lambda b, t: (None, []))
    ext, client = _ext(max_tokens=8192)
    ext.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF"))
    assert client.calls[0]["max_tokens"] == 8192


def test_is_extractor_protocol():
    ext, _ = _ext()
    assert isinstance(ext, Extractor)


def test_module_imports_without_third_party():
    import transitindex_ingest.pdf.markitdown_path as m  # must not raise

    assert hasattr(m, "MarkitdownExtractor")
    assert hasattr(m, "_to_markdown")
    assert hasattr(m, "_image_pages_pdf")
