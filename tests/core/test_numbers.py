import pytest

from core.utils.numbers import round_half_up, round_half_up_int, to_number


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (2.5, 3),
        (-2.5, -2),
        (0.49, 0),
        (99.5, 100),
    ],
)
def test_round_half_up_int_matches_javascript(value, expected):
    assert round_half_up_int(value) == expected


def test_round_half_up_keeps_decimals():
    assert round_half_up(12.345, 2) == 12.35
    assert round_half_up(-0.05, 1) == 0.0


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("12", 12.0),
        (" 7.5 ", 7.5),
        ("", 0.0),
        ("1,200", 0.0),
        ("abc", 0.0),
        (None, 0.0),
        (True, 1.0),
        (float("nan"), 0.0),
        (40, 40.0),
    ],
)
def test_to_number_behaves_like_number_or_zero(value, expected):
    assert to_number(value) == expected
