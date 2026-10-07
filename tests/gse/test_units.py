"""Pruebas de la cache del resultado, el reporte de Clockify y la base."""

import copy
from datetime import UTC, date, datetime, timedelta

import pytest

from apps.gse.exceptions import GseError
from apps.gse.services import clockify_month
from apps.gse.services.base_store import (
    BaseStore,
    Connection,
    build_connection,
    parse_saved_at,
)
from apps.gse.services.cells import format_base_date
from apps.gse.services.clockify_month import (
    MonthReportLoader,
    build_payload,
    raise_for_report_status,
    read_report_entry,
)
from apps.gse.services.month_report import GseContext, get_month
from apps.gse.services.refresh import refresh_sheet_reads
from apps.gse.services.result_cache import ResultCache
from apps.gse.services.year_base import last_month, parse_year
from tests.fakes import InMemorySheetRepository
from tests.gse import sample_data

NOW = datetime(2026, 10, 2, 18, 0, tzinfo=UTC)
CONNECTION = Connection(sample_data.WORKSPACE, sample_data.CONNECTION)


class DictStore:
    def __init__(self):
        self.items = {}
        self.timeouts = []

    def get(self, key):
        return self.items.get(key)

    def set(self, key, value, timeout):
        self.items[key] = value
        self.timeouts.append(timeout)

    def delete(self, key):
        self.items.pop(key, None)


def test_connection_key_hides_api_key():
    connection = build_connection("secreto", "ws 1/x")

    assert connection.workspace == "ws 1/x"
    assert connection.key.startswith("ws_1_x_")
    assert "secreto" not in connection.key
    assert len(connection.key.split("_")[-1]) == 16


def test_year_and_last_month():
    assert parse_year("2026") == 2026
    assert parse_year(2026.5) is None
    assert parse_year("abc") is None
    assert parse_year(1999) is None
    assert last_month(2025, date(2026, 10, 2)) == 12
    assert last_month(2026, date(2026, 10, 2)) == 10
    assert last_month(2027, date(2026, 10, 2)) == 0


def test_format_base_date_accepts_serial_numbers():
    assert format_base_date(46_023) == "2026-01-01"
    assert format_base_date(5) == ""
    assert format_base_date("1/2/2026") == "2026-02-01"
    assert format_base_date("2026-03-04T10:00") == "2026-03-04"
    assert format_base_date("x") == ""


def test_parse_saved_at_variants():
    assert parse_saved_at("2026-10-02T17:30:00.000Z") == datetime(
        2026,
        10,
        2,
        17,
        30,
        tzinfo=UTC,
    )
    assert parse_saved_at("no es fecha") is None
    assert parse_saved_at(46_023.5) is not None


def build_store(now):
    reader = InMemorySheetRepository(
        copy.deepcopy(sample_data.build_datasets()["main"]),
    )

    return BaseStore(reader, CONNECTION, now)


def test_current_month_coverage_expires_after_one_hour():
    fresh = build_store(NOW)
    stale = build_store(NOW + timedelta(hours=2))

    assert fresh.read_stored_month("2026-10", ["u1", "u2"], False)
    assert stale.read_stored_month("2026-10", ["u1", "u2"], False) is None
    assert stale.read_stored_month("2026-10", ["u1", "u2"], True)
    # Un mes anterior no vence.
    assert stale.read_stored_month("2026-09", None, False)


def test_coverage_without_requested_people_is_ignored():
    store = build_store(NOW)

    assert store.read_stored_month("2026-10", ["u1", "u9"], True) is None
    assert store.read_stored_month("2026-10", None, True) is None


def test_invalid_coverage_json_is_reported():
    store = build_store(NOW)
    store._reader.sheets["GSE_Base_Control"][1][2] = "{roto"

    with pytest.raises(GseError):
        store.read_stored_month("2026-09", None, True)


def test_result_cache_round_trip_and_fallback():
    store = DictStore()
    cache = ResultCache(store, "SS", date(2026, 10, 2), lambda: 1_000.0)
    result = {"data": {"2026-09": {"ok": True}}, "bandas": [1], "total": 5}

    assert cache.read((2026, "", False)) == {"ok": True, "cached": False}
    saved = cache.save(2026, "", result)
    assert saved == {"ok": True, "savedAt": 1_000_000}
    assert store.timeouts == [21_600]

    general = cache.read((2026, "", False))
    assert general["cached"] is True and general["scopeArea"] == ""

    by_area = cache.read((2026, "QA", False))
    assert by_area["cached"] is True and by_area["scopeArea"] == ""

    cache.save(2026, "QA", result)
    assert cache.read((2026, "QA", False))["scopeArea"] == "QA"

    assert cache.read((2026, "QA", True)) == {"ok": True, "cached": False}
    # Borrar un area tambien borra el resultado general, como el original.
    assert cache.read((2026, "", False)) == {"ok": True, "cached": False}
    assert cache.read((2026, "QA", False)) == {"ok": True, "cached": False}


