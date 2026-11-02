"""Inversión requiere la etiqueta exacta, no nombres ni textos semejantes."""

import pytest

from core.time_entries.investment import investment_categories


@pytest.mark.parametrize(
    "tags,expected",
    [
        ([" INV_OPERATIVA ", "inv_comercial"], ("operational", "commercial")),
        (["INV_OPERATIVA", "INV_OPERATIVA"], ("operational",)),
        (
            [
                "Pre-Venta",
                "Internos",
                "Inversión Operaciones",
                "Inversión Comercial",
            ],
            (),
        ),
        (["NO_INV_OPERATIVA", "INV_COMERCIAL_EXTRA", "INV OPERATIVA"], ()),
        ([], ()),
    ],
)
def test_exact_investment_tags(tags, expected):
    assert investment_categories(tags) == expected
