"""Compara Minutas IA contra el Apps Script original.

expected_results.json es la salida del MinutasService.gs y del
MinutasViewService.gs originales con sample_data.
"""

import copy
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from apps.minutas.exceptions import DriveRequestError
from apps.minutas.services.drive_folder import DriveDocument, build_document
from apps.minutas.services.minute_scanner import ScanContext, scan_new_minutes
from apps.minutas.services.minutes_view import (
    build_minutes_view,
    list_projects_with_minutes,
)
from apps.minutas.services.rule_parser import extract_by_rules
from core.utils.dates import to_datetime, to_utc_iso
from tests.fakes import InMemorySheetRepository
from tests.minutas import sample_data as sample

NOW = datetime(2026, 10, 2, 12, 0)
SHEETS_EPOCH = datetime(1899, 12, 30)
EXPECTED = json.loads(
    (Path(__file__).parent / "expected_results.json").read_text("utf-8"),
)


class FakeDocumentSource:
    """Carpeta de Drive con los documentos de sample_data."""

    def list_documents(self, folder_id):
        documents = [
            build_document(
                {
                    "id": document_id,
                    "name": name,
                    "createdTime": created,
                    "webViewLink": "https://docs.google.com/document/d/"
                    f"{document_id}/edit?usp=drivesdk",
                },
            )
            for document_id, name, created, _ in sample.DOCUMENTS[folder_id]
        ]

        for subfolder_id in sample.SUBFOLDERS[folder_id]:
            documents.extend(self.list_documents(subfolder_id))

        return documents

    def export_text(self, document_id):
        texts = {
            document[0]: document[3]
            for documents in sample.DOCUMENTS.values()
            for document in documents
        }

        if texts[document_id] is None:
            raise DriveRequestError("Export fallo con status 403")

        return texts[document_id]


def to_serial(value):
    """Convierte una fecha a numero de serie, como la regresa Sheets."""
    if isinstance(value, datetime):
        return (value - SHEETS_EPOCH).total_seconds() / 86400

    return value


def parsed_to_json(extracted):
    data = asdict(extracted)

    return {
        "proyecto": data["project_id"],
        "resumen": data["summary"],
        "asistentes": data["attendees"],
        "pendientes": [
            {
                "responsable": item["responsible"],
                "descripcion": item["description"],
            }
            for item in data["pending_items"]
        ],
        "riesgos": data["risks"],
        "acuerdos": data["agreements"],
    }


def without_detection_date(views):
    for view in views:
        for minute in view["minutas"]:
            for risk in minute["riesgos"]:
                risk.pop("Fecha_Deteccion", None)

    return views


def test_rule_parser_matches_original():
    projects = InMemorySheetRepository(
        {"Proyectos": sample.PROJECTS},
    ).read_as_objects("Proyectos")
    texts = [sample.GEMINI_NOTES, sample.NAME_ONLY_NOTES, sample.SHORT_NOTES]

    assert [
        parsed_to_json(extract_by_rules(text, projects)) for text in texts
    ] == EXPECTED["parsed"]


def test_scan_and_view_match_original():
    repository = InMemorySheetRepository(copy.deepcopy(sample.SHEETS))
    context = ScanContext(repository, repository, FakeDocumentSource(), NOW)

    assert scan_new_minutes(context, sample.FOLDER_ID) == 4

    sheets = {
        name: [
            [
                to_utc_iso(cell) if isinstance(cell, datetime) else cell
                for cell in row
            ]
            for row in rows
        ]
        for name, rows in repository.sheets.items()
    }
    # En el original la fecha de reunion ya leida es un Date.
    for row in sheets["Minutas"][1:]:
        if isinstance(row[3], int | float):
            row[3] = to_utc_iso(to_datetime(row[3]))

    expected_sheets = copy.deepcopy(EXPECTED["sheets"])
    # La duracion del escaneo depende del reloj; se compara sin ella.
    for rows in (sheets, expected_sheets):
        for row in rows["Log_Automatizaciones"][1:]:
            row[4] = ""

    assert sheets == expected_sheets

    for rows in repository.sheets.values():
        for row in rows:
            row[:] = [to_serial(cell) for cell in row]

    views = [
        build_minutes_view(
            repository.read_as_objects("Minutas"),
            repository.read_as_objects("Pendientes_Minutas"),
            repository.read_as_objects("Riesgos"),
            filters,
        )
        for filters in sample.VIEW_FILTERS
    ]

    assert without_detection_date(
        json.loads(json.dumps(views)),
    ) == without_detection_date(EXPECTED["views"])
    assert (
        list_projects_with_minutes(
            repository.read_as_objects("Minutas"),
            repository.read_as_objects("Proyectos"),
        )
        == EXPECTED["proyectos"]
    )


def test_scan_without_folder_logs_error():
    repository = InMemorySheetRepository(copy.deepcopy(sample.SHEETS))
    context = ScanContext(repository, repository, FakeDocumentSource(), NOW)

    assert scan_new_minutes(context, "") == 0
    assert repository.sheets["Log_Automatizaciones"][-1][1:] == [
        "escanearMinutasNuevas",
        "ERROR",
        "Falta configurar CARPETA_MINUTAS_ID",
        "",
    ]


def test_drive_document_dates_are_local():
    document = build_document(
        {"id": "a", "createdTime": "2026-10-03T00:30:00.000Z"},
    )

    assert document == DriveDocument("a", "", datetime(2026, 10, 2, 18, 30), "")
