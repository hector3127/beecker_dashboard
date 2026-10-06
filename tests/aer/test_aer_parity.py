"""Compara el dashboard AER / T&M contra AERTYMProyectoService.gs.

aer_expected.json es la salida del original (harness de Node con
SpreadsheetApp simulado y las horas de Clockify de aer_data.json) para
todas las operaciones de aer_data.json, incluido el estado final de cada
hoja. Ambos lados convierten el texto como Sheets: "2026-10-05" en fecha,
"TRUE" en booleano y "12" en numero.
"""

import json
import re
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from apps.aer.services import dashboard, people_client, plan, risks_actions
from apps.aer.services.manual_store import AerStore
from apps.clockify.services.date_ranges import ProjectDateRange
from apps.daily.services.ixs_store import run_safely
from core.time_entries.models import TimeEntry
from core.utils.dates import (
    SHEETS_EPOCH,
    to_datetime,
    to_local_naive,
    to_utc_iso,
)
from tests.fakes import InMemorySheetRepository

HERE = Path(__file__).parent
DATA = json.loads((HERE / "aer_data.json").read_text("utf-8"))
EXPECTED = json.loads((HERE / "aer_expected.json").read_text("utf-8"))
NOW = datetime.fromisoformat(DATA["NOW"].replace("Z", "+00:00")).astimezone(UTC)
DATE_TEXT = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})(?: (\d{2}):(\d{2})(?::(\d{2}))?)?$",
)
NUMBER_TEXT = re.compile(r"^-?\d+(\.\d+)?$")


def serial(moment):
    return (moment - SHEETS_EPOCH).total_seconds() / 86400


def sheets_value(value):
    """Lo que guarda Sheets al recibir el valor (USER_ENTERED)."""
    if isinstance(value, datetime):
        return serial(to_local_naive(value) if value.tzinfo else value)

    if not isinstance(value, str):
        return value

    match = DATE_TEXT.match(value)

    if match:
        parts = [int(part or 0) for part in match.groups()]
        return serial(datetime(*parts))

    if value in ("TRUE", "FALSE"):
        return value == "TRUE"

    if NUMBER_TEXT.match(value):
        number = float(value)
        return int(number) if number.is_integer() else number

    return value


class SheetsLikeRepository(InMemorySheetRepository):
    """Repositorio en memoria que convierte lo escrito como Sheets."""

    def append_row(self, sheet_name, values):
        super().append_row(
            sheet_name, [sheets_value(value) for value in values]
        )

    def write_row(self, sheet_name, row_number, values):
        super().write_row(
            sheet_name,
            row_number,
            [sheets_value(value) for value in values],
        )

    def write_cell(self, sheet_name, row_number, column_number, value):
        super().write_cell(
            sheet_name, row_number, column_number, sheets_value(value)
        )


def initial_value(value):
    if isinstance(value, dict) and "d" in value:
        return sheets_value(value["d"])

    return value


def hours_loader(project):
    result = DATA["CLOCKIFY"].get(project, {"ok": True, "registros": []})

    if not result["ok"]:
        return dashboard.ClockifyHours([], "", None, result["error"])

    entries = []

    for item in result["registros"]:
        start = datetime.fromisoformat(item["fechaInicioCompleta"]).replace(
            tzinfo=None,
        )
        entries.append(
            TimeEntry(
                entry_id=item["id"],
                project_id=project,
                resource_name=item["recurso"],
                entry_date=datetime(start.year, start.month, start.day),
                duration_hours=item["duracion"],
                is_billable=item["billable"],
                costing_rate=item["costingRate"],
                description=item["descripcion"],
                task_name=item["task"],
                started_at=start,
            ),
        )

    date_range = result["rango"]

    return dashboard.ClockifyHours(
        entries,
        result["proyectoClockify"],
        ProjectDateRange(
            date.fromisoformat(date_range["fechaInicio"]),
            date.fromisoformat(date_range["fechaFin"]),
            date_range["fuente"],
        ),
        None,
    )


