"""El color de Advance depende exclusivamente del presupuesto de horas."""

from apps.ejecutivo.services.ixb_summary import hours_consumption_color


def test_consumption_within_budget_is_green():
    assert hours_consumption_color(20, 100) == "en_rango"
    assert hours_consumption_color(80, 100) == "en_rango"
    assert hours_consumption_color(0, 100) == "en_rango"


def test_exact_budget_is_green():
    assert hours_consumption_color(100, 100) == "en_rango"


def test_exceeded_budget_is_red_even_if_percentage_rounds_to_100():
    assert hours_consumption_color(120, 100) == "atrasado"
    assert hours_consumption_color(100.01, 100) == "atrasado"


def test_missing_budget_is_neutral():
    assert hours_consumption_color(80, 0) == "sin_presupuesto"
    assert hours_consumption_color(80, -1) == "sin_presupuesto"
