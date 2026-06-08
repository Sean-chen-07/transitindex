"""parse_number + scale/sign handling for PDF extraction (stdlib + pytest)."""

from __future__ import annotations

from decimal import Decimal

from transitindex_ingest.pdf.llm import _row_to_value, apply_scale_sign, parse_number


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
