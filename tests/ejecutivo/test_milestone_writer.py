"""Escritura de hitos adicionales y riesgos manuales.

write_expected.json es el resultado de ejecutar las mismas operaciones
con el ProyectoEjecutivoService.gs original.
"""

import copy
import json
from datetime import datetime
from pathlib import Path

import pytest

from apps.ejecutivo.services.additional_milestones import list_milestone_types
from apps.ejecutivo.services.manual_risks import add_manual_risk
from apps.ejecutivo.services.milestone_writer import (
    MilestoneSheet,
    build_entry,
    delete_milestone,
    edit_milestone,
    format_milestone_date,
    save_milestones,
)
from core.exceptions import DashboardError, describe_error
from tests.ejecutivo import project_sample_data as sample
from tests.fakes import InMemorySheetRepository

NOW = datetime(2026, 10, 2, 12, 0)
NOW_MS = 1790964000000
EXPECTED = json.loads(
    (Path(__file__).parent / "write_expected.json").read_text("utf-8"),
)


def run_operation(repository, function_name, args):
    def milestone_action(action):
        try:
            hitos = action(MilestoneSheet(repository, repository))
        except DashboardError as error:
            return {"ok": False, "error": describe_error(error), "hitos": []}
        return {"ok": True, "hitos": hitos}

    if function_name == "obtenerTiposHitosExistentes":
        return list_milestone_types(repository.read_values("Proyectos"))

    if function_name == "guardarHitosAdicionalesLote":
        return milestone_action(
            lambda sheet: save_milestones(sheet, args[0], args[1]),
        )

    if function_name == "editarHitoAdicional":
        return milestone_action(
            lambda sheet: edit_milestone(
                sheet,
                (args[0], args[1], args[2]),
                args[3],
                args[4],
            ),
        )

    if function_name == "eliminarHitoAdicional":
        return milestone_action(
            lambda sheet: delete_milestone(sheet, args[0], args[1], args[2]),
        )

    try:
        add_manual_risk((repository, repository), tuple(args), (NOW, NOW_MS))
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}

    return {"ok": True}


def without_slash_notes(value):
    """Quita el "/" que el original ponia en observaciones vacias."""
    if isinstance(value, dict):
        return {
            key: ""
            if key == "observacion" and item == "/"
            else without_slash_notes(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [without_slash_notes(item) for item in value]

    if isinstance(value, str):
        return value.replace("::/", "::")

    return value


def test_write_operations_match_original():
    repository = InMemorySheetRepository(copy.deepcopy(sample.WRITE_SHEETS))
    results = [
        run_operation(repository, function_name, args)
        for function_name, args in sample.WRITE_OPERATIONS
    ]
    sheets = {
        name: [
            ["DATE" if isinstance(cell, datetime) else cell for cell in row]
            for row in rows
        ]
        for name, rows in repository.sheets.items()
    }

    assert json.loads(json.dumps(results)) == without_slash_notes(
        EXPECTED["results"],
    )
    assert sheets == without_slash_notes(EXPECTED["sheets"])


@pytest.mark.parametrize(
    ("date_value", "expected"),
    [
        # Diferencia intencional: el original guardaba 14/11/2026.
        ("2026-11-15", "15/11/2026"),
        ("2026-11-15T10:00:00", "15/11/2026"),
        ("15/11/2026", "15/11/2026"),
        ("sin fecha", "sin fecha"),
        (None, ""),
    ],
)
def test_format_milestone_date(date_value, expected):
    assert format_milestone_date(date_value) == expected


def test_build_entry_cleans_separators():
    # Diferencia intencional: el original intercalaba "/" entre letras.
    assert build_entry("2026-11-15", " Nota | con::dos ") == (
        "15/11/2026::Nota / con:dos"
    )


def test_edit_rejects_non_integer_index():
    repository = InMemorySheetRepository(copy.deepcopy(sample.WRITE_SHEETS))
    sheet = MilestoneSheet(repository, repository)

    with pytest.raises(DashboardError, match="fuera de rango"):
        edit_milestone(sheet, ("AMK.008", "Go Live", "0"), "", "")

    with pytest.raises(DashboardError, match="fuera de rango"):
        delete_milestone(sheet, "AMK.008", "Go Live", 0.5)


def test_milestone_sheet_requires_id_column():
    repository = InMemorySheetRepository({"Proyectos": [["Otro"]]})

    with pytest.raises(DashboardError, match="ID_Proyecto"):
        MilestoneSheet(repository, repository).find_project_row("A")