def test_result_cache_expires_and_validates():
    store = DictStore()
    now = [1_000.0]
    cache = ResultCache(store, "SS", date(2026, 10, 2), lambda: now[0])
    result = {"data": {"2026-09": {"ok": True}}, "total": 1}
    cache.save(2026, "", result)
    now[0] += 21_601

    assert cache.read((2026, "", False)) == {"ok": True, "cached": False}
    assert cache.save(2026, "", None)["ok"] is False
    assert cache.save(2026, "", {"data": {}})["ok"] is False
    pending = {"data": {"2026-09": {"pending": True}}}
    assert cache.save(2026, "", pending)["error"] == (
        "Solo se guardan lecturas terminadas."
    )
    huge = {"data": {"2026-09": {"x": "a" * 5_000_001}}}
    assert cache.save(2026, "", huge)["error"] == (
        "Resultado demasiado grande para caché."
    )


def test_result_cache_key_changes_with_month_and_book():
    store = DictStore()
    first = ResultCache(store, "SS", date(2026, 10, 2))
    first.save(2026, "", {"data": {"m": {"ok": True}}})
    other_month = ResultCache(store, "SS", date(2026, 11, 2))
    other_book = ResultCache(store, "OTRO", date(2026, 10, 2))

    assert first.read((2026, "", False))["cached"] is True
    assert other_month.read((2026, "", False))["cached"] is False
    assert other_book.read((2026, "", False))["cached"] is False


def test_report_payload_filters_by_users():
    payload = build_payload("2026-02", ["u1"], 3, "America/Mexico_City")

    assert payload["dateRangeEnd"] == "2026-02-28T23:59:59.999"
    assert payload["detailedFilter"]["page"] == 3
    assert payload["users"] == {"ids": ["u1"], "contains": "CONTAINS"}
    assert "users" not in build_payload("2026-02", None, 1, "UTC")


def test_report_status_messages():
    raise_for_report_status(200, "2026-09")

    with pytest.raises(GseError, match="Puedes consultar la base en Sheets"):
        raise_for_report_status(403, "2026-09")

    with pytest.raises(GseError, match="Revisa la conexión"):
        raise_for_report_status(500, "2026-09")


def test_read_report_entry_variants():
    record = read_report_entry(
        {
            "_id": "a1",
            "userId": "u1",
            "userName": "Ana",
            "projectName": "P",
            "taskName": "T",
            "tags": [{"name": "x"}, "y"],
            "billable": 1,
            "timeInterval": {
                "start": "2026-09-30T23:30:00Z",
                "duration": "PT1H30M",
            },
        },
        "America/Mexico_City",
    )

    assert (record.day, record.hours, record.tags) == (
        "2026-09-30",
        1.5,
        ["x", "y"],
    )
    assert record.billable is True

    nested = read_report_entry(
        {
            "id": "a2",
            "user": {"id": "u2", "name": "Luis"},
            "project": {"name": "Q"},
            "task": {"name": "W"},
            "timeInterval": {"duration": 3600},
        },
        "UTC",
    )

    assert (nested.user_id, nested.resource, nested.project) == (
        "u2",
        "Luis",
        "Q",
    )
    assert nested.day == "" and nested.hours == 1.0

    with pytest.raises(GseError, match="Registro sin ID"):
        read_report_entry({"timeInterval": {"duration": 1}}, "UTC")

    with pytest.raises(GseError, match="Registro sin duración"):
        read_report_entry({"_id": "x", "timeInterval": {}}, "UTC")


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body

        return self._body


def entry(index, hours=3600):
    return {
        "_id": f"e{index}",
        "userId": "u1",
        "userName": "Ana Pérez",
        "projectName": "AMK.008",
        "timeInterval": {"start": "2026-09-03T15:00:00Z", "duration": hours},
    }


class FakeClient:
    responses = []
    payloads = []

    def __init__(self, api_key, sleep):
        self.sleep = sleep

    def post_workspace_report(self, workspace_id, payload):
        FakeClient.payloads.append((workspace_id, payload))

        return FakeClient.responses.pop(0)


def build_loader(monkeypatch, persist=None, settings=("k", "ws1", "UTC")):
    monkeypatch.setattr(clockify_month, "ClockifyClient", FakeClient)
    FakeClient.payloads = []
    cache = DictStore()
    store = build_store(NOW + timedelta(days=30))
    sleeps = []
    loader = MonthReportLoader(
        settings,
        (store, CONNECTION, cache),
        persist,
        sleeps.append,
    )

    return loader, cache, sleeps


