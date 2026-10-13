"""Listas de proyectos en ejecucion y en tiempo por Delivery Manager."""

from apps.portal.services.project_groups import (
    build_project_groups,
    select_on_time,
)
from tests.portal.builders import make_project


def portfolio():
    return [
        make_project(project_id="1", name="Zeta", client="B"),
        make_project(project_id="2", name="Alfa", client="A"),
        make_project(
            project_id="3",
            name="Critico",
            health="Crítica",
            burn_hours=125.0,
        ),
        make_project(project_id="4", name="Riesgo", health="En Riesgo"),
        make_project(project_id="5", name="Pausa", status_category="En Pausa"),
        make_project(
            project_id="6",
            name="Solo",
            delivery_manager="Ana",
            health="Crítica",
        ),
        make_project(project_id="7", name="Cerrado", status_category="Cerrado"),
    ]


def test_select_on_time_keeps_only_in_progress_on_time():
    assert [item.project_id for item in select_on_time(portfolio())] == [
        "1",
        "2",
    ]


def test_groups_in_progress_order_and_summary():
    groups = build_project_groups(portfolio(), only_on_time=False)

    assert [group.name for group in groups] == ["Laura Vega", "Ana"]
    laura, ana = groups
    assert laura.slug == "laura-vega"
    assert [row.name for row in laura.rows] == [
        "Critico",
        "Riesgo",
        "Alfa",
        "Zeta",
    ]
    assert laura.rows[0].detail == "Presupuesto usado: 125%"
    assert laura.summary == (
        "4 proyectos · 2 en tiempo · 1 en riesgo · 1 crítico"
    )
    assert ana.summary == "1 proyecto · 0 en tiempo · 1 crítico"


def test_groups_on_time_only():
    groups = build_project_groups(portfolio(), only_on_time=True)

    assert len(groups) == 1
    assert groups[0].summary == "2 proyectos en tiempo"
    assert [row.client for row in groups[0].rows] == ["A", "B"]


def test_groups_without_projects():
    assert build_project_groups([], only_on_time=False) == ()
