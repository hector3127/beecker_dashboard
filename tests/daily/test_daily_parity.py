"""Compara el panel Daily contra DailyPanelService.gs.

expected_results.json es la salida del original con sample_data y una
organizacion de Azure DevOps simulada (tests/daily/fakes.py replica la
misma simulacion).
"""

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

from apps.daily.constants import SHEET_UAT_ADJUSTMENTS
from apps.daily.services import (
    azure_config,
    daily_sheets,
    risk_form,
    work_items,
)
from apps.daily.services.azure_connection import ConnectionStore
from apps.daily.services.daily_azure_client import DailyAzureClient
from apps.daily.services.daily_sheets import DailySheets
from apps.daily.services.project_links import list_project_sprints
from core.exceptions import DashboardError, describe_error
from core.utils.dates import to_datetime, to_utc_iso
from tests.daily import sample_data as sample
from tests.daily.fakes import FakeAzureSession, MemoryCache
from tests.fakes import InMemorySheetRepository

NOW = datetime(2026, 10, 2, 12, 0)
NOW_UTC = datetime(2026, 10, 2, 18, 0, tzinfo=UTC)
FIRST_TIMESTAMP = 1790964000000
EXPECTED = json.loads(
    (Path(__file__).parent / "expected_results.json").read_text("utf-8"),
)


