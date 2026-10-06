from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from googleapiclient.errors import HttpError

from core.exceptions import (
    SheetAuthenticationError,
    SheetColumnNotFoundError,
    SheetNotFoundError,
    SpreadsheetNotFoundError,
)
from core.sheets.repository import (
    GoogleSheetRepository,
    column_letter,
    quote_sheet_name,
)


def build_service(values_by_sheet):
    service = MagicMock()
    spreadsheets = service.spreadsheets.return_value
    spreadsheets.get.return_value.execute.return_value = {
        "sheets": [
            {"properties": {"title": name, "sheetId": index}}
            for index, name in enumerate(values_by_sheet)
        ],
    }

    def batch_get(**kwargs):
        request = MagicMock()
        request.execute.return_value = {
            "valueRanges": [
                {"values": values_by_sheet[name.strip("'")]}
                for name in kwargs["ranges"]
            ],
        }
        return request

    spreadsheets.values.return_value.batchGet.side_effect = batch_get
    return service


def test_read_as_objects_pads_short_rows_and_skips_empty_rows():
    service = build_service(
        {
            "Proyectos": [
                ["ID_Proyecto", "Nombre", "Cliente"],
                ["P-1", "Alpha"],
                ["", "", ""],
                ["P-2", "Beta", "ACME"],
            ],
        },
    )
    repository = GoogleSheetRepository(service, "sheet-id")

    rows = repository.read_as_objects("Proyectos")

    assert rows == [
        {"ID_Proyecto": "P-1", "Nombre": "Alpha", "Cliente": ""},
        {"ID_Proyecto": "P-2", "Nombre": "Beta", "Cliente": "ACME"},
    ]


def test_reads_are_cached_per_instance():
    service = build_service({"Riesgos": [["ID"], ["R-1"]]})
    repository = GoogleSheetRepository(service, "sheet-id")

    repository.read_values("Riesgos")
    repository.read_values("Riesgos")

    batch_get = service.spreadsheets.return_value.values.return_value.batchGet
    assert batch_get.call_count == 1


def test_missing_sheet_raises_not_found():
    repository = GoogleSheetRepository(build_service({}), "sheet-id")

    with pytest.raises(SheetNotFoundError):
        repository.read_values("No existe")


def test_upsert_updates_existing_row():
    service = build_service(
        {"Proyectos": [["ID_Proyecto", "Estado"], ["P-1", "Discovery"]]},
    )
    repository = GoogleSheetRepository(service, "sheet-id")

    repository.upsert_row(
        "Proyectos",
        "ID_Proyecto",
        {"ID_Proyecto": "P-1", "Estado": "Development"},
    )

    update = service.spreadsheets.return_value.values.return_value.update
    kwargs = update.call_args.kwargs
    assert kwargs["range"] == "'Proyectos'!A2"
    assert kwargs["body"] == {"values": [["P-1", "Development"]]}


def test_upsert_appends_when_id_does_not_exist():
    service = build_service({"Proyectos": [["ID_Proyecto", "Estado"]]})
    repository = GoogleSheetRepository(service, "sheet-id")

    repository.upsert_row(
        "Proyectos",
        "ID_Proyecto",
        {"ID_Proyecto": "P-9", "Estado": None},
    )

    append = service.spreadsheets.return_value.values.return_value.append
    assert append.call_args.kwargs["body"] == {"values": [["P-9", ""]]}


def test_upsert_requires_id_column():
    service = build_service({"Proyectos": [["Nombre"]]})
    repository = GoogleSheetRepository(service, "sheet-id")

    with pytest.raises(SheetColumnNotFoundError):
        repository.upsert_row("Proyectos", "ID_Proyecto", {})


def test_append_row_serializes_dates():
    service = build_service({"Log": [["Timestamp"]]})
    repository = GoogleSheetRepository(service, "sheet-id")

    repository.append_row("Log", [datetime(2026, 10, 2, 9, 30), None, 3])

    append = service.spreadsheets.return_value.values.return_value.append
    assert append.call_args.kwargs["body"] == {
        "values": [["2026-10-02 09:30:00", "", 3]],
    }


@pytest.mark.parametrize(
    ("status", "expected_error"),
    [
        (403, SheetAuthenticationError),
        (404, SpreadsheetNotFoundError),
    ],
)
def test_http_errors_are_translated(status, expected_error):
    service = MagicMock()
    service.spreadsheets.return_value.get.return_value.execute.side_effect = (
        HttpError(SimpleNamespace(status=status), b"")
    )
    repository = GoogleSheetRepository(service, "sheet-id")

    with pytest.raises(expected_error):
        repository.sheet_exists("Proyectos")


