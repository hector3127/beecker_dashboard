"""Pruebas del panel de conexion de Clockify (sin llamadas reales)."""

import json
from datetime import date
from types import SimpleNamespace

from apps.clockify.exceptions import ClockifyRequestError
from apps.clockify.services import connection_panel as panel
from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.date_ranges import ProjectDateRange
from tests.fakes import InMemorySheetRepository

PROJECTS = [
    ClockifyProject("p1", "RAS.001 - Cliente", "c1"),
    ClockifyProject("p2", "AER.AWN.001"),
    ClockifyProject("p3", "ras.001 viejo"),
]


def reply(status, body):
    return SimpleNamespace(status_code=status, json=lambda: body)


OWNER = reply(200, {"name": "Ana", "email": "a@x"})


class FakeLoader:
    def __init__(self, user=OWNER):
        self.user = user
        self.fresh_calls = []

    def list_clockify_projects(self):
        return PROJECTS

    def find_clockify_project(self, internal_id):
        return PROJECTS[0] if internal_id.startswith("RAS") else None

    def resolve_range(self, internal_id):
        if internal_id.startswith("AER"):
            return ProjectDateRange(None, None, "MPB")
        return ProjectDateRange(
            date(2026, 1, 6), date(2026, 3, 15), "Historico_Proyectos"
        )

    def create_client(self):
        return SimpleNamespace(get=lambda path: self.user)

    def load_fresh_project_hours(self, internal_id):
        self.fresh_calls.append(internal_id)
        if internal_id == "RAS.002":
            raise ClockifyRequestError("HTTP 403")
        entries = [
            SimpleNamespace(resource_name="Ana"),
            SimpleNamespace(resource_name="Ana"),
            SimpleNamespace(resource_name="Beto"),
        ]
        return SimpleNamespace(
            entries=entries, project_name="RAS.001 - Cliente", project_id="p1"
        ), 2


def context(loader=None):
    return panel.PanelContext(loader, "clave-secreta-1234", "ws1")


def test_list_projects_and_setup_error():
    result = panel.list_projects(context(FakeLoader()))

    assert result["proyectos"][0] == {
        "id": "p1",
        "nombre": "RAS.001 - Cliente",
        "clienteId": "c1",
    }
    assert panel.list_projects(context())["error"] == panel.SETUP_ERROR


def test_save_link_validates_and_upserts():
    repo = InMemorySheetRepository({})
    ctx = context(FakeLoader())

    assert panel.save_link(ctx, repo, repo, "RAS 001", "p1")["error"] == (
        "Escribe un ID interno válido."
    )
    assert (
        "Selecciona un proyecto"
        in panel.save_link(ctx, repo, repo, "RAS.001", "nope")["error"]
    )

    first = panel.save_link(ctx, repo, repo, "RAS.001_S2", "p1")
    again = panel.save_link(ctx, repo, repo, "ras.001_s2", "p3")

    assert first == {
        "ok": True,
        "idInterno": "RAS.001_S2",
        "nombreClockify": "RAS.001 - Cliente",
    }
    assert again["nombreClockify"] == "ras.001 viejo"
    assert repo.sheets["Clockify_Vinculos"] == [
        ["ID_Proyecto", "Clockify_Project_ID"],
        ["RAS.001_S2", "p3"],
    ]


def test_connection_check():
    result = panel.connection_check(context(FakeLoader()), " RAS.001_CR1 ")

    assert result == {
        "ok": True,
        "conexionGlobal": True,
        "workspace": "ws1",
        "sufijo": "1234",
        "totalProyectos": 3,
        "proyectoEncontrado": "RAS.001 - Cliente",
        "similares": ["RAS.001 - Cliente", "ras.001 viejo"],
    }
    assert panel.connection_check(context(), "X")["error"] == (
        "Falta conectar Clockify y elegir el workspace."
    )
    assert panel.connection_check(context(FakeLoader()), "")["ok"] is False


def test_hours_check_success_and_errors():
    loader = FakeLoader()
    result = panel.hours_check(context(loader), "RAS.001")

    assert result["ok"] is True
    assert result["registros"] == 3
    assert result["usuariosConsultados"] == 2
    assert result["rango"] == {
        "fechaInicio": "2026-01-06",
        "fechaFin": "2026-03-15",
        "fuente": "Historico_Proyectos",
    }
    assert result["aviso"] == (
        "Proyecto Clockify: RAS.001 - Cliente [p1]. Reporte detallado: 2 "
        "consulta(s). Conexión global (.env), clave ****1234, titular: Ana "
        "(a@x), workspace ID: ws1."
    )
    assert "1234" in result["aviso"] and "clave-secreta" not in json.dumps(
        result
    )

    failed = panel.hours_check(context(loader), "RAS.002")
    assert failed["ok"] is False and failed["registros"] is None
    assert failed["error"].endswith(panel.ACCESS_HINT.strip())

    mpb = panel.hours_check(context(loader), "AER.X")
    assert mpb["error"] == (
        'No se encontró INICIO en MPB para "AER.X" (SERVICE AER/TYM).'
    )


def test_identity_without_permission():
    loader = FakeLoader(user=reply(401, {}))

    assert panel.identity_text(context(loader)) == (
        "Conexión global (.env), clave ****1234: Clockify no permitió "
        "identificar al titular (HTTP 401)."
    )
