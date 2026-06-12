"""Offline tests for the per-report model router.

No network, no pypdf, no real Anthropic call. `route_from_texts` is pure, so it
is driven with plain lists of strings; `RoutingExtractor` is driven with
FakeExtractors and a monkeypatched `_page_texts`, so the scanned-vs-clean signal
is supplied directly. The lazy-import proof needs no third-party deps.
"""

from __future__ import annotations

from decimal import Decimal

from transitindex_ingest.pdf.extractor import (
    ExtractionRequest,
    Extractor,
    FakeExtractor,
)
from transitindex_ingest.pdf.llm import ExtractedValue
from transitindex_ingest.pdf import router


def _ev(metric, value, conf=0.9, year=2024, unit="count"):
    return ExtractedValue(
        metric_code=metric, value=Decimal(str(value)), unit=unit,
        period_kind="annual", period_year=year, page_number=1,
        confidence=Decimal(str(conf)),
    )


def _route(texts, **over):
    kwargs = dict(
        max_pages=15, image_text_threshold=120, image_cutoff=0.25,
        premium="PREM", cheap="CHEAP",
    )
    kwargs.update(over)
    return router.route_from_texts(texts, **kwargs)


# --- the pure decision -------------------------------------------------------


def test_clean_text_routes_to_cheap():
    model, diag = _route(["word " * 100] * 5)
    assert model == "CHEAP"
    assert diag["reason"] == "text_clean"
    assert diag["image_fraction"] == 0.0
    assert diag["pages_considered"] == 5


def test_all_scanned_routes_to_premium():
    model, diag = _route(["", "", "", "", ""])
    assert model == "PREM"
    assert diag["reason"] == "image_heavy"
    assert diag["pages_scanned"] == 5
    assert diag["image_fraction"] == 1.0


def test_cutoff_boundary_stays_cheap_below():
    # 1 scanned of 5 = 0.2, below the 0.25 cutoff -> cheap.
    model, _ = _route(["x" * 400] * 4 + [""])
    assert model == "CHEAP"


def test_cutoff_boundary_flips_at_or_above():
    # 2 scanned of 5 = 0.4, at/above the cutoff -> premium.
    model, _ = _route(["x" * 400] * 3 + ["", ""])
    assert model == "PREM"


def test_whitespace_only_page_counts_as_scanned():
    model, diag = _route(["   \n  \t ", "x" * 400, "y" * 400])
    assert diag["pages_scanned"] == 1
    assert model == "PREM"  # 1/3 = 0.33 >= 0.25


def test_no_text_at_all_defaults_to_premium():
    model, diag = _route([])
    assert model == "PREM"
    assert diag["reason"] == "no_text_extracted"


def test_only_kept_pages_are_classified():
    # 20 pages > max_pages(15): the prefilter keeps the first 3 (head) plus the
    # highest-scoring rest. A blank page buried past the budget must not count.
    texts = ["ridership 100 revenue 200 " * 20] * 19 + [""]
    model, diag = _route(texts, max_pages=15)
    assert diag["pages_considered"] == 15
    assert diag["pages_scanned"] == 0  # the lone blank page was not selected
    assert model == "CHEAP"


# --- the extractor wrapper ---------------------------------------------------


def _pair():
    return {
        "PREM": FakeExtractor([_ev("ridership", 250000000)], {"model": "PREM"}),
        "CHEAP": FakeExtractor([_ev("ridership", 999)], {"model": "CHEAP"}),
    }


def _routing_extractor():
    return router.RoutingExtractor(
        _pair(), premium="PREM", cheap="CHEAP",
        image_cutoff=0.25, image_text_threshold=120, max_pages=15,
    )


def test_routing_extractor_sends_scanned_pdf_to_premium(monkeypatch):
    monkeypatch.setattr(router, "_page_texts", lambda b: ["", "", ""])
    res = _routing_extractor().extract(
        ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF-1.7 fake")
    )
    assert res.values[0].value == Decimal("250000000")        # premium's find
    assert res.diagnostics["extractor"] == "routed"
    assert res.diagnostics["routing"]["routed_to"] == "PREM"
    assert res.diagnostics["model"] == "PREM"                 # delegated diag kept


def test_routing_extractor_sends_clean_pdf_to_cheap(monkeypatch):
    monkeypatch.setattr(router, "_page_texts", lambda b: ["x" * 500, "y" * 500])
    res = _routing_extractor().extract(
        ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF-1.7 fake")
    )
    assert res.values[0].value == Decimal("999")              # cheap's find
    assert res.diagnostics["routing"]["routed_to"] == "CHEAP"


def test_routing_extractor_unreadable_pdf_defaults_to_premium(monkeypatch):
    def _boom(_):
        raise ValueError("not a pdf")

    monkeypatch.setattr(router, "_page_texts", _boom)
    res = _routing_extractor().extract(
        ExtractionRequest(agency_slug="ttc", pdf_bytes=b"garbage")
    )
    assert res.diagnostics["routing"]["reason"] == "unreadable_default_premium"
    assert res.diagnostics["routing"]["routed_to"] == "PREM"


def test_routing_extractor_pages_only_uses_cheap():
    res = _routing_extractor().extract(
        ExtractionRequest(agency_slug="ttc", pages=[(1, "some pre-extracted text")])
    )
    assert res.values[0].value == Decimal("999")              # cheap's find
    assert res.diagnostics["routing"]["reason"] == "pages_only_text"


def test_routing_extractor_rejects_unknown_model_ids():
    import pytest

    with pytest.raises(ValueError):
        router.RoutingExtractor(_pair(), premium="PREM", cheap="MISSING")


def test_routing_extractor_is_extractor_protocol():
    assert isinstance(_routing_extractor(), Extractor)


def test_router_imports_without_third_party():
    import transitindex_ingest.pdf.router as r  # must not raise

    assert hasattr(r, "RoutingExtractor")
    assert hasattr(r, "claude_routed")