def test_quote_sheet_name_escapes_single_quotes():
    assert quote_sheet_name("Banda salarial") == "'Banda salarial'"
    assert quote_sheet_name("O'Hara") == "'O''Hara'"


@pytest.mark.parametrize(
    ("column_number", "expected"),
    [(1, "A"), (12, "L"), (26, "Z"), (27, "AA"), (703, "AAA")],
)
def test_column_letter(column_number, expected):
    assert column_letter(column_number) == expected


def test_write_cell_updates_single_cell():
    service = build_service({"Proyectos": [["ID_Proyecto"]]})
    repository = GoogleSheetRepository(service, "sheet-id")

    repository.write_cell("Proyectos", 3, 13, "15/11/2026::Nota")

    update = service.spreadsheets.return_value.values.return_value.update
    kwargs = update.call_args.kwargs
    assert kwargs["range"] == "'Proyectos'!M3"
    assert kwargs["body"] == {"values": [["15/11/2026::Nota"]]}
    assert kwargs["valueInputOption"] == "USER_ENTERED"


def test_delete_row_uses_sheet_id():
    service = build_service({"Hoja": [["ID"]], "Ajustes_UAT": [["ID"]]})
    repository = GoogleSheetRepository(service, "sheet-id")

    repository.delete_row("Ajustes_UAT", 4)

    batch_update = service.spreadsheets.return_value.batchUpdate
    request = batch_update.call_args.kwargs["body"]["requests"][0]
    assert request["deleteDimension"]["range"] == {
        "sheetId": 1,
        "dimension": "ROWS",
        "startIndex": 3,
        "endIndex": 4,
    }

    with pytest.raises(SheetNotFoundError):
        repository.delete_row("No existe", 2)


def test_write_row_updates_from_column_a():
    service = build_service({"IXS_Planeacion": [["UID"]]})
    repository = GoogleSheetRepository(service, "sheet-id")

    repository.write_row("IXS_Planeacion", 4, ["u1", "GPO.007", None])

    update = service.spreadsheets.return_value.values.return_value.update
    kwargs = update.call_args.kwargs
    assert kwargs["range"] == "'IXS_Planeacion'!A4"
    assert kwargs["body"] == {"values": [["u1", "GPO.007", ""]]}


def test_delete_sheet_uses_sheet_id():
    service = build_service({"Hoja": [["ID"]], "Vieja": [["ID"]]})
    repository = GoogleSheetRepository(service, "sheet-id")

    repository.delete_sheet("Vieja")

    batch_update = service.spreadsheets.return_value.batchUpdate
    request = batch_update.call_args.kwargs["body"]["requests"][0]
    assert request == {"deleteSheet": {"sheetId": 1}}
    assert not repository.sheet_exists("Vieja")

    with pytest.raises(SheetNotFoundError):
        repository.delete_sheet("No existe")


def test_read_previews_uses_one_batch_get():
    service = build_service({"Hoja": [["ID"]], "Otra": [["A"]]})
    repository = GoogleSheetRepository(service, "sheet-id")
    batch_get = service.spreadsheets.return_value.values.return_value.batchGet
    batch_get.side_effect = None
    batch_get.return_value.execute.return_value = {
        "valueRanges": [{"values": [["ID"]]}, {}],
    }

    previews = repository.read_previews(["Hoja", "No existe", "Otra"], 12, 80)

    assert batch_get.call_args.kwargs["ranges"] == [
        "'Hoja'!A1:CB12",
        "'Otra'!A1:CB12",
    ]
    assert previews == {"Hoja": [["ID"]], "Otra": []}
    assert repository.list_sheet_names() == ["Hoja", "Otra"]


def test_delete_row_range_uses_one_request():
    service = build_service({"Hoja": [["ID"]], "Validaciones": [["ID"]]})
    repository = GoogleSheetRepository(service, "sheet-id")

    repository.delete_row_range("Validaciones", 2, 5)

    batch_update = service.spreadsheets.return_value.batchUpdate
    request = batch_update.call_args.kwargs["body"]["requests"][0]
    assert request["deleteDimension"]["range"] == {
        "sheetId": 1,
        "dimension": "ROWS",
        "startIndex": 1,
        "endIndex": 6,
    }