@pytest.fixture(scope="module")
def run():
    repository = SheetsLikeRepository(
        {
            name: [[initial_value(value) for value in row] for row in rows]
            for name, rows in DATA["SHEETS"].items()
        },
    )
    counter = iter(range(1, 1000))
    store = AerStore(
        reader=repository,
        writer=repository,
        now=NOW,
        new_uid=lambda: f"uuid-{next(counter)}",
    )
    functions = {
        "getDashboardAERTYMProyecto": lambda project: dashboard.build_dashboard(
            store,
            project,
            hours_loader,
        ),
        "getRegistrosClockifyAERRango": lambda project, start, end: (
            dashboard.entries_in_range(project, (start, end), hours_loader)
        ),
        "guardarPlaneacionAER": lambda payload: plan.save_plan(store, payload),
        "guardarLotePlaneacionAER": lambda *args: plan.save_plan_batch(
            store, *args
        ),
        "actualizarEsfuerzoPlaneacionAER": lambda *args: plan.update_effort(
            store,
            *args,
        ),
        "actualizarEstadoCierrePlaneacionAER": lambda *args: (
            plan.update_close_state(store, args)
        ),
        "marcarCierrePlaneacionAER": lambda *args: plan.mark_closed(
            store, *args
        ),
        "eliminarPlaneacionAER": lambda uid: plan.delete_plan(store, uid),
        "eliminarLotePlaneacionAER": lambda *args: plan.delete_plan_batch(
            store,
            *args,
        ),
        "guardarRiesgoAER": lambda payload: risks_actions.save_risk(
            store, payload
        ),
        "getRiesgosAERProyecto": lambda project: risks_actions.get_risks(
            store,
            project,
        ),
        "limpiarDuplicadosRiesgosAER": lambda project: (
            risks_actions.clean_risks(
                store,
                project,
            )
        ),
        "eliminarRiesgoAER": lambda uid: risks_actions.delete_risk(store, uid),
        "guardarAccionAER": lambda payload: risks_actions.save_action(
            store,
            payload,
        ),
        "actualizarCampoAccionAER": lambda *args: (
            risks_actions.update_action_field(
                store,
                args,
            )
        ),
        "getAccionesAERProyecto": lambda project: risks_actions.get_actions(
            store,
            project,
        ),
        "limpiarDuplicadosAccionesAER": lambda project: (
            risks_actions.clean_actions(store, project)
        ),
        "eliminarAccionAER": lambda uid: risks_actions.delete_action(
            store, uid
        ),
        "guardarVacacionAER": lambda payload: people_client.save_vacation(
            store,
            payload,
        ),
        "eliminarVacacionAER": lambda *args: people_client.delete_vacation(
            store,
            *args,
        ),
        "guardarEvaluacionAER": lambda payload: people_client.save_evaluation(
            store,
            payload,
        ),
        "eliminarEvaluacionAER": lambda *args: people_client.delete_evaluation(
            store,
            *args,
        ),
        "guardarContactoAER": lambda payload: people_client.save_contact(
            store,
            payload,
        ),
        "eliminarContactoAER": lambda *args: people_client.delete_contact(
            store,
            *args,
        ),
        "guardarClienteInfoAER": lambda payload: people_client.save_client_info(
            store,
            payload,
        ),
        "guardarGobiernoClienteAER": lambda *args: (
            people_client.save_governance(
                store,
                *args,
            )
        ),
        "guardarDocumentoClienteAER": lambda payload: (
            people_client.save_document(
                store,
                payload,
            )
        ),
        "eliminarDocumentoClienteAER": lambda *args: (
            people_client.delete_document(store, *args)
        ),
    }
    results = [
        json.loads(
            json.dumps(
                run_safely(
                    lambda name=name, args=args: functions[name](
                        *json.loads(json.dumps(args)),
                    ),
                ),
            ),
        )
        for name, args in DATA["OPERATIONS"]
    ]

    return results, repository.sheets


@pytest.mark.parametrize("index", range(len(DATA["OPERATIONS"])))
def test_operation_matches_original(run, index):
    assert run[0][index] == EXPECTED["results"][index], DATA["OPERATIONS"][
        index
    ]


DATE_SHEET_COLUMNS = {
    "Fecha_Inicio",
    "Fecha_Fin_Estimada",
    "Inicio_Plan",
    "Fin_Plan",
    "Inicio_Real",
    "Fin_Real",
    "Fecha_Limite",
    "Fecha_Real",
    "Inicio",
    "Fin",
    "Fecha_Registro",
    "Fecha_Evaluacion",
    "Proxima_Evaluacion",
    "Proxima_Reunion",
    "Actualizado",
}


def test_sheets_match_original(run):
    for name, rows in run[1].items():
        expected_rows = EXPECTED["sheets"][name]
        headers = (
            [str(cell) for cell in expected_rows[0]] if expected_rows else []
        )

        actual = [
            [
                {"date": to_utc_iso(to_datetime(value))}
                if column < len(headers)
                and headers[column] in DATE_SHEET_COLUMNS
                and isinstance(value, int | float)
                and not isinstance(value, bool)
                else value
                for column, value in enumerate(row)
            ]
            for row in rows
        ]

        assert actual == expected_rows, name