class DailyHarness:
    """Ejecuta las funciones del Daily con dependencias simuladas."""

    def __init__(self):
        self.cache = MemoryCache()
        self.store = ConnectionStore(
            self.cache,
            sample.ORGANIZATION,
            sample.PAT,
            sample.PROJECT,
        )
        self.repository = InMemorySheetRepository(copy.deepcopy(sample.SHEETS))
        self.timestamp = FIRST_TIMESTAMP

    def build_client(self, organization, token):
        return DailyAzureClient(organization, token, session=FakeAzureSession())

    def azure(self):
        connection = self.store.load()

        return work_items.DailyAzure(
            connection=connection,
            build_client=lambda: self.build_client(
                connection.organization,
                connection.personal_access_token,
            ),
            cache=self.cache,
        )

    def sheets(self):
        return DailySheets(
            self.repository,
            self.repository,
            NOW,
            self.timestamp + 1,
        )

    def sheet_action(self, action, failure):
        try:
            result = action(self.sheets())
        except DashboardError as error:
            return {"ok": False, **failure, "error": describe_error(error)}

        if "id" in result:
            self.timestamp += 1

        return result

    def run(self, name, args):
        handlers = {
            "obtenerConfigAzureDevOps": lambda: azure_config.read_azure_config(
                self.store,
            ),
            "probarConexionAzureDevOps": lambda: (
                azure_config.test_azure_connection(
                    self.store,
                    self.build_client,
                )
            ),
            "listarProyectosAzureDevOps": lambda: (
                azure_config.list_azure_projects(
                    args[0],
                    args[1],
                    self.store,
                    self.build_client,
                )
            ),
            "listarProyectosGuardadosAzureDevOps": lambda: (
                azure_config.list_saved_projects(self.store, self.build_client)
            ),
            "obtenerWorkItemsPendientes": lambda: (
                work_items.load_pending_work_items(self.azure(), args[0])
            ),
            "obtenerRiesgosAzureDevOps": lambda: (
                work_items.load_work_items_by_type(
                    self.azure(), "Risk", args[0]
                )
            ),
            "obtenerOportunidadesAzureDevOps": lambda: (
                work_items.load_work_items_by_type(
                    self.azure(),
                    "Opportunity",
                    args[0],
                )
            ),
            "obtenerWorkItemsToBeYCR": lambda: work_items.load_tobe_work_items(
                self.azure(),
                args[0],
                lambda: daily_sheets.load_progress_map(self.sheets()),
            ),
            "obtenerWorkItemsSinSeguimiento": lambda: (
                work_items.load_stale_work_items(self.azure(), args[0], NOW_UTC)
            ),
            "inspeccionarCamposWorkItem": lambda: (
                work_items.inspect_work_item_fields(self.azure(), args[0])
            ),
            "guardarCampoAvanceWorkItem": lambda: self.sheet_action(
                lambda sheets: daily_sheets.save_work_item_progress(
                    sheets,
                    tuple(args),
                    self.store.active_project(),
                ),
                {},
            ),
            "cambiarProyectoActivoAzureDevOps": lambda: (
                azure_config.change_active_project(
                    self.store,
                    self.cache,
                    args[0],
                )
            ),
            "guardarConfigAzureDevOps": lambda: azure_config.save_azure_config(
                self.store,
                self.cache,
                tuple(args),
            ),
            "listarSprintsProyecto": lambda: list_project_sprints(
                args[0],
                self.repository.read_as_objects("Proyectos"),
            ),
            "agregarPendienteDaily": lambda: self.sheet_action(
                lambda sheets: daily_sheets.add_daily_pending(
                    sheets, tuple(args)
                ),
                {},
            ),
            "obtenerPendientesDaily": lambda: self.sheet_action(
                lambda sheets: daily_sheets.list_daily_pending(sheets, args[0]),
                {"pendientes": [], "total": 0},
            ),
            "actualizarEstadoPendienteDaily": lambda: self.sheet_action(
                lambda sheets: daily_sheets.update_daily_pending_state(
                    sheets,
                    args[0],
                    args[1],
                ),
                {},
            ),
            "agregarAjusteUAT": lambda: self.sheet_action(
                lambda sheets: daily_sheets.add_adjustment(
                    sheets,
                    SHEET_UAT_ADJUSTMENTS,
                    tuple(args),
                ),
                {},
            ),
            "obtenerAjustesUAT": lambda: self.sheet_action(
                lambda sheets: daily_sheets.list_adjustments(
                    sheets,
                    SHEET_UAT_ADJUSTMENTS,
                    args[0],
                ),
                {"ajustes": [], "total": 0},
            ),
            "actualizarAjusteUAT": lambda: self.sheet_action(
                lambda sheets: daily_sheets.update_adjustment(
                    sheets,
                    SHEET_UAT_ADJUSTMENTS,
                    args[0],
                    (args[1], args[2]),
                ),
                {},
            ),
            "obtenerFormularioRiesgoAzure": lambda: risk_form.build_risk_form(
                self.azure(),
            ),
            "buscarIteraciones": lambda: risk_form.search_iterations(
                self.azure(),
                args[0],
            ),
            "buscarUsuariosAzureDevOps": lambda: risk_form.search_users(
                self.azure(),
                args[0],
            ),
            "buscarWorkItemsParaRelacionar": lambda: (
                risk_form.search_work_items(self.azure(), args[0])
            ),
            "crearWorkItemRiesgoAzure": lambda: risk_form.create_risk_work_item(
                self.azure(), args[0]
            ),
            "agregarComentarioWorkItem": lambda: (
                risk_form.add_work_item_comment(
                    self.azure(),
                    args[0],
                    args[1],
                    NOW,
                )
            ),
            "eliminarAjusteUAT": lambda: self.sheet_action(
                lambda sheets: daily_sheets.delete_adjustment(
                    sheets,
                    SHEET_UAT_ADJUSTMENTS,
                    args[0],
                ),
                {},
            ),
        }

        return handlers[name]()


def without_global_flag(results):
    """El original en modo personal reporta global False; aqui es True."""
    for result in results:
        result.pop("global", None)

    return results


def sheet_snapshot(sheets):
    snapshot = {}

    for name, rows in sheets.items():
        snapshot[name] = [
            [
                to_utc_iso(cell) if isinstance(cell, datetime) else cell
                for cell in row
            ]
            for row in rows
        ]

    progress = snapshot["WorkItems_Avance"]

    for row in progress[1:]:
        if isinstance(row[5], int | float) and not isinstance(row[5], bool):
            row[5] = to_utc_iso(to_datetime(row[5]))

    return snapshot


def test_daily_operations_match_original():
    FakeAzureSession.posts.clear()
    harness = DailyHarness()
    results = [harness.run(name, args) for name, args in sample.OPERATIONS]

    assert without_global_flag(json.loads(json.dumps(results))) == (
        without_global_flag(copy.deepcopy(EXPECTED["results"]))
    )
    assert sheet_snapshot(harness.repository.sheets) == EXPECTED["sheets"]
    assert FakeAzureSession.posts == EXPECTED["posts"]
