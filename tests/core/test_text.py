from core.utils.cell_types import SheetRow
from core.utils.text import (
    get_flexible_value,
    normalize_name,
    text_or_default,
    to_text,
)


def test_normalize_name_removes_accents_and_case():
    assert normalize_name("  José PÉREZ ") == "jose perez"


def test_to_text_formats_integral_floats_like_javascript():
    assert to_text(5.0) == "5"
    assert to_text(5.25) == "5.25"
    assert to_text(None) == ""
    assert to_text(True) == "true"


def test_get_flexible_value_ignores_accents_and_spaces():
    row: SheetRow = {" Posición ": "QA", "Horas Estimadas": 0}

    assert get_flexible_value(row, ["posicion"]) == "QA"
    assert get_flexible_value(row, ["Horas_Estimadas", "Horas Estimadas"]) == 0
    assert get_flexible_value(row, ["No existe"]) == ""


def test_text_or_default_uses_javascript_truthiness():
    assert text_or_default("", "ID-1") == "ID-1"
    assert text_or_default(0, "ID-1") == "ID-1"
    assert text_or_default("Nombre", "ID-1") == "Nombre"
