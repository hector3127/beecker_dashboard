from core.utils.cell_types import SheetRow
from core.utils.text import (
    get_flexible_value,
    header_map,
    normalize_name,
    strip_accents,
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


def test_normalization_is_remembered_but_values_other_than_text_still_work():
    assert normalize_name(5.0) == "5"
    assert normalize_name(None) == ""
    assert normalize_name(True) == "true"
    assert normalize_name("  ÁÉÍ ") == normalize_name("áéí") == "aei"
    assert strip_accents("Ñandú") == strip_accents("Ñandú") == "Nandu"


def test_header_map_is_shared_between_rows_with_the_same_columns():
    first = {"Cliente": "A", "Nombre": "B"}
    second = {"Cliente": "C", "Nombre": "D"}

    assert header_map(tuple(first)) is header_map(tuple(second))
    assert get_flexible_value(first, ["cliente"]) == "A"
    assert get_flexible_value(second, ["CLIÉNTE", "nombre"]) == "C"
    assert get_flexible_value(second, ["inexistente", "nombre"]) == "D"


def test_two_headers_that_normalize_alike_resolve_to_the_last_one():
    row = {"Posición": "primero", "posicion": "ultimo"}

    assert get_flexible_value(row, ["POSICION"]) == "ultimo"


def test_text_or_default_uses_javascript_truthiness():
    assert text_or_default("", "ID-1") == "ID-1"
    assert text_or_default(0, "ID-1") == "ID-1"
    assert text_or_default("Nombre", "ID-1") == "Nombre"
