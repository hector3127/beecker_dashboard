"""Compara el guardado de GSE contra el Apps Script original.

expected_writes.json guarda, por escenario, lo que regresan y como dejan
las hojas gseBaseGuardar_() y gseObtenerIDsClockify() del .gs original
(sample_data.SAVE_SCENARIOS e IDS_SCENARIOS).
"""

import copy
import json
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest

from apps.gse.exceptions import GseError
from apps.gse.services import base_writer, clockify_ids
from apps.gse.services.base_store import BaseStore, Connection, HourRecord
from apps.gse.services.base_writer import BaseWriter
from apps.gse.services.clockify_ids import IdsContext, get_clockify_ids
from apps.gse.services.clockify_month import MonthReportLoader
from core.exceptions import DashboardError, describe_error
from tests.fakes import InMemorySheetRepository
from tests.gse import sample_data

NOW = datetime(2026, 10, 2, 18, 0, tzinfo=UTC)
EXPECTED = json.loads(
    (Path(__file__).parent / "expected_writes.json").read_text("utf-8"),
)
CONNECTION = Connection(sample_data.WORKSPACE, sample_data.CONNECTION)


def build_records():
    return [
        HourRecord(
            record_id=item["id"],
            user_id=item["userId"],
            resource=item["recurso"],
            project=item["proyecto"],
            task=item["task"],
            tags=item["tags"],
            billable=item["billable"],
            day=item["fecha"],
            hours=item["horas"],
        )
        for item in sample_data.NEW_RECORDS
    ]


def trimmed_sheets(sheets):
    """Hojas sin filas ni columnas finales vacias, como las ve el .gs."""
    result = {}

    for name, rows in sheets.items():
        kept = [list(row) for row in rows]

        while kept and all(cell in ("", None) for cell in kept[-1]):
            kept.pop()

        width = max(
            (
                index + 1
                for row in kept
                for index, cell in enumerate(row)
                if cell not in ("", None)
            ),
            default=0,
        )
        result[name] = [(row + [""] * width)[:width] for row in kept]

    return result


def normalize(sheets):
    """Los numeros se comparan como numeros y los vacios como ''."""
    return {
        name: [["" if cell is None else cell for cell in row] for row in rows]
        for name, rows in sheets.items()
    }


@pytest.mark.parametrize(
    ("scenario", "expected"),
    list(zip(sample_data.SAVE_SCENARIOS, EXPECTED["saves"], strict=True)),
)
def test_save_month_matches_original(scenario, expected):
    dataset, month, user_ids = scenario
    sheets = InMemorySheetRepository(
        copy.deepcopy(sample_data.build_write_datasets()[dataset]),
    )

    try:
        BaseWriter(sheets, CONNECTION, NOW).save_month(
            month,
            build_records(),
            user_ids,
        )
        result = {"ok": True}
    except DashboardError as error:
        result = {"ok": False, "error": describe_error(error)}

    assert result == expected["result"]
    assert normalize(trimmed_sheets(sheets.sheets)) == normalize(
        expected["sheets"],
    )


class FakeResponse:
    def __init__(self, status, body):
        self.status_code = status
        self._body = body

    def json(self):
        return self._body


class FakeClient:
    """Cliente que contesta una pagina por llamada (la ultima se repite)."""

    def __init__(self, script):
        self.script = script
        self.calls = []

    def get_users_page(self, workspace_id, page_number, page_size):
        self.calls.append((workspace_id, page_number, page_size))
        item = self.script[min(len(self.calls) - 1, len(self.script) - 1)]

        return FakeResponse(item["status"], item["body"])


class MemoryCache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, timeout):
        self.data[key] = value

    def delete(self, key):
        self.data.pop(key, None)


def build_report_loader(sheets):
    store = BaseStore(sheets, CONNECTION, NOW)

    return MonthReportLoader(
        ("KEY", sample_data.WORKSPACE, "America/Mexico_City"),
        (store, CONNECTION, MemoryCache()),
        None,
    )


@pytest.mark.parametrize(
    ("scenario", "expected"),
    list(zip(sample_data.IDS_SCENARIOS, EXPECTED["ids"], strict=True)),
)
def test_clockify_ids_match_original(scenario, expected):
    dataset, month, report_only, script_name = scenario
    sheets = InMemorySheetRepository(
        copy.deepcopy(sample_data.build_write_datasets()[dataset]),
    )
    context = IdsContext(
        sheets,
        FakeClient(sample_data.USER_SCRIPTS[script_name]),
        sample_data.WORKSPACE,
        build_report_loader(sheets),
    )

    result = get_clockify_ids(context, month, report_only)

    assert result == expected["result"]
    assert normalize(trimmed_sheets(sheets.sheets)) == normalize(
        expected["sheets"],
    )


