"""Compara las vistas de proyecto Clockify contra ClockifyService.gs.

project_views_expected.json es la salida del original (harness de Node
con SpreadsheetApp, UrlFetchApp y CacheService simulados) para las
operaciones de project_views_data.json. Los errores de rango solo se
comparan por ok: false porque el texto del mensaje es distinto.
"""

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from apps.clockify.services import project_views
from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.date_ranges import ProjectDateRangeResolver
from apps.clockify.services.time_entry_loader import ClockifyTimeEntryLoader
from core.utils.dates import SHEETS_EPOCH
from tests.clockify.fakes import DictCache
from tests.fakes import InMemorySheetRepository

HERE = Path(__file__).parent
DATA = json.loads((HERE / "project_views_data.json").read_text("utf-8"))
EXPECTED = json.loads(
    (HERE / "project_views_expected.json").read_text("utf-8"),
)
TODAY = date(2026, 10, 3)
MESSAGE_ONLY_DIFFERS = {10, 14}


def cell(value):
    """{"d": "YYYY-MM-DD"} es una fecha de Sheets (numero de serie)."""
    if isinstance(value, dict):
        moment = datetime.fromisoformat(value["d"])
        return (moment - SHEETS_EPOCH).days

    return value


class FakeClient:
    """Proyectos, reporte y tasks de project_views_data.json."""

    def list_projects(self, workspace_id):
        return [
            ClockifyProject(item["id"], item["name"])
            for item in DATA["PROJECTS"]
        ]

    def fetch_detailed_report_counted(
        self, workspace_id, project_id, start, end, timezone_name
    ):
        return DATA["REPORT"].get(project_id, []), 1

    def list_project_tasks(self, workspace_id, project_id):
        return [dict(task) for task in DATA["TASKS"].get(project_id, [])]


def build():
    repository = InMemorySheetRepository(
        {
            name: [[cell(value) for value in row] for row in rows]
            for name, rows in DATA["SHEETS"].items()
        },
    )
    loader = ClockifyTimeEntryLoader(
        reader=repository,
        client_factory=FakeClient,
        workspace_id="ws",
        today=TODAY,
        cache_store=DictCache(),
        cache_prefix="test",
    )
    sources = project_views.ProjectSources(
        project_rows=repository.read_as_objects("Proyectos"),
        history_values=repository.read_values("Historico_Proyectos"),
        today=TODAY,
    )

    return repository, loader, sources


def run(name, project):
    repository, loader, sources = build()
    resolver = ProjectDateRangeResolver(repository, TODAY)

    if name == "obtenerRangoClockifyProyecto":
        return project_views.range_dates(resolver.resolve(project.strip()))

    if name == "obtenerEtapasHistoricoAIProyecto":
        return project_views.stages_response(
            sources,
            project.strip(),
            resolver.resolve_from_history(project.strip()),
        )

    if name == "getRegistrosClockifyProyecto":
        return project_views.project_entries(
            sources, project, loader.load_project_hours
        )

    return project_views.tasks_summary(
        sources,
        project,
        loader.load_project_hours,
        loader.load_project_tasks,
    )


@pytest.mark.parametrize("index", range(len(DATA["OPERATIONS"])))
def test_matches_original(index):
    name, args = DATA["OPERATIONS"][index]
    result = json.loads(json.dumps(run(name, *args)))
    expected = EXPECTED[index]

    if index in MESSAGE_ONLY_DIFFERS:
        assert result["ok"] is False
        assert {**result, "error": ""} == {**expected, "error": ""}
        return

    assert result == expected
