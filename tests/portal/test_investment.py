"""Inversion operativa y comercial desde el detalle de GSE."""

from apps.portal.services.investment import (
    build_bars,
    build_investment_view,
    classify_investment,
)


def row(area, project, categories, hours):
    return {
        "recurso": "X",
        "area": area,
        "proyecto": project,
        "categorias": categories,
        "horas": hours,
    }


GSE = {
    "ok": True,
    "detalle": [
        row("DEV", "Preventa Acme", ["No Facturables", "Pre-Venta"], 42),
        row("DEV", "Interno", ["Internos"], 60),
        row("QA", "Inv QA", ["Inversión Operaciones"], 35),
        row("BA", "Propuesta", ["Inversion Comercial"], 28),
        row("DEV", "AER.001", ["Facturable"], 100),
        row("", "", ["Internos"], 5),
        "x",
    ],
}


def test_classify_investment():
    assert classify_investment(["Pre-Venta", "Internos"]) == (
        "comercial",
        "Pre-Venta",
    )
    assert classify_investment(["Inversión Operaciones"])[0] == "operativa"
    assert classify_investment(["Facturable"]) == ("", "")
    assert classify_investment([None]) == ("", "")


def test_view_totals_areas_and_bars():
    view = build_investment_view(GSE, "2026-10")

    assert view.label == "Octubre 2026"
    assert (view.totals.commercial, view.totals.operational) == (70, 100)
    assert view.totals.total == 170
    assert [item.name for item in view.by_area] == [
        "DEV",
        "QA",
        "BA",
        "Sin especialidad",
    ]
    assert view.by_area[0].commercial == 42
    assert [bar.label for bar in view.commercial_by_type] == [
        "Pre-Venta",
        "Inversion Comercial",
    ]
    assert view.commercial_by_type[1].width == 66.7
    assert view.operational_by_project[0].label == "Interno"
    assert view.operational_by_project[-1].label == "Sin proyecto"


def test_view_without_data():
    view = build_investment_view({}, "2026-10")

    assert view.totals.total == 0
    assert view.by_area == ()
    assert view.commercial_by_type == ()


def test_bars_group_the_rest_in_others():
    bars = build_bars({f"P{index}": float(index) for index in range(1, 10)})

    assert [bar.label for bar in bars][:2] == ["P9", "P8"]
    assert bars[-1].label == "Otros"
    assert bars[-1].hours == 6
    assert len(bars) == 7
