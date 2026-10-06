"""Compara las funciones de hojas de la vista IXS contra DailyPanelService.gs.

ixs_sheets_expected.json es la salida del original (harness de Node con
SpreadsheetApp simulado) para las operaciones de ixs_sheets_data.json:
cliente y acciones, recursos, planeacion y beeCom, incluido el estado
final de cada hoja.
"""

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.daily.services.ixs_functions import SHEET_FUNCTIONS, call_action
from apps.daily.services.ixs_store import IxsStore, run_safely
from core.utils.dates import to_datetime, to_utc_iso
from tests.fakes import InMemorySheetRepository

HERE = Path(__file__).parent
DATA = json.loads((HERE / "ixs_sheets_data.json").read_text("utf-8"))
EXPECTED = json.loads((HERE / "ixs_sheets_expected.json").read_text("utf-8"))
NOW = datetime.fromisoformat(DATA["NOW"].replace("Z", "+00:00")).astimezone(UTC)

# El JSON guardado esta corrupto: V8 y Python describen distinto el error
# de JSON.parse; solo se compara que la respuesta sea un error.
CORRUPT_JSON_OPERATION = 27


@pytest.fixture(scope="module")
def run():
    repository = InMemorySheetRepository(copy.deepcopy(DATA["SHEETS"]))
    counter = iter(range(1, 1000))
    store = IxsStore(
        reader=repository,
        writer=repository,
        now=NOW,
        new_uid=lambda: f"uuid-{next(counter)}",
    )
    results = [
        json.loads(
            json.dumps(
                run_safely(
                    lambda name=name, args=args: call_action(
                        SHEET_FUNCTIONS[name],
                        store,
                        tuple(args),
                    ),
                ),
            ),
        )
        for name, args in DATA["OPERATIONS"]
    ]

    return results, repository.sheets


def normalize_cell(sheet_name, column, value):
    if isinstance(value, datetime):
        return {"date": to_utc_iso(value)}

    if (
        sheet_name == "Comunicados"
        and column == 1
        and isinstance(value, int | float)
        and not isinstance(value, bool)
    ):
        return {"date": to_utc_iso(to_datetime(value))}

    return value


@pytest.mark.parametrize("index", range(len(DATA["OPERATIONS"])))
def test_operation_matches_original(run, index):
    actual = run[0][index]
    expected = EXPECTED["results"][index]

    if index == CORRUPT_JSON_OPERATION:
        assert actual["ok"] is False
        assert expected["ok"] is False
        return

    assert actual == expected, DATA["OPERATIONS"][index]


def test_sheets_match_original(run):
    sheets = {
        name: [
            [
                normalize_cell(name, column, value)
                for column, value in enumerate(row)
            ]
            for row in rows
        ]
        for name, rows in run[1].items()
    }

    assert sheets == EXPECTED["sheets"]
