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


def test_reference_breakdown_reconciles_with_existing_totals():
    from apps.portal.services.investment import investment_breakdown

    view = build_investment_view(GSE, "2026-10")
    detail = investment_breakdown(GSE, view)
    assert sum(row["total"] for row in detail["people"]) == view.totals.total
    assert sum(row["commercial"] for row in detail["people"]) == 70
    assert sum(row["operational"] for row in detail["people"]) == 100
    assert detail["operational_share"] == 58.8
    assert detail["commercial_share"] == 41.2
    assert detail["areas"][0]["share"] == 60
    assert (
        investment_breakdown({}, build_investment_view({}, "2026-10"))[
            "operational_share"
        ]
        == 0
    )


def test_person_projects_reconcile_and_keep_commercial_operational_separate():
    from apps.portal.services.investment import investment_breakdown

    data = {
        "detalle": [
            {**row("DEV", "P1", ["Pre-Venta"], 2), "recurso": "Ana"},
            {**row("DEV", "P1", ["Internos"], 3), "recurso": "Ana"},
            {**row("DEV", "P2", ["Internos"], 1), "recurso": "Ana"},
            {**row("QA", "P3", ["Internos"], 10), "recurso": "Luis"},
            {**row("DEV", "Excluded", ["Facturable"], 99), "recurso": "Ana"},
        ]
    }
    people = investment_breakdown(data, build_investment_view(data, "2026-10"))[
        "people"
    ]
    ana = next(p for p in people if p["name"] == "Ana")
    assert ana["total"] == 6
    assert ana["projects"] == [
        {"name": "P1", "commercial": 2, "operational": 3, "total": 5},
        {"name": "P2", "commercial": 0, "operational": 1, "total": 1},
    ]
    assert sum(p["total"] for p in ana["projects"]) == ana["total"]


def test_accumulated_active_projects_keep_old_hours_and_reconcile_people():
    from datetime import date

    from apps.portal.services.investment import accumulated_investment_context

    records = [
        {
            "resource": "Ana",
            "project": "AER.1",
            "category": "operational",
            "hours": 100,
            "day": "2025-01-01",
        },
        {
            "resource": "Ana",
            "project": "IXB.2",
            "category": "commercial",
            "hours": 5,
            "day": "2026-09-03",
        },
        {
            "resource": "Luis",
            "project": "IXB.2",
            "category": "operational",
            "hours": 20,
            "day": "2026-10-30",
        },
        {
            "resource": "Sin rol",
            "project": "IXB.2",
            "category": "operational",
            "hours": 2,
            "day": None,
        },
    ]
    context = accumulated_investment_context(
        {"complete": True, "records": records, "projects": 2},
        date(2026, 10, 31),
        {"ana": "DEV"},
    )
    totals = context["investment"].totals
    assert totals.commercial == 5
    assert totals.operational == 122
    assert (
        sum(p["total"] for p in context["investment_detail"]["people"]) == 127
    )
    for person in context["investment_detail"]["people"]:
        assert sum(p["total"] for p in person["projects"]) == person["total"]
    history = context["investment_chart"]["history"]
    assert history[0]["operational"] == 100
    assert history[-1]["operational"] == 120
    assert history[-1]["commercial"] == 5
    assert context["investment_chart"]["undated"] == 2
    assert context["investment_from"] == "2025-01-01"


def test_incomplete_accumulated_source_does_not_present_partial_hours():
    from datetime import date

    from apps.portal.services.investment import accumulated_investment_context

    context = accumulated_investment_context(
        {"complete": False, "error": "Clockify", "records": [{"hours": 100}]},
        date(2026, 10, 31),
    )
    assert not context["investment_ready"]
    assert context["investment_detail"]["people"] == []
    assert context["error"] == "Clockify"
