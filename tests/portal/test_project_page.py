"""Pantalla de un proyecto."""

from datetime import date

from apps.portal.services.decisions import decision_for
from apps.portal.services.project_page import build_project_page
from tests.portal.builders import make_project

TODAY = date(2026, 10, 12)


def make_dashboard(**overrides):
    data = {
        "proyecto": {
            "fechaInicio": "2026-05-05T00:00:00.000Z",
            "fechaFinEstimada": "2026-10-28T00:00:00.000Z",
        },
        "avance": {"pctTiempoTranscurrido": 91.2},
        "riesgosCriticos": [
            {
                "descripcion": "Acceso",
                "impacto": "Alto",
                "probabilidad": "Alta",
            },
        ],
        "filasRecursosCompleto": [
            {"posicion": "DEV", "nombre": "A", "horasReales": 300},
            {"posicion": "DEV", "nombre": "B", "horasReales": 220.4},
            {"posicion": "QA", "nombre": "C", "horasReales": 240},
            {"posicion": "", "nombre": "D", "horasReales": "x"},
        ],
        "hitos": [
            {
                "nombre": "Discovery",
                "estado": "Completado",
                "fechaFinPlan": "2026-06-01T00:00:00.000Z",
                "fechaFinReal": "2026-06-10T00:00:00.000Z",
            },
            {
                "nombre": "Integracion",
                "estado": "En curso",
                "fechaFinPlan": "2026-10-15T00:00:00.000Z",
            },
            {"nombre": "Sin fecha", "estado": "Pendiente"},
        ],
    }
    data.update(overrides)

    return data


def critical_project(**overrides):
    values = {
        "project_id": "HIS-1",
        "name": "HIS",
        "health": "Crítica",
        "budget_hours": 400.0,
        "burn_hours": 500.0,
        "progress_percent": 50,
        "etc_hours": 120.0,
    }
    values.update(overrides)

    return make_project(**values)


def test_numbers_bars_and_summary():
    page = build_project_page(critical_project(), make_dashboard(), TODAY)

    assert page.budget_used == 125
    assert (page.budget_hours, page.burn_hours) == (400, 500)
    assert page.etc_hours == 120
    assert page.status_label == "Crítico"
    assert page.end_date == "28/10/2026"
    assert [bar.percent_text for bar in page.bars] == ["125%", "50%", "91%"]
    assert page.bars[0].color == "#D6304B"
    assert page.bars[0].width == 83.3
    assert page.marker_left == 66.7
    assert page.summary == (
        "Lo gastado va 75 puntos por encima del trabajo avanzado. "
        "Con 91% del tiempo transcurrido, quedan 16 días para la fecha "
        "de entrega."
    )
    assert page.client_slug == "acme"


def test_summary_variants():
    ahead = build_project_page(
        make_project(burn_hours=25.0, progress_percent=40),
        make_dashboard(),
        TODAY,
    )
    even = build_project_page(
        make_project(burn_hours=40.0, progress_percent=40),
        {},
        TODAY,
    )
    late = build_project_page(
        critical_project(),
        make_dashboard(
            proyecto={"fechaFinEstimada": "2026-10-02T00:00:00.000Z"},
        ),
        TODAY,
    )

    assert ahead.summary.startswith("El trabajo avanzado va 15 puntos")
    assert even.summary == "Lo gastado y el trabajo avanzado van parejos."
    assert "pasó hace 10 días" in late.summary


def test_risks_team_and_events():
    page = build_project_page(critical_project(), make_dashboard(), TODAY)

    assert [(r.description, r.impact) for r in page.risks] == [
        ("Acceso", "Alto"),
    ]
    assert [(t.role, t.people, t.hours) for t in page.team] == [
        ("DEV", 2, 520),
        ("QA", 1, 240),
        ("Sin rol", 1, 0),
    ]
    assert [e.title for e in page.events] == [
        "Fecha estimada de entrega",
        "Integracion",
        "Discovery",
        "Inicio del proyecto",
    ]
    assert [e.done for e in page.events] == [False, False, True, True]
    assert page.events[2].text == "Completado. Fin planeado: 01/06/2026"


def test_page_without_dashboard_keeps_portfolio_data():
    page = build_project_page(critical_project(), {}, TODAY)

    assert page.budget_used == 125
    assert page.end_date == ""
    assert [bar.label for bar in page.bars] == [
        "Presupuesto usado",
        "Avance en horas",
    ]
    assert page.risks == ()
    assert page.team == ()
    assert page.events == ()
    assert page.summary == (
        "Lo gastado va 75 puntos por encima del trabajo avanzado."
    )


def test_page_with_malformed_dashboard():
    page = build_project_page(
        critical_project(),
        {
            "proyecto": "x",
            "avance": [],
            "riesgosCriticos": "x",
            "filasRecursosCompleto": [1, None],
            "hitos": ["x", {"fechaFinReal": "mala"}],
        },
        TODAY,
    )

    assert page.risks == ()
    assert page.team == ()
    assert page.events == ()


def test_decision_only_for_in_progress_projects_with_problems():
    assert decision_for(critical_project()).action.startswith("Decidir")
    assert decision_for(make_project()) is None
    assert decision_for(critical_project(status_category="En Pausa")) is None
    assert decision_for(make_project(health="En Riesgo")) is not None
