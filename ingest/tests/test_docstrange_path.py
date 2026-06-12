"""Offline tests for the DocStrange markdown path (path b).

No network, no docstrange install, no real Anthropic call. The DocStrange step is
the module-level seam `_pdf_to_markdown` (monkeypatched to return canned markdown)
and the Claude step is a FakeLLMClient, so the extractor runs end-to-end offline.
"""

from __future__ import annotations

from decimal import Decimal

from transitindex_ingest.pdf.extractor import ExtractionRequest, Extractor
from transitindex_ingest.pdf.llm import ExtractedValue, FakeLLMClient
from transitindex_ingest.pdf import docstrange_path


def _ev(metric="ridership", value=250000000, conf=0.9):
    return ExtractedValue(
        metric_code=metric, value=Decimal(str(value)), unit="count",
        period_kind="annual", period_year=2024, page_number=1,
        confidence=Decimal(str(conf)),
    )


def _extractor(values, **over):
    kwargs = dict(model="claude-opus-4-8", llm_client=FakeLLMClient(values))
    kwargs.update(over)
    return docstrange_path.DocStrangeExtractor(api_key="unused", **kwargs)


def test_pdf_goes_through_docstrange_then_claude(monkeypatch):
    seen = {}

    def fake_md(pdf_bytes, *, mode, api_key):
        seen["mode"] = mode
        seen["api_key"] = api_key
        return "## Operating statistics\n\n| Annual ridership | 250,000,000 |"

    monkeypatch.setattr(docstrange_path, "_pdf_to_markdown", fake_md)

    res = _extractor([_ev()], mode="cloud", docstrange_api_key="key123").extract(
        ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF-1.7 fake")
    )

    assert res.values[0].value == Decimal("250000000")
    assert res.diagnostics["extractor"] == "docstrange_markdown"
    assert res.diagnostics["source"] == "docstrange_cloud"
    assert res.diagnostics["model"] == "claude-opus-4-8"
    assert res.diagnostics["markdown_chars"] > 0
    assert res.diagnostics["est_cost_usd"] > 0
    # the chosen mode + key reach the docstrange seam
    assert seen == {"mode": "cloud", "api_key": "key123"}


def test_local_mode_passes_mode_through(monkeypatch):
    monkeypatch.setattr(
        docstrange_path, "_pdf_to_markdown",
        lambda pdf_bytes, *, mode, api_key: f"md[{mode}]",
    )
    res = _extractor([_ev()], mode="cpu").extract(
        ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF")
    )
    assert res.diagnostics["source"] == "docstrange_cpu"


def test_pages_only_skips_docstrange_and_uses_text():
    # No pdf_bytes: must NOT call docstrange (it would raise if reached) and
    # should read the supplied page text instead.
    res = _extractor([_ev("fleet_size", 2000)]).extract(
        ExtractionRequest(agency_slug="ttc", pages=[(1, "fleet of 2000 buses")])
    )
    assert res.values[0].metric_code == "fleet_size"
    assert res.diagnostics["source"] == "pages_text"


def test_estimate_cost_scales_with_length_and_model():
    cheap = docstrange_path._estimate_cost("x" * 4000, "claude-haiku-4-5")
    dear = docstrange_path._estimate_cost("x" * 4000, "claude-opus-4-8")
    assert dear > cheap                       # opus rate > haiku rate
    assert docstrange_path._estimate_cost("x" * 8000, "claude-opus-4-8") > dear


def test_result_markdown_accepts_method_or_attribute():
    class _MethodResult:
        def extract_markdown(self):
            return "from-method"

    class _AttrResult:
        markdown = "from-attr"

    assert docstrange_path._result_markdown(_MethodResult()) == "from-method"
    assert docstrange_path._result_markdown(_AttrResult()) == "from-attr"


def test_is_extractor_protocol():
    assert isinstance(_extractor([]), Extractor)


def test_module_imports_without_third_party():
    import transitindex_ingest.pdf.docstrange_path as dp  # must not raise

    assert hasattr(dp, "DocStrangeExtractor")
    assert hasattr(dp, "_pdf_to_markdown")
