"""parse_number + scale/sign handling for PDF extraction (stdlib + pytest)."""

from __future__ import annotations

from decimal import Decimal

from transitindex_ingest.pdf.llm import (
    ExtractedValue,
    _row_to_value,
    apply_scale_sign,
    parse_number,
    quote_supports_value,
    value_from_dict,
    value_to_dict,
)


# --- parse_number -----------------------------------------------------------


def test_parse_number_french_and_space_separators_unchanged():
    assert parse_number("1 234 567") == Decimal("1234567")
    assert parse_number("12,5") == Decimal("12.5")
    assert parse_number("4200") == Decimal("4200")


def test_parse_number_accounting_parentheses_are_negative():
    assert parse_number("(1234)") == Decimal("-1234")  # was a ValueError (dropped value) before
    assert parse_number("(0)") == Decimal("0")


def test_parse_number_english_comma_thousands():
    # Comma thousands separators are stripped, NOT read as a decimal point. Before the
    # fix "1,234" silently became 1.234 (1000x too small) and "250,000,000" raised.
    assert parse_number("1,234") == Decimal("1234")
    assert parse_number("250,000,000") == Decimal("250000000")
    assert parse_number("1,234.56") == Decimal("1234.56")
    assert parse_number("(1,234)") == Decimal("-1234")


def test_parse_number_french_comma_decimal_still_works():
    # A lone comma trailing 1-2 digits stays a decimal separator, including alongside
    # French space-thousands ("1 234,56" -> 1234.56).
    assert parse_number("12,5") == Decimal("12.5")
    assert parse_number("1 234,56") == Decimal("1234.56")


# --- apply_scale_sign -------------------------------------------------------


def test_apply_scale_sign():
    assert apply_scale_sign(Decimal("1.5"), "thousands", "positive") == Decimal("1500")
    assert apply_scale_sign(Decimal("2"), "millions", "positive") == Decimal("2000000")
    assert apply_scale_sign(Decimal("1234"), "units", "negative") == Decimal("-1234")
    assert apply_scale_sign(Decimal("42"), "units", "positive") == Decimal("42")


# --- _row_to_value applies scale + sign -------------------------------------


def _row(**over) -> dict:
    base = dict(
        metric_code="operating_expenses",
        value="2370",
        unit="CAD",
        period_kind="annual",
        period_year=2024,
        page_number=4,
        confidence=0.9,
    )
    base.update(over)
    return base


def test_row_to_value_scales_thousands():
    # "(in thousands)" statement: 2,370 printed -> $2,370,000.
    ev = _row_to_value(_row(value="2370", printed_scale="thousands"))
    assert ev.value == Decimal("2370000")
    assert ev.printed_scale == "thousands"


def test_row_to_value_applies_negative_sign():
    ev = _row_to_value(_row(metric_code="net_debt", value="500", printed_sign="negative"))
    assert ev.value == Decimal("-500")
    assert ev.printed_sign == "negative"


def test_row_to_value_defaults_leave_value_as_printed():
    ev = _row_to_value(_row(value="419900000"))
    assert ev.value == Decimal("419900000")
    assert ev.printed_scale == "units"
    assert ev.printed_sign == "positive"


# --- value_to_dict / value_from_dict round-trip -----------------------------


def test_value_dict_round_trip_lossless_all_fields():
    v = ExtractedValue(
        metric_code="operating_revenue",
        value=Decimal("1234.56"),
        unit="CAD",
        period_kind="monthly",
        period_year=2024,
        page_number=7,
        confidence=Decimal("0.83"),
        period_month=3,
        note="restated",
        source_quote="Total revenue 1,234.56",
        printed_scale="thousands",
        printed_sign="negative",
    )
    d = value_to_dict(v)
    # Decimal fields serialize as strings.
    assert d["value"] == "1234.56"
    assert d["confidence"] == "0.83"
    assert value_from_dict(d) == v


def test_value_dict_round_trip_with_optional_fields_none():
    v = ExtractedValue(
        metric_code="ridership",
        value=Decimal("250000000"),
        unit="count",
        period_kind="annual",
        period_year=2024,
        page_number=2,
        confidence=Decimal("0.9"),
    )
    assert value_from_dict(value_to_dict(v)) == v
    assert value_to_dict(v)["period_month"] is None
    assert value_to_dict(v)["note"] is None
    assert value_to_dict(v)["source_quote"] is None


# --- quote_supports_value ---------------------------------------------------


def test_quote_supports_value_exact():
    assert quote_supports_value("250000000", "Total ridership 250000000 in 2024") is None


def test_quote_supports_value_comma_thousands_quote():
    # Printed plain digits found inside a comma-grouped quote.
    assert quote_supports_value("250000000", "Ridership of 250,000,000 riders") is None


def test_quote_supports_value_french_comma_decimal():
    # English-printed "525.5" matches a French comma-decimal quote "525,5".
    assert quote_supports_value("525.5", "Recettes de 525,5 millions") is None


def test_quote_supports_value_missing_quote():
    assert quote_supports_value("250000000", None) == "missing"
    assert quote_supports_value("250000000", "   ") == "missing"


def test_quote_supports_value_wrong_digits():
    assert quote_supports_value("250000000", "Ridership of 251,000,000") == "mismatch"


# --- _row_to_value: canonical unit + source-quote confidence caps ------------


def test_row_to_value_uses_canonical_unit_not_free_text():
    # Model free-text unit "thousands of dollars" is discarded for the canonical CAD.
    ev = _row_to_value(
        _row(
            metric_code="operating_expenses",
            unit="thousands of dollars",
            source_quote="Operating expenses 2,370",
        )
    )
    assert ev.unit == "CAD"


def test_row_to_value_caps_confidence_when_quote_missing():
    ev = _row_to_value(_row(value="2370", confidence=0.9))  # no source_quote
    assert ev.confidence == Decimal("0.5")
    assert "no source quote" in ev.note


def test_row_to_value_caps_confidence_when_quote_mismatch():
    ev = _row_to_value(
        _row(value="2370", confidence=0.9, source_quote="Operating expenses 9,999")
    )
    assert ev.confidence == Decimal("0.3")
    assert "value not found in its source quote" in ev.note


def test_row_to_value_quote_supports_keeps_confidence_and_note():
    ev = _row_to_value(
        _row(
            value="2370",
            confidence=0.9,
            note="restated",
            source_quote="Operating expenses 2,370 thousand",
        )
    )
    assert ev.confidence == Decimal("0.9")
    assert ev.note == "restated"  # no cap note appended when the quote supports it
