"""Compara Claude y la IA IXS contra DailyPanelService.gs.

ai_expected.json es la salida del original (harness de Node con
UrlFetchApp, DriveApp, CacheService y SpreadsheetApp simulados) para las
operaciones de ai_data.json, incluidos los cuerpos exactos enviados a
Claude. Las respuestas de Claude se entregan en el mismo orden a ambos.
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.daily.services import claude_assist, ixs_ai, ixs_drive
from apps.daily.services.claude_assist import STANDARD_PROMPTS, ClaudeSettings
from apps.daily.services.ixs_drive import (
    DriveContext,
    DriveExportError,
    DriveItem,
)
from apps.daily.services.ixs_store import IxsStore, run_safely
from apps.minutas.exceptions import DriveRequestError
from core.integrations.claude_client import ClaudeClient
from tests.daily.fakes import MemoryCache
from tests.fakes import InMemorySheetRepository

HERE = Path(__file__).parent
DATA = json.loads((HERE / "ai_data.json").read_text("utf-8"))
EXPECTED = json.loads((HERE / "ai_expected.json").read_text("utf-8"))
NOW = datetime.fromisoformat(DATA["NOW"].replace("Z", "+00:00")).astimezone(UTC)
FOLDER_MIME = "application/vnd.google-apps.folder"


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self.text = (
            body
            if isinstance(body, str)
            else json.dumps(body, ensure_ascii=False, separators=(",", ":"))
        )


class FakeClaudeSession:
    """Entrega las respuestas en orden y guarda los cuerpos enviados."""

    def __init__(self, state):
        self.state = state

    def post(self, url, json, headers, timeout):
        assert headers["x-api-key"] == DATA["API_KEY"]
        self.state["posts"].append(json)
        response = DATA["RESPONSES"][len(self.state["posts"]) - 1]
        return FakeResponse(response["status"], response["body"])


class FakeDrive:
    """Carpetas de ai_data.json."""

    def folder_name(self, folder_id):
        folder = DATA["DRIVE"].get(folder_id)

        if folder is None:
            raise DriveRequestError("No item with the given ID could be found.")

        return folder["name"]

    def list_children(self, folder_id):
        folder = DATA["DRIVE"].get(folder_id)

        if folder is None:
            raise DriveRequestError("No item with the given ID could be found.")

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
            DriveItem(child, "", FOLDER_MIME, "", NOW)
            for child in folder["folders"]
        ]

        return files + folders

    def _file(self, file_id):
        return next(
            item
            for folder in DATA["DRIVE"].values()
            for item in folder["files"]
            if item["id"] == file_id
        )

    def export_document(self, file_id):
        item = self._file(file_id)

        if item.get("broken"):
            raise DriveExportError(403)

        return item["content"]

    def download_text(self, file_id):
        return self._file(file_id).get("content", "")


def cell_value(value):
    if isinstance(value, dict) and "serial" in value:
        return value["serial"]

    return value


@pytest.fixture(scope="module")
def run():
    state = {"posts": []}
    repository = InMemorySheetRepository(
        {
            name: [[cell_value(value) for value in row] for row in rows]
            for name, rows in DATA["SHEETS"].items()
        },
    )
    counter = iter(range(1, 1000))
    store = IxsStore(
        reader=repository,
        writer=repository,
        now=NOW,
        new_uid=lambda: f"uuid-{next(counter)}",
    )
    settings = ClaudeSettings(
        api_key=DATA["API_KEY"],
        model="claude-haiku-4-5-20251001",
        store=MemoryCache(),
        build_client=lambda: ClaudeClient(
            DATA["API_KEY"],
            session=FakeClaudeSession(state),
        ),
        now=NOW,
    )
    drive = DriveContext(store=store, drive=FakeDrive())
    functions = {
        "obtenerConfigClaude": lambda: claude_assist.read_config(settings),
        "guardarApiKeyClaude": claude_assist.save_api_key,
        "guardarPromptPersonalizadoClaude": lambda text: (
            claude_assist.save_custom_prompt(settings, text)
        ),
        "generarSugerenciaRiesgoConClaude": lambda text: (
            claude_assist.suggest_risk(settings, text)
        ),
        "ixsRaidObtenerPrompt": lambda kind: claude_assist.read_raid_prompt(
            settings,
            kind,
        ),
        "ixsRaidGuardarPrompt": lambda kind, text: (
            claude_assist.save_raid_prompt(
                settings,
                kind,
                text,
            )
        ),
        "ixsRaidSugerirClaude": lambda kind, text: claude_assist.suggest_raid(
            settings,
            kind,
            text,
        ),
        "ixsIAAnalisisLeer": lambda project: ixs_ai.read_analysis(
            store, project
        ),
        "ixsIAAnalizar": lambda *args: ixs_ai.analyze_project(
            settings, store, args
        ),
        "ixsIAPreguntar": lambda *args: ixs_ai.ask_question(settings, args),
        "ixsIAMemoriaLeer": lambda project: ixs_ai.read_memory(store, project),
        "ixsIAMemoriaActualizar": lambda *args: ixs_ai.save_memory(
            store, *args
        ),
        "ixsIAMinutasLeer": lambda project: ixs_ai.read_minutes(store, project),
        "ixsIAMinutaGuardar": lambda *args: ixs_ai.save_minute(store, args),
        "ixsIADriveConfigLeer": lambda project: ixs_drive.read_config(
            store,
            project,
        ),
        "ixsIADriveConfigGuardar": lambda *args: ixs_drive.save_folder(
            DriveContext(store=store, drive=FakeDrive()),
            *args,
        ),
        "ixsIADriveConfigQuitar": lambda *args: ixs_drive.remove_folder(
            store,
            *args,
        ),
        "ixsIADriveListar": lambda project: ixs_drive.list_files(
            drive, project
        ),
        "ixsIADriveLeerDocumento": lambda *args: ixs_drive.read_document(
            drive,
            *args,
        ),
        "ixsIADriveGenerarMinuta": lambda *args: ixs_drive.generate_minute(
            settings,
            drive,
            args,
        ),
    }

    def resolve(value):
        if value == "__STANDARD_OPPORTUNITY__":
            return STANDARD_PROMPTS["Opportunity"]

        return value

    results = [
        json.loads(
            json.dumps(
                run_safely(
                    lambda name=name, args=args: functions[name](
                        *[resolve(value) for value in args],
                    ),
                ),
            ),
        )
        for name, args in DATA["OPERATIONS"]
    ]

    return results, state["posts"]


@pytest.mark.parametrize("index", range(len(DATA["OPERATIONS"])))
def test_operation_matches_original(run, index):
    assert run[0][index] == EXPECTED["results"][index], DATA["OPERATIONS"][
        index
    ]


def test_claude_payloads_match_original(run):
    assert len(run[1]) == len(EXPECTED["posts"])

    for actual, expected in zip(run[1], EXPECTED["posts"], strict=True):
        assert actual == expected


def test_api_key_is_never_saved_from_the_panel():
    result = claude_assist.save_api_key("sk-ant-nueva")

    assert result == {"ok": False, "error": claude_assist.ENV_ONLY_MESSAGE}
