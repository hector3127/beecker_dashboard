"""Tarjeta Operations: ultimo mes cerrado, meta y grafica."""

from datetime import date

from apps.portal.services.facturability import (
    build_month_facturability,
    person_month_hours,
)
from apps.portal.services.operations_summary import (
    build_chart_bars,
    build_operations_summary,
    last_closed_month,
)


def month(value, aer_percent, variable_percent=0, people=1):
    """Mes cuya facturabilidad da exactamente los porcentajes pedidos."""
    capacity = people * person_month_hours(value)

    def row(service, percent):
        return {
            "recurso": "A",
            "area": "DEV",
            "servicio": service,
            "horas": percent * capacity / 100,
            "categorias": ["Facturable"],
        }

    gse = {
        "areas": [{"area": "DEV", "recursos": people, "personas": []}],
        "detalle": [row("AER", aer_percent), row("IXB", variable_percent)],
    }

    return build_month_facturability(value, gse)


def test_last_closed_month():
    assert last_closed_month(date(2026, 10, 13)) == "2026-09"
    assert last_closed_month(date(2026, 1, 20)) == "2026-01"
    assert last_closed_month(date(2026, 12, 1)) == "2026-11"


def test_summary_above_and_below_target():
    above = build_operations_summary([month("2026-08", 50, 30)])
    below = build_operations_summary(
        [month("2026-08", 50, 30), month("2026-09", 40, 10)],
        month_closed=False,
    )

    assert above.selected.global_percent == 80.0
    assert above.gap == 10.0
    assert above.gap_abs == 10.0
    assert above.month_label == "Agosto 2026"
    assert below.gap == -20.0
    assert below.gap_abs == 20.0
    assert below.month_closed is False
    assert [bar.label for bar in below.bars] == ["Ago", "Sep"]


def test_summary_without_months_or_capacity():
    empty = build_operations_summary([])
    no_capacity = build_operations_summary([month("2026-08", 10, 0, 0)])

    assert empty.selected is None
    assert empty.gap is None
    assert empty.bars == ()
    assert no_capacity.gap is None
    assert no_capacity.bars[0].value_text == "—"


def test_chart_bars_positions():
    bars = build_chart_bars(
        [month("2026-01", 68), month("2026-02", 99.5), month("2026-03", 200)],
    )

    assert [bar.value_text for bar in bars] == ["68%", "99.5%", "200%"]
    assert bars[0].width == 40.0
    assert bars[0].height == 53.0
    assert bars[0].y == 47.0
    assert bars[2].height == 89.7
    assert [bar.current for bar in bars] == [False, False, True]
    assert bars[1].x > bars[0].x
