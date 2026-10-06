"""Compara el RAID ejecutivo contra obtenerRaidProyectoEjecutivoAzure().

raid_expected.json es la salida del original (harness de Node con
UrlFetchApp y SpreadsheetApp simulados) para los IDs de raid_data.json.
Cuando la consulta WIQL falla solo se compara ok: false porque el texto
del error es distinto.
"""

import json
from pathlib import Path

import pytest

from apps.azure_devops.exceptions import AzureDevOpsRequestError
from apps.azure_devops.services.project_raid import build_project_raid

HERE = Path(__file__).parent
DATA = json.loads((HERE / "raid_data.json").read_text("utf-8"))
EXPECTED = json.loads((HERE / "raid_expected.json").read_text("utf-8"))
HEADERS, *ROWS = DATA["SHEETS"]["Pendientes_Daily"]
PENDING = [dict(zip(HEADERS, row, strict=True)) for row in ROWS]


def load_items(project):
    if project in DATA["WIQL_FAIL"]:
        raise AzureDevOpsRequestError("Azure DevOps respondio 500.")

    return DATA["ITEMS"].get(project, []), DATA["FIELDS"].get(project, [])


@pytest.mark.parametrize("index", range(len(DATA["OPERATIONS"])))
def test_matches_original(index):
    result = build_project_raid(
        DATA["OPERATIONS"][index],
        DATA["PROJECTS"],
        DATA["ACTIVE"],
        load_items,
        lambda: PENDING,
        DATA["ORG"],
    )
    expected = EXPECTED[index]

    if "Azure WIQL" in str(expected.get("error")):
        assert result["ok"] is False
        assert {**result, "error": ""} == {**expected, "error": ""}
        return

    assert json.loads(json.dumps(result)) == expected


def test_without_azure_configuration():
    result = build_project_raid(
        "GPO.007", DATA["PROJECTS"], "", None, lambda: [], ""
    )

    assert result["ok"] is False
    assert result["error"] == "Conecta Azure DevOps primero."
