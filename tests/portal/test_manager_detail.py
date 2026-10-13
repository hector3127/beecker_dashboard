"""Detalle de Delivery Manager y resumen de suspendidos."""

from apps.portal.services.manager_detail import (
    build_manager_detail,
    build_project_row,
    build_status_detail,
    classify_status,
    find_manager,
    summarize_suspended,
)
from apps.portal.services.slugs import build_slug
from tests.portal.builders import make_project


def laura_projects():
    return [
        make_project(project_id="1", name="Zeta"),
        make_project(project_id="2", name="Alfa", risk_level="Alto"),
        make_project(
            project_id="3",
            name="Critico",
            health="Crítica",
            burn_hours=125.0,
        ),
        make_project(
            project_id="4",
            name="Riesgo",
            health="En Riesgo",
            delay_days=9,
        ),
        make_project(project_id="5", name="Pausa", status_category="En Pausa"),
        make_project(project_id="6", name="Cerrado", status_category="Cerrado"),
        make_project(
            project_id="7",
            name="Planeado",
            status_category="Planificación",
        ),
    ]


def test_slug_removes_accents_and_symbols():
    assert build_slug("Patricio Ochoa") == "patricio-ochoa"
    assert build_slug("José Pérez-Ñandú") == "jose-perez-nandu"
    assert build_slug("Sin Delivery Manager") == "sin-delivery-manager"
    assert build_slug("???") == "sin-nombre"


def test_find_manager_by_slug():
    projects = laura_projects() + [
        make_project(project_id="9", delivery_manager="Ana María"),
    ]

    name, mine = find_manager(projects, "laura-vega")
    assert name == "Laura Vega"
    assert len(mine) == 7
    assert find_manager(projects, "ana-maria")[0] == "Ana María"
    assert find_manager(projects, "nadie") is None


def test_classify_status():
    assert classify_status(make_project()) == "g"
    assert classify_status(make_project(health="En Riesgo")) == "a"
    assert classify_status(make_project(health="Crítica")) == "r"
    assert classify_status(make_project(status_category="En Pausa")) == "x"


def test_status_detail_explains_the_problem():
    over = make_project(health="Crítica", burn_hours=125.0)
    late = make_project(health="En Riesgo", delay_days=12)
    plain = make_project(health="En Riesgo")

    assert build_status_detail(over, "r") == "Presupuesto usado: 125%"
    assert build_status_detail(late, "a") == "12 días atrasado"
    assert build_status_detail(plain, "a") == ""
    assert build_status_detail(over, "g") == ""
    assert build_status_detail(over, "x") == ""


def test_project_row_values():
    row = build_project_row(
        make_project(
            health="Crítica",
            burn_hours=125.0,
            etc_hours=179.6,
            progress_percent=88,
            risk_level="Alto",
        ),
    )

    assert row.status_label == "Crítico"
    assert row.row_class == "rs"
    assert row.etc_hours == 180
    assert row.progress_percent == 88
    assert row.risk_label == "Alto"
    assert build_project_row(make_project()).risk_label == "—"
    assert build_project_row(make_project()).row_class == ""


def test_detail_totals_and_ordering():
    detail = build_manager_detail("Laura Vega", laura_projects())

    assert detail.total == 5
    assert detail.in_progress == 4
    assert detail.paused == 1
    assert (detail.health.on_time, detail.health.at_risk) == (2, 1)
    assert detail.health.critical == 1
    assert [row.name for row in detail.rows] == [
        "Critico",
        "Riesgo",
        "Alfa",
        "Zeta",
        "Pausa",
    ]
    assert detail.rows[-1].status_code == "x"
    assert detail.initials == "LV"


def test_detail_risk_note_and_shares():
    detail = build_manager_detail("Laura Vega", laura_projects())

    assert detail.high_risk == 1
    assert detail.high_risk_note == "En Alfa"
    assert [item.count for item in detail.shares] == [2, 1, 1]
    assert [item.percent for item in detail.shares] == [50, 25, 25]
    assert detail.shares[0].label == "En tiempo"


def test_risk_note_without_risks_and_with_many():
    quiet = build_manager_detail("Ana", [make_project()])
    noisy = build_manager_detail(
        "Ana",
        [
            make_project(
                project_id=str(index), name=f"P{index}", risk_level="Alto"
            )
            for index in range(4)
        ],
    )

    assert quiet.high_risk_note == "Sin riesgos altos abiertos"
    assert noisy.high_risk_note == "En P0 y P1 y 2 más"


def test_detail_without_projects():
    detail = build_manager_detail("Ana", [])

    assert detail.total == 0
    assert detail.rows == ()
    assert [item.percent for item in detail.shares] == [0, 0, 0]


def test_suspended_summary():
    projects = [
        make_project(project_id="1", delivery_manager="Laura"),
        make_project(
            project_id="2",
            name="Beta",
            delivery_manager="Mario",
            status_category="En Pausa",
            etc_hours=100.4,
        ),
        make_project(
            project_id="3",
            name="Alfa",
            delivery_manager="Mario",
            status_category="En Pausa",
            etc_hours=50.0,
        ),
    ]
    summary = summarize_suspended(projects)

    assert summary.count == 2
    assert summary.by_manager == (("Mario", 2), ("Laura", 0))
    assert summary.etc_hours == 150
    assert [row.name for row in summary.rows] == ["Alfa", "Beta"]
    assert summary.rows[0].etc_hours == 50


def test_suspended_summary_empty():
    summary = summarize_suspended([])

    assert summary.count == 0
    assert summary.by_manager == ()
    assert summary.rows == ()
