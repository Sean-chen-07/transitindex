"""Offline tests for the Extractor seam and ClaudePdfExtractor.

No network, no real Anthropic call, no pypdf, no DB beyond the in-memory `repo`
fixture. ClaudePdfExtractor is exercised by replacing its `self._client` with a
scripted fake whose `messages.create` returns canned objects, so `anthropic` is
never actually called. Construction-based tests are gated with importorskip
(the constructor does `import anthropic`); the lazy-import proof needs no deps.
The chunking guard is tested behind importorskip("pypdf").
"""

from __future__ import annotations

import types
from decimal import Decimal

import pytest

from transitindex_ingest.pdf.extractor import (
    ExtractionRequest,
    ExtractionResult,
    Extractor,
    FakeExtractor,
    LegacyTextExtractor,
)
from transitindex_ingest.pdf.llm import (
    EXTRACTION_SYSTEM_PROMPT,
    ExtractedValue,
    FakeLLMClient,
)
from transitindex_ingest.pdf.pipeline import SourceRefMeta, run_pdf

# --- fakes mimicking the SDK surface the code touches -----------------------


class _FakeBlock:
    """A tool_use content block."""

    def __init__(self, name, payload):
        self.type = "tool_use"
        self.name = name
        self.input = payload


class _FakeMessage:
    def __init__(self, blocks, input_tokens=1234):
        self.content = blocks
        self.usage = types.SimpleNamespace(
            input_tokens=input_tokens,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )


