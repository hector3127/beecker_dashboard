"""Pantalla EVA 2 a partir del resumen IXB/RaaS."""

from apps.portal.services.eva2 import (
    build_eva2_project,
    build_eva2_view,
    service_label,
    status_code,
)


def wi(total, closed):
    return {"total": total, "cerrados": closed, "pendientes": total - closed}


def make_row(**overrides):
    row = {
        "deliveryManager": "Laura Vega",
        "idProyecto": "AMK.008_S4",
        "servicio": "RAAS",
        "nombre": "Alertas",
        "status": "Deployment",
        "fechaInicio": "2026-08-28T00:00:00",
        "fechaFin": "2026-10-13T00:00:00",
        "desviacionDias": 1,
        "budget": 141,
        "burn": 167.59,
        "etc": -26.59,
        "avance": 118.8,
        "wi": {
            "discovery": wi(41, 41),
            "development": wi(56, 50),
            "deployment": wi(39, 2),
            "general": wi(154, 102),
        },
        "etapas": {
            "discovery": {"cerrada": True},
            "development": {"cerrada": True},
            "deployment": {"cerrada": False},
        },
        "riesgos": ["Riesgo 1", "Riesgo 2"],
    }
    row.update(overrides)

    return row


def test_service_label_and_status_code():
    assert service_label("RAAS") == "RaaS"
    assert service_label("IXB Y RAAS") == "IXB y RaaS"
    assert service_label("OTRO") == "OTRO"
    assert status_code("Suspendido") == "sus"
    assert status_code("Deployment") == "dep"
    assert status_code("Development") == "dev"
    assert status_code("Discovery") == "dis"
    assert status_code("Cerrado") == ""


def test_project_values_and_alerts():
    project = build_eva2_project(make_row())

    assert project.service == "RaaS"
    assert project.start == "28/08/26"
    assert project.end == "13/10/26"
    assert project.progress_bad is True
    assert project.risks == 2
    discovery, development, deployment, general = project.stages
    assert (discovery.total, discovery.pending, discovery.alert) == (
        41,
        0,
        False,
    )
    assert development.pending == 6
    assert development.alert is True
    assert deployment.pending == 37
    assert deployment.alert is False
    assert general.alert is False


def test_project_without_azure_data_or_dates():
    project = build_eva2_project(
        make_row(
            wi={},
            etapas={},
            fechaFin=None,
            desviacionDias=None,
            avance=2.7,
            deliveryManager="",
        ),
    )

    assert project.manager == "Sin asignar"
    assert project.end == ""
    assert project.deviation_days is None
    assert project.progress_bad is False
    assert all(stage.total == 0 for stage in project.stages)


def test_view_pivots_totals_and_suspended_note():
    view = build_eva2_view(
        [
            make_row(),
            make_row(
                idProyecto="AMK.004_CR",
                servicio="IXB",
                nombre="Data Retrieve",
                status="Suspendido",
            ),
            make_row(
                deliveryManager="Mario",
                idProyecto="AMK.015",
                servicio="IXB",
                status="Discovery",
            ),
            make_row(
                deliveryManager="Mario",
                idProyecto="AMK.016",
                servicio="SAAS",
                status="Development",
            ),
        ],
    )

    assert view.total_projects == 4
    assert view.services == ("IXB", "RaaS", "SaaS")
    assert [row.name for row in view.service_rows] == ["Laura Vega", "Mario"]
    assert view.service_rows[0].counts == (1, 1, 0)
    assert view.service_rows[1].counts == (1, 0, 1)
    assert view.service_totals.counts == (2, 1, 1)
    assert view.service_totals.total == 4
    assert view.status_rows[0].counts == (1, 0, 0, 1)
    assert view.status_totals.counts == (1, 1, 1, 1)
    assert view.suspended_count == 1
    assert view.suspended_note == "AMK.004_CR · Data Retrieve"


def test_empty_view_keeps_preferred_service_columns():
    view = build_eva2_view([])

    assert view.total_projects == 0
    assert view.services == ("IXB", "RaaS")
    assert view.service_rows == ()
    assert view.suspended_note == ""
