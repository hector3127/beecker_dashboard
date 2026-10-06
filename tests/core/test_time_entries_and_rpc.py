from datetime import datetime

import pytest

from core.rpc.registry import (
    RPC_FUNCTIONS,
    DuplicateRpcFunctionError,
    get_rpc_function,
    register_rpc,
)
from core.time_entries.sheet_provider import SheetTimeEntryProvider
from tests.fakes import InMemorySheetRepository


def test_sheet_provider_reads_registros_tiempo():
    repository = InMemorySheetRepository(
        {
            "Registros_Tiempo": [
                [
                    "ID_Registro",
                    "Proyecto",
                    "Recurso",
                    "Fecha",
                    "Duracion_Hrs",
                    "Costing_Rate",
                    "Billable",
                ],
                ["T-1", "P-1", "Ana", 46296, 2.5, 20, "YES"],
                ["T-2", "P-1", "Ana", "2026-10-01", "1", "", "No"],
            ],
        },
    )

    batch = SheetTimeEntryProvider(repository).load_time_entries()

    assert [entry.is_billable for entry in batch.entries] == [True, False]
    assert batch.entries[0].duration_hours == 2.5
    assert batch.entries[0].entry_date == datetime(2026, 10, 1)
    assert batch.entries[1].costing_rate == 0


def test_register_rpc_rejects_duplicates():
    @register_rpc("pruebaDuplicada")
    def first_function():
        return 1

    try:
        assert get_rpc_function("pruebaDuplicada") is first_function

        with pytest.raises(DuplicateRpcFunctionError):
            register_rpc("pruebaDuplicada")(first_function)
    finally:
        RPC_FUNCTIONS.pop("pruebaDuplicada")


def test_unknown_function_is_not_registered():
    assert get_rpc_function("funcionQueNoExiste") is None
