"""Tests for selectable date overlay parts and font fitting."""

from sisr.core import (
    format_datetime,
    normalize_date_parts,
    overlay_font_size_for_text,
    parse_datetime,
    validate_date,
)

RAW = "2024:01:05 13:30:00"


def test_normalize_date_parts_defaults_and_overrides():
    assert normalize_date_parts(None) == {
        "day": True,
        "month": True,
        "date": True,
        "year": True,
        "time": True,
    }
    assert normalize_date_parts({"time": False, "day": False})["time"] is False
    assert normalize_date_parts({"time": False})["month"] is True


def test_format_datetime_full_matches_legacy():
    assert format_datetime(RAW) == "Friday, January 05, 2024 01:30PM"
    assert format_datetime(RAW, {"time": False}) == "Friday, January 05, 2024"


def test_format_datetime_individual_parts():
    assert format_datetime(RAW, {
        "day": True, "month": False, "date": False, "year": False, "time": False,
    }) == "Friday"
    assert format_datetime(RAW, {
        "day": False, "month": True, "date": False, "year": False, "time": False,
    }) == "January"
    assert format_datetime(RAW, {
        "day": False, "month": False, "date": True, "year": False, "time": False,
    }) == "05"
    assert format_datetime(RAW, {
        "day": False, "month": False, "date": False, "year": True, "time": False,
    }) == "2024"
    assert format_datetime(RAW, {
        "day": False, "month": False, "date": False, "year": False, "time": True,
    }) == "01:30PM"


def test_format_datetime_combinations_read_naturally():
    assert format_datetime(RAW, {
        "day": False, "month": True, "date": True, "year": True, "time": False,
    }) == "January 05, 2024"
    assert format_datetime(RAW, {
        "day": False, "month": True, "date": False, "year": True, "time": False,
    }) == "January 2024"
    assert format_datetime(RAW, {
        "day": True, "month": True, "date": True, "year": False, "time": True,
    }) == "Friday, January 05 01:30PM"
    assert format_datetime(RAW, {
        "day": True, "month": False, "date": False, "year": False, "time": True,
    }) == "Friday 01:30PM"
    assert format_datetime(RAW, {
        "day": False, "month": False, "date": True, "year": True, "time": False,
    }) == "05, 2024"


def test_format_datetime_all_disabled_is_empty():
    assert format_datetime(RAW, {
        "day": False, "month": False, "date": False, "year": False, "time": False,
    }) == ""


def test_format_datetime_accepts_already_formatted():
    formatted = format_datetime(RAW)
    assert format_datetime(formatted, {
        "day": False, "month": True, "date": True, "year": True, "time": False,
    }) == "January 05, 2024"


def test_parse_and_validate():
    assert parse_datetime(RAW) is not None
    assert validate_date("Friday, January 05, 2024 01:30PM")
    assert validate_date("2024:01:05")
    assert not validate_date("not a date")


def test_overlay_font_size_shrinks_for_long_text():
    short = overlay_font_size_for_text("2024", 640, 360)
    long = overlay_font_size_for_text(
        "Wednesday, September 30, 2026 12:00PM",
        640,
        360,
    )
    assert short >= long
    assert long >= 12
