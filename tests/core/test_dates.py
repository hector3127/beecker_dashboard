from datetime import date, datetime

from core.utils.dates import format_iso_date, to_datetime


def test_serial_number_is_converted_from_sheets_epoch():
    assert to_datetime(46113) == datetime(2026, 4, 1)
    assert to_datetime(46113.5) == datetime(2026, 4, 1, 12, 0)


def test_text_dates_in_iso_and_mexican_formats():
    assert to_datetime("2026-03-15") == datetime(2026, 3, 15)
    assert to_datetime("15/03/2026") == datetime(2026, 3, 15)
    assert to_datetime("2026-03-15T18:00:00Z") == datetime(2026, 3, 15, 12)


def test_invalid_values_return_none():
    assert to_datetime("") is None
    assert to_datetime("sin fecha") is None
    assert to_datetime(None) is None
    assert to_datetime(True) is None


def test_date_objects_and_format():
    assert to_datetime(date(2026, 1, 2)) == datetime(2026, 1, 2)
    assert format_iso_date(datetime(2026, 1, 2, 23, 59)) == "2026-01-02"
