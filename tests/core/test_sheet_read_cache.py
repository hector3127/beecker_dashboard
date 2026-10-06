import pickle
from unittest.mock import MagicMock

from core.sheets.read_cache import SheetReadCache
from core.sheets.repository import GoogleSheetRepository


class PickleStore:
    """Cache en memoria que copia los valores, como la de Django."""

    def __init__(self):
        self.data = {}

    def get(self, key):
        stored = self.data.get(key)

        return pickle.loads(stored) if stored is not None else None

    def set(self, key, value, timeout):
        self.data[key] = pickle.dumps(value)

    def delete(self, key):
        self.data.pop(key, None)


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
    spreadsheets.batchUpdate.return_value.execute.return_value = {
        "replies": [{"addSheet": {"properties": {"sheetId": 99}}}],
    }

    return service


def batch_get_count(service):
    values = service.spreadsheets.return_value.values.return_value

    return values.batchGet.call_count


def sheet_list_count(service):
    return service.spreadsheets.return_value.get.call_count


def build_repository(service, store, seconds=900):
    return GoogleSheetRepository(
        service,
        "sheet-id",
        SheetReadCache("sheet-id", seconds, store),
    )


def test_second_request_reads_from_shared_cache():
    store = PickleStore()
    service = build_service({"Proyectos": [["ID"], ["P-1"]]})

    first = build_repository(service, store).read_values("Proyectos")
    second = build_repository(service, store).read_values("Proyectos")

    assert first == second == [["ID"], ["P-1"]]
    assert batch_get_count(service) == 1
    assert sheet_list_count(service) == 1


def test_cached_values_are_copies():
    store = PickleStore()
    service = build_service({"Proyectos": [["ID"], ["P-1"]]})
    build_repository(service, store).read_values("Proyectos")

    changed = build_repository(service, store).read_values("Proyectos")
    changed.append(["P-2"])

    untouched = build_repository(service, store).read_values("Proyectos")
    assert untouched == [["ID"], ["P-1"]]


def test_prefetch_only_asks_for_sheets_missing_from_cache():
    store = PickleStore()
    service = build_service(
        {"Proyectos": [["ID"], ["P-1"]], "Riesgos": [["ID"], ["R-1"]]},
    )
    build_repository(service, store).read_values("Proyectos")

    repository = build_repository(service, store)
    repository.prefetch(["Proyectos", "Riesgos"])

    batch_get = service.spreadsheets.return_value.values.return_value.batchGet
    assert batch_get.call_count == 2
    assert batch_get.call_args.kwargs["ranges"] == ["'Riesgos'"]
    assert repository.read_values("Proyectos") == [["ID"], ["P-1"]]


def test_write_invalidates_the_sheet_for_other_requests():
    store = PickleStore()
    service = build_service({"Riesgos": [["ID"], ["R-1"]]})
    build_repository(service, store).read_values("Riesgos")

    build_repository(service, store).append_row("Riesgos", ["R-2"])
    build_repository(service, store).read_values("Riesgos")

    assert batch_get_count(service) == 2


def test_write_to_one_sheet_keeps_the_others_cached():
    store = PickleStore()
    service = build_service(
        {"Riesgos": [["ID"], ["R-1"]], "Proyectos": [["ID"], ["P-1"]]},
    )
    reader = build_repository(service, store)
    reader.prefetch(["Riesgos", "Proyectos"])

    build_repository(service, store).append_row("Riesgos", ["R-2"])
    build_repository(service, store).read_values("Proyectos")

    assert batch_get_count(service) == 1


def test_new_sheet_invalidates_cached_sheet_names():
    store = PickleStore()
    service = build_service({"Riesgos": [["ID"], ["R-1"]]})
    build_repository(service, store).read_values("Riesgos")

    build_repository(service, store).ensure_sheet("Nueva", ["ID"])

    assert not any(key.endswith(":ids") for key in store.data)
    build_repository(service, store).list_sheet_names()
    assert sheet_list_count(service) == 2


def test_zero_seconds_turns_the_shared_cache_off():
    store = PickleStore()
    service = build_service({"Riesgos": [["ID"], ["R-1"]]})

    build_repository(service, store, seconds=0).read_values("Riesgos")
    build_repository(service, store, seconds=0).read_values("Riesgos")

    assert batch_get_count(service) == 2
    assert store.data == {}


def test_repository_without_shared_cache_keeps_old_behavior():
    service = build_service({"Riesgos": [["ID"], ["R-1"]]})

    GoogleSheetRepository(service, "sheet-id").read_values("Riesgos")
    GoogleSheetRepository(service, "sheet-id").read_values("Riesgos")

    assert batch_get_count(service) == 2


def test_sheet_names_with_accents_get_distinct_keys():
    store = PickleStore()
    cache = SheetReadCache("sheet-id", 900, store)

    cache.set_values("Histórico", [["a"]])
    cache.set_values("Historico", [["b"]])

    assert cache.get_values("Histórico") == [["a"]]
    assert cache.get_values("Historico") == [["b"]]