def test_save_month_without_lock_raises_gse_error(monkeypatch):
    sheets = InMemorySheetRepository(
        copy.deepcopy(sample_data.build_datasets()["main"]),
    )
    held = threading.Lock()
    held.acquire()
    monkeypatch.setattr("core.utils.locks._SCRIPT_LOCK", held)
    monkeypatch.setattr(base_writer, "LOCK_SECONDS", 0.01)

    with pytest.raises(GseError, match="reintenta"):
        BaseWriter(sheets, CONNECTION, NOW).save_month("2026-09", [], None)


def test_ids_without_lock_return_error(monkeypatch):
    sheets = InMemorySheetRepository(
        copy.deepcopy(sample_data.build_datasets()["main"]),
    )
    held = threading.Lock()
    held.acquire()
    monkeypatch.setattr("core.utils.locks._SCRIPT_LOCK", held)
    monkeypatch.setattr(clockify_ids, "LOCK_SECONDS", 0.01)
    context = IdsContext(
        sheets,
        FakeClient(sample_data.USER_SCRIPTS["ok"]),
        sample_data.WORKSPACE,
        build_report_loader(sheets),
    )

    result = get_clockify_ids(context, "2026-09", False)

    assert result == {
        "ok": False,
        "error": "La hoja está siendo actualizada. Reintenta.",
    }


def test_ids_require_client_configuration():
    sheets = InMemorySheetRepository(
        copy.deepcopy(sample_data.build_datasets()["main"]),
    )
    context = IdsContext(sheets, None, "", build_report_loader(sheets))

    result = get_clockify_ids(context, "2026-09", False)

    assert result == {"ok": False, "error": "Clockify no está configurado."}


def test_ids_list_users_by_pages_until_short_page():
    sheets = InMemorySheetRepository(
        copy.deepcopy(sample_data.build_write_datasets()["ids_with_d"]),
    )
    full = [{"name": f"X{i}", "id": f"x{i}"} for i in range(200)]
    client = FakeClient(
        [
            {"status": 200, "body": full},
            {"status": 200, "body": sample_data.USER_LIST},
        ],
    )
    context = IdsContext(
        sheets,
        client,
        sample_data.WORKSPACE,
        build_report_loader(sheets),
    )

    result = get_clockify_ids(context, "2026-09", False)

    assert result["ok"] is True
    assert [call[1] for call in client.calls] == [1, 2]
    assert all(call[2] == 200 for call in client.calls)


def test_ids_stop_when_listing_takes_too_long():
    sheets = InMemorySheetRepository(
        copy.deepcopy(sample_data.build_write_datasets()["ids_with_d"]),
    )
    full = [{"name": f"X{i}", "id": f"x{i}"} for i in range(200)]
    ticks = iter([0.0, 41.0, 82.0])
    context = IdsContext(
        sheets,
        FakeClient([{"status": 200, "body": full}]),
        sample_data.WORKSPACE,
        build_report_loader(sheets),
        lambda: next(ticks),
    )

    result = get_clockify_ids(context, "2026-09", False)

    assert result["ok"] is False
    assert "demasiado largo" in result["error"]
    assert sheets.sheets["Bandas/rol"][0][3] == "Banda"


def test_report_loader_persists_downloaded_month(monkeypatch):
    sheets = InMemorySheetRepository(
        copy.deepcopy(sample_data.build_datasets()["no_base"]),
    )
    store = BaseStore(sheets, CONNECTION, NOW)
    writer = BaseWriter(sheets, CONNECTION, NOW)
    loader = MonthReportLoader(
        ("KEY", sample_data.WORKSPACE, "America/Mexico_City"),
        (store, CONNECTION, MemoryCache()),
        writer.save_month,
    )
    records = build_records()
    monkeypatch.setattr(loader, "_download", lambda month, ids: records)

    loader("2026-09", True, None)

    base = sheets.sheets["08.Base Clockify 2026"]
    control = sheets.sheets["GSE_Base_Control"]
    assert len(base) == 1 + len(records)
    assert control[1][1] == "2026-09"
    assert control[1][4] == len(records)
