"""Compara la IA por proyecto AER contra AERIAService.gs.

aer_ai_expected.json es la salida del original (harness de Node con
SpreadsheetApp, DriveApp, UrlFetchApp, CacheService y LockService
simulados) para las operaciones de aer_ai_data.json: respuestas, cuerpos
exactos enviados a Claude y estado final de las hojas (valores visibles).
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.aer.services.ai_common import AerAiContext, display
from apps.aer.services.ai_functions import FUNCTIONS
from apps.daily.services.ixs_drive import DriveItem
from apps.daily.services.ixs_store import run_safely
from apps.minutas.exceptions import DriveRequestError
from core.integrations.claude_client import ClaudeClient
from tests.aer.test_aer_parity import SheetsLikeRepository
from tests.daily.fakes import MemoryCache

HERE = Path(__file__).parent
DATA = json.loads((HERE / "aer_ai_data.json").read_text("utf-8"))
EXPECTED = json.loads((HERE / "aer_ai_expected.json").read_text("utf-8"))
NOW = datetime.fromisoformat(DATA["NOW"].replace("Z", "+00:00")).astimezone(UTC)
FOLDER_MIME = "application/vnd.google-apps.folder"
FILES = {
    item["id"]: item
    for folder in DATA["DRIVE"].values()
    for item in folder["files"]
}
KINDS = {
    "AER_Acciones_BeeckerCliente": (
        "",
        "",
        "",
        "",
        "date",
        "date",
        "",
        "",
        "datetime",
    ),
    "AER_IA_Minutas": ("", "", "date", "", "", "datetime"),
    "AER_IA_Minutas_Config": ("", "", "", "datetime", "", ""),
    "AER_IA_Analisis": ("", "datetime", ""),
    "AER_IA_Resumenes": ("", "", "", "datetime"),
}


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self.text = (
            body
            if isinstance(body, str)
            else json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        )


class FakeClaudeSession:
    def __init__(self, state):
        self.state = state

    def post(self, url, json, headers, timeout):
        assert headers["x-api-key"] == DATA["API_KEY"]
        self.state["posts"].append(json)
        response = DATA["RESPONSES"][len(self.state["posts"]) - 1]
        return FakeResponse(response["status"], response["body"])


class FakeDrive:
    def folder_name(self, folder_id):
        folder = DATA["DRIVE"].get(folder_id)

        if folder is None:
            raise DriveRequestError("No item with the given ID could be found.")

        return folder["name"]

    def list_children(self, folder_id):
        folder = DATA["DRIVE"][folder_id]
        files = [
            DriveItem(
                item["id"],
                item["name"],
                item["mime"],
                f"https://docs.google.com/d/{item['id']}",
                datetime.fromisoformat(item["modified"].replace("Z", "+00:00")),
            )
            for item in folder["files"]
        ]
        folders = [
            DriveItem(child, DATA["DRIVE"][child]["name"], FOLDER_MIME, "", NOW)
            for child in folder["folders"]
        ]
        return files + folders

    def export_document(self, file_id):
        return FILES[file_id]["content"]

    def download_text(self, file_id):
        return FILES[file_id]["content"]


@pytest.fixture(scope="module")
def run():
    repository = SheetsLikeRepository(
        {
            name: [list(row) for row in rows]
            for name, rows in DATA["SHEETS"].items()
        },
    )
    state = {"posts": [], "uid": 0}

    def new_uid():
        state["uid"] += 1
        return f"uuid-{state['uid']}"

    ctx = AerAiContext(
        reader=repository,
        writer=repository,
        now=NOW,
        api_key=DATA["API_KEY"],
        model="claude-haiku-4-5-20251001",
        build_client=lambda: ClaudeClient(
            DATA["API_KEY"], session=FakeClaudeSession(state)
        ),
        cache=MemoryCache(),
        new_uid=new_uid,
        drive=FakeDrive(),
    )
    results = []

    for name, args in DATA["OPERATIONS"]:
        count, action, _ = FUNCTIONS[name]
        padded = (tuple(args) + (None,) * count)[:count]
        results.append(
            json.loads(
                json.dumps(
                    run_safely(
                        lambda action=action, padded=padded: action(
                            ctx, padded
                        ),
                    ),
                ),
            ),
        )

    return results, state["posts"], repository


@pytest.mark.parametrize("index", range(len(DATA["OPERATIONS"])))
def test_operation_matches_original(run, index):
    assert run[0][index] == EXPECTED["results"][index]


def test_claude_requests_match_original(run):
    assert run[1] == EXPECTED["posts"]


def test_final_sheets_match_original(run):
    repository = run[2]

    for name, rows in EXPECTED["sheets"].items():
        kinds = KINDS.get(name, ())
        visible = [
            [
                display(cell, kinds[i] if i < len(kinds) and number > 0 else "")
                for i, cell in enumerate(row)
            ]
            for number, row in enumerate(repository.sheets[name])
        ]
        assert visible == rows, name
