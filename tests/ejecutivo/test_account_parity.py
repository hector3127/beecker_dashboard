"""Compara la vista de cuenta Beecker contra DailyPanelService.gs.

account_expected.json es la salida del original (harness de Node con
SpreadsheetApp, CacheService y Clockify simulados) para las operaciones
de account_data.json, incluidas las escrituras en el backlog y en la
columna BL de MPB.
"""

import json
from datetime import date, datetime
from pathlib import Path

import pytest

from apps.ejecutivo.services import account_actions, account_view
from core.exceptions import DashboardError, TimeEntrySourceError, describe_error
from core.time_entries.models import TimeEntry
from tests.daily.fakes import MemoryCache
from tests.fakes import InMemorySheetRepository

HERE = Path(__file__).parent
DATA = json.loads((HERE / "account_data.json").read_text("utf-8"))
EXPECTED = json.loads((HERE / "account_expected.json").read_text("utf-8"))
TODAY = date.fromisoformat(DATA["TODAY"])


class RecordingRepository(InMemorySheetRepository):
    """Repositorio en memoria que anota las escrituras."""

    def __init__(self, sheets):
        super().__init__(sheets)
        self.writes = []

    def append_row(self, sheet_name, values):
        self.writes.append([sheet_name, "append", list(values)])
        super().append_row(sheet_name, values)

    def write_cell(self, sheet_name, row_number, column_number, value):
        self.writes.append([sheet_name, row_number, column_number, value])
        super().write_cell(sheet_name, row_number, column_number, value)


def cell_value(value):
    if isinstance(value, dict) and "serial" in value:
        return float(value["serial"])

    return value


def load_entries(project_id, date_range):
    result = DATA["CLOCKIFY"].get(project_id, {"ok": True, "registros": []})

    if not result["ok"]:
        raise TimeEntrySourceError(result["error"])

    return [
        TimeEntry(
            "e",
            project_id,
            "Ana",
            datetime.fromisoformat(item["fecha"]),
            item["duracion"],
            True,
            0.0,
        )
        for item in result["registros"]
    ]


@pytest.fixture(scope="module")
def run():
    repository = RecordingRepository(
        {
            name: [[cell_value(value) for value in row] for row in rows]
            for name, rows in DATA["SHEETS"].items()
        },
    )
    cache = MemoryCache()
    sheets = (repository, repository)

    def call(name, args):
        args = list(args) + [None] * 4

        if name == "obtenerVistaCuentaBeecker":
            return account_view.build_account_view(
                repository, args[0], cache, TODAY
            )

        if name == "obtenerOportunidadesCuentaBeecker":
            data = account_view.load_opportunities(repository, args[0], cache)
            return {"ok": True, **data}

        if name == "beeCuentaGuardarOportunidad":
            return account_actions.save_opportunity(
                sheets, args[0], args[1], cache
            )

        return account_actions.load_account_consumption(
            sheets,
            tuple(args[:4]),
            load_entries,
            TODAY,
            cache,
        )

    results = []

    for name, args in DATA["OPERATIONS"]:
        try:
            result = call(name, args)
        except DashboardError as error:
            result = {"ok": False, "error": describe_error(error)}

        results.append(json.loads(json.dumps(result)))

    return results, repository.writes


@pytest.mark.parametrize("index", range(len(DATA["OPERATIONS"])))
def test_operation_matches_original(run, index):
    assert run[0][index] == EXPECTED["results"][index], DATA["OPERATIONS"][
        index
    ]


def test_writes_match_original(run):
    assert run[1] == EXPECTED["writes"]