def test_loader_downloads_pages_and_caches(monkeypatch):
    saved = []
    loader, cache, sleeps = build_loader(
        monkeypatch,
        lambda month, records, ids: saved.append((month, len(records), ids)),
    )
    first_page = [entry(i) for i in range(200)]
    FakeClient.responses = [
        FakeResponse(200, {"timeentries": first_page}),
        FakeResponse(200, {"timeentries": [entry(500)]}),
    ]

    records = loader("2026-11", False, ["u1"])

    assert len(records) == 201
    assert [p["detailedFilter"]["page"] for _, p in FakeClient.payloads] == [
        1,
        2,
    ]
    assert sleeps == [0.25]
    assert saved == [("2026-11", 201, ["u1"])]
    assert len(cache.items) == 1

    # Segunda consulta: sale de la cache sin llamar a Clockify.
    again = loader("2026-11", False, ["u1"])

    assert len(again) == 201 and len(FakeClient.payloads) == 2
    assert saved[-1] == ("2026-11", 201, ["u1"])

    FakeClient.responses = [FakeResponse(200, {"timeentries": []})]
    assert loader("2026-11", True, ["u1"]) == []


def test_loader_prefers_the_stored_base(monkeypatch):
    loader, _, _ = build_loader(monkeypatch)
    loader._store = build_store(NOW)

    records = loader("2026-09", False, None)

    assert records and not FakeClient.payloads


def test_loader_errors(monkeypatch):
    loader, _, _ = build_loader(monkeypatch, settings=("", "ws1", "UTC"))

    with pytest.raises(GseError, match="no está configurado"):
        loader("2026-11", False, None)

    loader, _, _ = build_loader(monkeypatch)
    FakeClient.responses = [FakeResponse(403, {})]

    with pytest.raises(GseError, match="reporte global"):
        loader("2026-11", False, None)

    FakeClient.responses = [FakeResponse(200, ValueError("x"))]

    with pytest.raises(GseError, match="JSON valido"):
        loader("2026-11", False, None)

    FakeClient.responses = [FakeResponse(200, {"otra": 1})]

    with pytest.raises(GseError, match="sin timeentries"):
        loader("2026-11", False, None)

    page = [entry(i) for i in range(200)]
    FakeClient.responses = [
        FakeResponse(200, {"timeentries": page}),
        FakeResponse(200, {"timeentries": page}),
    ]

    with pytest.raises(GseError, match="repitió una página"):
        loader("2026-11", False, None)


def test_loader_stops_after_too_many_pages(monkeypatch):
    loader, _, _ = build_loader(monkeypatch)
    monkeypatch.setattr(clockify_month, "MAX_PAGES", 2)
    FakeClient.responses = [
        FakeResponse(
            200, {"timeentries": [entry(i + 200 * n) for i in range(200)]}
        )
        for n in range(2)
    ]

    with pytest.raises(GseError, match="Demasiadas páginas"):
        loader("2026-11", False, None)


def test_month_detail_keeps_investment_categories_from_tags():
    sheets = copy.deepcopy(sample_data.build_datasets()["main"])
    base = sheets["08.Base Clockify 2026"]
    base.append(
        sample_data.base_row(
            [
                "AMK.008_S4",
                "Ana Pérez",
                "2026-09-05",
                2,
                "dev",
                "INV_operativa, x",
                "Yes",
                "inv1",
                "u1",
            ],
        ),
    )
    base.append(
        sample_data.base_row(
            [
                "AMK.008_S4",
                "Ana Pérez",
                "2026-09-06",
                1.5,
                "dev",
                "Inv_comercial",
                "Yes",
                "inv2",
                "u1",
            ],
        ),
    )
    reader = InMemorySheetRepository(sheets)
    connection = Connection(sample_data.WORKSPACE, sample_data.CONNECTION)
    context = GseContext(
        reader,
        BaseStore(reader, connection, datetime(2026, 10, 2, 18, tzinfo=UTC)),
        lambda *_: [],
    )

    result = get_month(context, ("2026-09", "sheet", False, ""))

    rows = [
        item for item in result["detalle"] if item["recurso"] == "Ana Pérez"
    ]
    operational = sum(
        item["horas"]
        for item in rows
        if "Inversión Operaciones" in item["categorias"]
    )
    commercial = sum(
        item["horas"]
        for item in rows
        if "Inversión Comercial" in item["categorias"]
    )
    assert operational == 2
    assert commercial == 1.5


class ForgetRecorder:
    def __init__(self, names):
        self.names = names
        self.forgotten = []

    def list_sheet_names(self):
        return self.names

    def forget_reads(self, names):
        self.forgotten = list(names)


def test_refresh_sheet_reads_only_forgets_gse_sheets():
    reader = ForgetRecorder(
        [
            "Bandas/rol",
            "CatalagoProyectos ",
            "GSE_Base_Control",
            "08.Base Clockify 2026",
            "08.Base Clockify 2025",
            "Otra hoja",
        ],
    )

    refresh_sheet_reads(reader, 2026)

    assert sorted(reader.forgotten) == [
        "08.Base Clockify 2026",
        "Bandas/rol",
        "CatalagoProyectos ",
        "GSE_Base_Control",
    ]