class _FakeAnthropic:
    """Scripted messages.create: pops one queued response per call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    @property
    def messages(self):
        return self

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


def _extract_block(rows):
    return _FakeBlock("record_metrics", {"values": rows})


def _verify_block(results):
    return _FakeBlock("verify_metrics", {"results": results})


def _make_extractor(responses, verify=True, prefilter=False):
    """A ClaudePdfExtractor whose client is the scripted fake (no real anthropic).

    prefilter defaults False: these tests stub _split_if_needed and feed fake PDF
    bytes, so they exercise the extract/verify path, not the pypdf prefilter (which
    has its own tests below).
    """
    pytest.importorskip("anthropic")
    from transitindex_ingest.pdf.claude_pdf import ClaudePdfExtractor

    ext = ClaudePdfExtractor(api_key="sk-test-not-real", verify=verify, prefilter=prefilter)
    ext._client = _FakeAnthropic(responses)
    return ext


def _request():
    return ExtractionRequest(agency_slug="ttc", pdf_bytes=b"%PDF-1.4 fake")


def _stub_split(ext):
    """Bypass pypdf: one chunk, offset 0, 3 pages."""
    ext._split_if_needed = lambda pdf_bytes: ([("ZmFrZQ==", 0)], 3)


# --- (a) extractor behavior with the fake client ----------------------------


def test_parses_tool_output_into_values():
    rows = [
        {
            "metric_code": "ridership",
            "value": "250000000",
            "unit": "count",
            "period_kind": "annual",
            "period_year": 2024,
            "page_number": 2,
            "confidence": 0.95,
        },
        {
            "metric_code": "operating_expenses",
            "value": "2100000000",
            "unit": "CAD",
            "period_kind": "annual",
            "period_year": 2024,
            "page_number": 2,
            "confidence": 0.9,
        },
    ]
    ext = _make_extractor([_FakeMessage([_extract_block(rows)])], verify=False)
    _stub_split(ext)

    result = ext.extract(_request())

    assert [v.metric_code for v in result.values] == [
        "ridership",
        "operating_expenses",
    ]
    assert result.values[0].value == Decimal("250000000")
    assert result.diagnostics["chunks"] == 1
    assert result.diagnostics["model"]
    assert result.diagnostics["input_tokens"] > 0


def test_verify_lowers_confidence():
    rows = [
        {
            "metric_code": "ridership",
            "value": "250000000",
            "unit": "count",
            "period_kind": "annual",
            "period_year": 2024,
            "page_number": 2,
            "confidence": 0.9,
        }
    ]
    verify = [{"index": 0, "supported": True, "confidence": 0.5}]
    ext = _make_extractor(
        [_FakeMessage([_extract_block(rows)]), _FakeMessage([_verify_block(verify)])]
    )
    _stub_split(ext)

    result = ext.extract(_request())

    assert len(result.values) == 1
    assert result.values[0].confidence == Decimal("0.5")
    assert result.diagnostics["verify_dropped"] == 0


def test_verify_drops_unsupported():
    rows = [
        {
            "metric_code": "ridership",
            "value": "250000000",
            "unit": "count",
            "period_kind": "annual",
            "period_year": 2024,
            "page_number": 2,
            "confidence": 0.9,
        }
    ]
    verify = [{"index": 0, "supported": False, "confidence": 0.0}]
    ext = _make_extractor(
        [_FakeMessage([_extract_block(rows)]), _FakeMessage([_verify_block(verify)])]
    )
    _stub_split(ext)

    result = ext.extract(_request())

    assert result.values == []
    assert result.diagnostics["verify_dropped"] == 1


def test_verify_corrects_value_and_records_note():
    rows = [
        {
            "metric_code": "ridership",
            "value": "250000000",
            "unit": "count",
            "period_kind": "annual",
            "period_year": 2024,
            "page_number": 2,
            "confidence": 0.9,
        }
    ]
    verify = [
        {
            "index": 0,
            "supported": True,
            "corrected_value": "250000001",
            "confidence": 0.9,
            "source_quote": "Total ridership 250,000,001",
        }
    ]
    ext = _make_extractor(
        [_FakeMessage([_extract_block(rows)]), _FakeMessage([_verify_block(verify)])]
    )
    _stub_split(ext)

    result = ext.extract(_request())

    (v,) = result.values
    assert v.value == Decimal("250000001")
    assert "verify-corrected from 250000000" in v.note
    assert v.source_quote == "Total ridership 250,000,001"


def _thousands_row():
    """One extract row as the model reports it: digits as printed ('2,240') in a
    '($000s)' table -> _row_to_value stores the final scaled value 2240000."""
    return {
        "metric_code": "operating_expenses",
        "value": "2,240",
        "unit": "CAD",
        "period_kind": "annual",
        "period_year": 2024,
        "page_number": 12,
        "confidence": 0.9,
        "printed_scale": "thousands",
    }


def test_verify_correction_reapplies_printed_scale():
    # A genuine correction (printed 2,245 not 2,240) arrives AS PRINTED with its
    # scale; the merged value must be the scaled 2,245,000 — never the raw 2245.
    verify = [
        {
            "index": 0,
            "supported": True,
            "corrected_value": "2,245",
            "printed_scale": "thousands",
            "confidence": 0.9,
        }
    ]
    ext = _make_extractor(
        [_FakeMessage([_extract_block([_thousands_row()])]), _FakeMessage([_verify_block(verify)])]
    )
    _stub_split(ext)

    (v,) = ext.extract(_request()).values

    assert v.value == Decimal("2245000")
    assert "verify-corrected from 2240000" in v.note


def test_verify_echoed_printed_digits_do_not_rescale():
    # THE 1000x regression: the model "corrects" with the printed digits ('2,240')
    # and omits the scale fields. The correction inherits the original reading's
    # printed_scale, so the value stays 2,240,000 — before the fix this overwrote
    # it with 2,240.
    verify = [
        {
            "index": 0,
            "supported": True,
            "corrected_value": "2,240",
            "confidence": 0.9,
        }
    ]
    ext = _make_extractor(
        [_FakeMessage([_extract_block([_thousands_row()])]), _FakeMessage([_verify_block(verify)])]
    )
    _stub_split(ext)

    (v,) = ext.extract(_request()).values

    assert v.value == Decimal("2240000")
    assert "verify-corrected" not in (v.note or "")  # same number -> no correction


def test_verify_catalogue_marks_scaled_values():
    # The verify prompt must tell the model the proposal is the FINAL value, not
    # the printed digits, so it doesn't "correct" every scaled number on sight.
    verify = [{"index": 0, "supported": True, "confidence": 0.9}]
    ext = _make_extractor(
        [_FakeMessage([_extract_block([_thousands_row()])]), _FakeMessage([_verify_block(verify)])]
    )
    _stub_split(ext)

    ext.extract(_request())

    prompt = ext._client.calls[1]["messages"][0]["content"][1]["text"]
    assert "2240000" in prompt
    assert "[printed in thousands]" in prompt


def test_french_numbers_parse():
    rows = [
        {
            "metric_code": "ridership",
            "value": "1 234 567",
            "unit": "count",
            "period_kind": "annual",
            "period_year": 2024,
            "page_number": 2,
            "confidence": 0.9,
        }
    ]
    verify = [{"index": 0, "supported": True, "confidence": 0.9}]
    ext = _make_extractor(
        [_FakeMessage([_extract_block(rows)]), _FakeMessage([_verify_block(verify)])]
    )
    _stub_split(ext)

    result = ext.extract(_request())

    assert result.values[0].value == Decimal("1234567")


def test_verify_false_disables_second_call():
    rows = [
        {
            "metric_code": "ridership",
            "value": "250000000",
            "unit": "count",
            "period_kind": "annual",
            "period_year": 2024,
            "page_number": 2,
            "confidence": 0.9,
        }
    ]
    ext = _make_extractor([_FakeMessage([_extract_block(rows)])], verify=False)
    _stub_split(ext)

    result = ext.extract(_request())

    assert len(ext._client.calls) == 1  # no verify call
    assert len(result.values) == 1


def test_document_block_uses_base64_and_cache_control():
    rows = [
        {
            "metric_code": "ridership",
            "value": "1",
            "unit": "count",
            "period_kind": "annual",
            "period_year": 2024,
            "page_number": 1,
            "confidence": 0.9,
        }
    ]
    ext = _make_extractor([_FakeMessage([_extract_block(rows)])], verify=False)
    _stub_split(ext)

    ext.extract(_request())

    block = ext._client.calls[0]["messages"][0]["content"][0]
    assert block["type"] == "document"
    assert block["source"]["type"] == "base64"
    assert block["source"]["media_type"] == "application/pdf"
    assert block["cache_control"] == {"type": "ephemeral"}


# --- (a continued) laziness proof: import without third-party deps -----------


def test_module_imports_without_anthropic_or_pypdf():
    import transitindex_ingest.pdf.claude_pdf as cp  # must not raise

    assert hasattr(cp, "ClaudePdfExtractor")


def test_no_top_level_third_party_imports():
    import transitindex_ingest.pdf.claude_pdf as cp

    with open(cp.__file__, encoding="utf-8") as fh:
        source = fh.read()
    # No module-level (column-0) imports of the optional deps.
    assert "\nimport anthropic" not in source
    assert "\nimport pypdf" not in source
    assert "\nfrom pypdf" not in source


# --- chunking guard (needs pypdf) -------------------------------------------


def _tiny_pdf(pages: int) -> bytes:
    from io import BytesIO

    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    buf = BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_split_returns_single_chunk_when_small():
    pytest.importorskip("pypdf")
    ext = _make_extractor([], verify=False)
    pdf_bytes = _tiny_pdf(2)

    chunks, page_count = ext._split_if_needed(pdf_bytes)

    assert page_count == 2
    assert len(chunks) == 1
    assert chunks[0][1] == 0  # offset


def test_split_chunks_and_reoffsets_pages(monkeypatch):
    pytest.importorskip("pypdf")
    import transitindex_ingest.pdf.claude_pdf as cp

    monkeypatch.setattr(cp, "ANTHROPIC_MAX_PAGES", 1)
    ext = _make_extractor([], verify=False)
    pdf_bytes = _tiny_pdf(2)

    chunks, page_count = ext._split_if_needed(pdf_bytes)

    assert page_count == 2
    assert [offset for _, offset in chunks] == [0, 1]
    # _reoffset re-bases a chunk-local page 1 onto the whole document.
    v = ExtractedValue(
        metric_code="ridership",
        value=Decimal("1"),
        unit="count",
        period_kind="annual",
        period_year=2024,
        page_number=1,
        confidence=Decimal("0.9"),
    )
    assert ext._reoffset(v, 1).page_number == 2


# --- (b) seam end-to-end through run_pdf -------------------------------------

PAGES = [(1, "page one"), (2, "stats"), (3, "notes")]
META = SourceRefMeta(document_type="annual_report", title="t")


class _StubExtractor:
    def __init__(self, values):
        self._values = values

    def extract(self, request):
        return ExtractionResult(values=list(self._values), diagnostics={})


def test_run_pdf_through_extractor_seam(repo):
    values = [
        ExtractedValue(
            metric_code="ridership",
            value=Decimal("250000000"),
            unit="count",
            period_kind="annual",
            period_year=2024,
            page_number=2,
            confidence=Decimal("0.4"),  # low -> flagged
            source_quote="Total ridership 250 million",
        )
    ]
    (pid,) = run_pdf(
        repo, PAGES, "ttc", source_ref_meta=META, extractor=_StubExtractor(values)
    )
    p = repo.get_pending_value(pid)
    assert p.review_status == "pending"
    assert "low_confidence" in p.flags


def test_source_quote_threaded_into_record_notes():
    # The verbatim snippet a reviewer sees lands in MetricValueRecord.notes.
    from transitindex_ingest.pdf.pipeline import _to_record

    ev = ExtractedValue(
        metric_code="ridership",
        value=Decimal("250000000"),
        unit="count",
        period_kind="annual",
        period_year=2024,
        page_number=2,
        confidence=Decimal("0.9"),
        note="restated",
        source_quote="Total ridership 250 million",
    )
    record = _to_record("ttc", ev, META)
    assert "restated" in record.notes
    assert "Total ridership 250 million" in record.notes


def test_run_pdf_rejects_both_or_neither(repo):
    with pytest.raises(ValueError):
        run_pdf(
            repo,
            PAGES,
            "ttc",
            source_ref_meta=META,
            extractor=_StubExtractor([]),
            llm_client=FakeLLMClient([]),
        )
    with pytest.raises(ValueError):
        run_pdf(repo, PAGES, "ttc", source_ref_meta=META)


def test_legacy_llm_client_path_unchanged(repo):
    values = [
        ExtractedValue(
            metric_code="fleet_size",
            value=Decimal("2000"),
            unit="count",
            period_kind="annual",
            period_year=2024,
            page_number=3,
            confidence=Decimal("0.88"),
        )
    ]
    (pid,) = run_pdf(
        repo, PAGES, "ttc", source_ref_meta=META, llm_client=FakeLLMClient(values)
    )
    p = repo.get_pending_value(pid)
    assert p.confidence == Decimal("0.88")
    assert p.page_number == 3


def test_isinstance_extractor_protocol():
    assert isinstance(_StubExtractor([]), Extractor)
    assert isinstance(FakeExtractor([]), Extractor)
    assert isinstance(
        LegacyTextExtractor(FakeLLMClient([]), EXTRACTION_SYSTEM_PROMPT), Extractor
    )


# --- (c) page prefilter -----------------------------------------------------

from transitindex_ingest.pdf.claude_pdf import score_page, select_page_indices


def test_score_page_rewards_metrics_and_numbers():
    dense = "Annual ridership was 250,000,000 and operating expenses 2,100,000,000."
    sparse = "Thank you for reading this introductory letter."
    assert score_page(dense) > score_page(sparse)
    assert score_page("") == 0


def test_select_page_indices_keeps_head_plus_dense_pages():
    texts = ["cover", "intro", "contents"] + [f"filler {i}" for i in range(3, 8)]
    texts[5] = "Ridership 250000000 revenue 1000000 expenses 2100000000"  # dense
    # head 0,1,2 always kept; the one remaining slot goes to the dense page 5.
    assert select_page_indices(texts, max_pages=4) == [0, 1, 2, 5]


def test_select_page_indices_sends_all_when_doc_fits():
    texts = ["a", "b", "c", "d"]
    assert select_page_indices(texts, max_pages=10) == [0, 1, 2, 3]


def test_select_page_indices_caps_at_max_pages_in_document_order():
    texts = [f"ridership {i}000000 revenue {i}00000" for i in range(1, 6)]
    keep = select_page_indices(texts, max_pages=2)
    assert len(keep) == 2
    assert keep == sorted(keep)


def test_select_page_indices_falls_back_when_nothing_scores():
    keep = select_page_indices(["", "   ", "no data here", "still nothing"], max_pages=2)
    assert len(keep) == 2  # never returns empty (e.g. a scanned PDF)


def test_remap_page_back_to_original():
    ext = _make_extractor([], verify=False)
    v = ExtractedValue(
        metric_code="ridership", value=Decimal("1"), unit="count",
        period_kind="annual", period_year=2024, page_number=2, confidence=Decimal("0.9"),
    )
    assert ext._remap_page(v, {1: 4, 2: 9}).page_number == 9   # filtered p2 -> original p9
    assert ext._remap_page(v, {1: 4}).page_number == 2         # unknown -> unchanged


def test_filter_pdf_keeps_all_when_no_text():
    pytest.importorskip("pypdf")
    ext = _make_extractor([], verify=False)
    pdf_bytes = _tiny_pdf(3)  # blank pages -> no text -> fallback keeps all, no remap
    filtered, page_map, total, selected = ext._filter_pdf(pdf_bytes)
    assert total == 3
    assert page_map is None
    assert filtered is pdf_bytes
    assert selected == [1, 2, 3]


# --- (d) dual-model extractor ----------------------------------------------

from transitindex_ingest.pdf.ensemble import DualModelExtractor, reconcile


def _ev(metric, value, conf=0.9, year=2024, unit="count"):
    return ExtractedValue(
        metric_code=metric, value=Decimal(str(value)), unit=unit,
        period_kind="annual", period_year=year, page_number=1,
        confidence=Decimal(str(conf)),
    )


def test_reconcile_agreement_is_trusted():
    (v,) = reconcile({
        "opus": [_ev("ridership", 250000000, 0.9)],
        "sonnet": [_ev("ridership", 250000000, 0.8)],
    })
    assert v.value == Decimal("250000000")
    assert v.confidence == Decimal("0.9")  # higher of the two; not lowered
    assert "agree" in v.note


def test_reconcile_disagreement_flagged_with_both_values():
    (v,) = reconcile({
        "opus": [_ev("ridership", 250000000, 0.9)],
        "sonnet": [_ev("ridership", 251000000, 0.9)],
    })
    assert v.confidence <= Decimal("0.5")  # surfaces in review queue
    assert "250000000" in v.note and "251000000" in v.note
    assert "disagree" in v.note


def test_reconcile_single_model_find_flagged():
    (v,) = reconcile({
        "opus": [_ev("fleet_size", 2000, 0.95)],
        "sonnet": [],
    })
    assert v.confidence <= Decimal("0.5")
    assert "only opus" in v.note


def test_dual_extractor_runs_both_and_reconciles():
    dual = DualModelExtractor({
        "opus": FakeExtractor([_ev("ridership", 250000000, 0.9)]),
        "sonnet": FakeExtractor([_ev("ridership", 250000000, 0.8)]),
    })
    result = dual.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"x"))
    assert len(result.values) == 1
    assert result.diagnostics["per_model_counts"] == {"opus": 1, "sonnet": 1}
    assert result.diagnostics["reconciled_count"] == 1


def test_dual_extractor_survives_one_model_error():
    class _Boom:
        def extract(self, request):
            raise RuntimeError("rate limited")

    dual = DualModelExtractor({
        "opus": _Boom(),
        "sonnet": FakeExtractor([_ev("ridership", 250000000, 0.9)]),
    })
    result = dual.extract(ExtractionRequest(agency_slug="ttc", pdf_bytes=b"x"))
    assert len(result.values) == 1                       # sonnet's find survives
    assert "opus" in result.diagnostics["errors"]
    assert result.values[0].confidence <= Decimal("0.5")  # flagged (single model)


def test_dual_extractor_is_extractor_protocol():
    assert isinstance(DualModelExtractor({"m": FakeExtractor([])}), Extractor)


def test_ensemble_imports_without_third_party():
    import transitindex_ingest.pdf.ensemble as ens  # must not raise

    assert hasattr(ens, "DualModelExtractor")
