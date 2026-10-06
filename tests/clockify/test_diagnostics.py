"""Pruebas de los diagnosticos de Clockify y del cliente de tasks."""

import json
from datetime import date
from types import SimpleNamespace

import pytest

from apps.clockify.exceptions import ClockifyRequestError
from apps.clockify.services import diagnostics
from apps.clockify.services.clockify_client import (
    ClockifyClient,
    ClockifyProject,
)
from apps.clockify.services.date_ranges import ProjectDateRange
from apps.clockify.services.report_mapper import read_task_id
from tests.clockify.fakes import FakeResponse, FakeSession

RANGE = ProjectDateRange(date(2026, 1, 6), date(2026, 3, 15), "Historico")
PROJECT = ClockifyProject("p1", "RAS.001 - Cliente")


def reply(status, body):
    text = body if isinstance(body, str) else json.dumps(body)
    return SimpleNamespace(
        status_code=status, text=text, json=lambda: json.loads(text)
    )


class FakeHttp:
    """GET por ruta; guarda las llamadas."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        for prefix, response in self.routes.items():
            if path.startswith(prefix):
                return (
                    response(path, params) if callable(response) else response
                )
        raise AssertionError(path)


class FakeLoader:
    workspace_id = "ws"

    def __init__(self, project=PROJECT):
        self.project = project

    def find_clockify_project(self, internal_id):
        return self.project

    def list_clockify_projects(self):
        return [ClockifyProject("p1", "Uno"), ClockifyProject("p2", "Dos")]

    def resolve_range(self, internal_id):
        return RANGE


def context(routes, resources=(), project=PROJECT):
    return diagnostics.DiagnosticContext(
        loader=FakeLoader(project),
        resource_rows=lambda: list(resources),
        range_payload=lambda project_id, date_range: {
            "fechaInicio": date_range.start_date.isoformat(),
        },
        sleep=lambda seconds: None,
        client=FakeHttp(routes),
    )


USERS = [
    {"id": "u1", "name": "Ana López", "email": "ana@x"},
    {"id": "u2", "name": "Beto", "email": "beto@x"},
]


def test_quick_diagnostic_uses_project_members():
    ctx = context(
        {
            "/workspaces/ws/projects/p1": reply(
                200, {"memberships": [{"userId": "u2"}, {"userId": "u9"}]}
            ),
            "/workspaces/ws/users": reply(200, USERS),
            "/workspaces/ws/member-profile/u9": reply(200, {"email": "z@x"}),
            "/workspaces/ws/user/u2/time-entries": reply(200, [{"id": 1}] * 4),
        },
    )

    result = diagnostics.quick_diagnostic(ctx, "RAS.001")

    assert result["fuenteUsuarios"] == "miembros del proyecto"
    assert result["usuarioPrueba"] == {
        "id": "u2",
        "nombre": "Beto",
        "email": "beto@x",
    }
    assert result["totalUsuariosEnWorkspace"] == 2
    assert result["cantidadEntradasDeEsteUsuario"] == 4
    assert len(result["primerasEntradasCrudas"]) == 3
    path, params = ctx.client.calls[-1]
    assert params["start"] == "2026-01-06T00:00:00.000Z"
    assert params["page-size"] == 5


def test_quick_diagnostic_falls_back_and_reports_errors():
    ctx = context(
        {
            "/workspaces/ws/projects/p1": reply(404, "no existe"),
            "/workspaces/ws/users": reply(200, USERS),
            "/workspaces/ws/user/u1/time-entries": reply(403, "privado"),
        },
    )

    result = diagnostics.quick_diagnostic(ctx, "RAS.001")

    assert result["ok"] is False
    assert (
        result["error"]
        == 'Clockify respondió 403 probando con "Ana López": privado'
    )

    missing = diagnostics.quick_diagnostic(context({}, project=None), "X.1")
    assert missing["error"] == (
        'No se encontró match para "X.1". Proyectos disponibles en '
        "Clockify: Uno, Dos"
    )


def test_full_diagnostic_filters_by_resources():
    entries = {
        "u1": reply(
            200,
            [
                {"timeInterval": {"duration": "PT1H30M"}},
                {"timeInterval": {"duration": 1800}},
            ],
        ),
        "u2": reply(403, "x"),
    }
    ctx = context(
        {
            "/workspaces/ws/projects/p1": reply(
                200, {"memberships": [{"userId": "u1"}, {"userId": "u2"}]}
            ),
            "/workspaces/ws/users": reply(200, USERS),
            "/workspaces/ws/user/": lambda path, params: entries[
                path.split("/")[4]
            ],
        },
        resources=[
            {"Proyecto": "RAS.001_S2", "Nombre del recurso": "Ana Lopez"},
            {"Proyecto": "OTRO", "Nombre del recurso": "Beto"},
        ],
    )

    result = diagnostics.full_diagnostic(ctx, "RAS.001")

    assert result["totalMiembros"] == 1
    assert result["totalMiembrosEnClockify"] == 2
    assert result["modoEmergenciaSinFiltroRecursos"] is False
    assert result["detallePorUsuario"] == [
        {"usuario": "Ana López", "entradas": 2, "horas": 2.0},
    ]
    assert result["totalHoras"] == 2.0


def test_full_diagnostic_without_resources_uses_everyone():
    ctx = context(
        {
            "/workspaces/ws/projects/p1": reply(
                200, {"memberships": [{"userId": "u2"}]}
            ),
            "/workspaces/ws/users": reply(200, USERS),
            "/workspaces/ws/user/u2/time-entries": reply(500, "x"),
        },
    )

    result = diagnostics.full_diagnostic(ctx, "RAS.001")

    assert result["modoEmergenciaSinFiltroRecursos"] is True
    assert result["detallePorUsuario"][0]["error"] == "Código 500"


def test_client_get_retries_once_on_429():
    session = FakeSession(
        [FakeResponse(429, []), FakeResponse(200, [])],
    )
    waits = []
    client = ClockifyClient("k", session=session, sleep=waits.append)

    assert client.get("/workspaces").status_code == 200
    assert waits == [1.5]


def test_list_project_tasks_pages_and_errors():
    first = [
        {"id": f"t{i}", "name": f"T{i}", "status": "ACTIVE"} for i in range(200)
    ]
    session = FakeSession(
        [FakeResponse(200, first), FakeResponse(200, [{"id": "x"}])],
    )
    tasks = ClockifyClient("k", session=session).list_project_tasks("ws", "p1")

    assert len(tasks) == 201
    assert tasks[-1] == {"id": "x", "name": "", "status": ""}

    failing = FakeResponse(403, [])
    failing.text = "denegado"
    with pytest.raises(ClockifyRequestError, match="tasks respondió 403"):
        ClockifyClient("k", session=FakeSession([failing])).list_project_tasks(
            "ws", "p1"
        )


def test_read_task_id():
    assert read_task_id({"taskId": "t1"}) == "t1"
    assert read_task_id({"task": {"id": "t2"}}) == "t2"
    assert read_task_id({}) == ""
