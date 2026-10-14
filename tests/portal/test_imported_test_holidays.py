"""Festivos oficiales de Mexico y dias habiles."""

from datetime import date

from apps.portal.services.holidays import (
    count_business_days,
    mexican_holidays,
    nth_monday,
)


def test_movable_holidays_fall_on_mondays():
    assert nth_monday(2026, 2, 1) == date(2026, 2, 2)
    assert nth_monday(2026, 3, 3) == date(2026, 3, 16)
    assert nth_monday(2026, 11, 3) == date(2026, 11, 16)


def test_holidays_2026_and_transmission_years():
    assert mexican_holidays(2026) == frozenset(
        {
            date(2026, 1, 1),
            date(2026, 2, 2),
            date(2026, 3, 16),
            date(2026, 5, 1),
            date(2026, 9, 16),
            date(2026, 11, 16),
            date(2026, 12, 25),
        },
    )
    assert date(2030, 10, 1) in mexican_holidays(2030)
    assert date(2026, 10, 1) not in mexican_holidays(2026)


def test_business_days_by_month():
    days = [count_business_days(f"2026-{month:02d}") for month in range(1, 13)]

    assert days == [21, 19, 21, 22, 20, 22, 23, 21, 21, 22, 20, 22]


def test_current_month_counts_until_today():
    assert count_business_days("2026-10", date(2026, 10, 12)) == 8
    assert count_business_days("2026-09", date(2026, 10, 12)) == 21
