import pytest

from apps.datastore.models import SheetSnapshot
from apps.datastore.services.sheet_sync import sync_sheets
from core.sheets import store_read_cache
from core.sheets.repository import GoogleSheetRepository
from core.sheets.store_read_cache import (
    SHEET_IDS_NAME,
    StoredSheetReadCache,
)
from tests.core.test_repository import build_service

pytestmark = pytest.mark.django_db

SHEETS = {
    "MPB": [["ID", "HORAS"], ["AMK.008", 100]],
    "Otra": [["A"], ["x"]],
}


@pytest.fixture(autouse=True)
def clean_memory():
    store_read_cache._memory.clear()


def stored_cache():
    return StoredSheetReadCache("sheet-id", 0, ["MPB"])


def batch_calls(service):
    values = service.spreadsheets.return_value.values.return_value
    return values.batchGet.call_count


def test_stored_sheet_is_saved_and_returned_without_expiry():
    cache = stored_cache()
    assert cache.get_values("MPB") is None
    cache.set_values("MPB", SHEETS["MPB"])
    assert SheetSnapshot.objects.get(name="MPB").row_count == 2
    assert cache.get_values("MPB") == SHEETS["MPB"]


def test_services_can_modify_what_they_read_without_changing_the_store():
    cache = stored_cache()
    cache.set_values("MPB", [["ID"], ["a"]])
    cache.get_values("MPB")[1][0] = "cambiado"
    assert cache.get_values("MPB")[1][0] == "a"


def test_other_sheets_keep_using_the_normal_cache():
    cache = stored_cache()
    cache.set_values("Otra", SHEETS["Otra"])
    assert not SheetSnapshot.objects.filter(name="Otra").exists()


def test_invalidate_removes_the_stored_sheet_and_the_sheet_ids():
    cache = stored_cache()
    cache.set_values("MPB", SHEETS["MPB"])
    cache.set_sheet_ids({"MPB": 3})
    assert cache.get_sheet_ids() == {"MPB": 3}
    cache.invalidate_values("MPB")
    cache.invalidate_sheet_ids()
    assert cache.get_values("MPB") is None
    assert cache.get_sheet_ids() is None


def test_a_newer_snapshot_replaces_the_one_kept_in_memory():
    cache = stored_cache()
    cache.set_values("MPB", [["ID"], ["viejo"]])
    assert cache.get_values("MPB")[1] == ["viejo"]
    cache.set_values("MPB", [["ID"], ["nuevo"]])
    assert cache.get_values("MPB")[1] == ["nuevo"]


def test_repository_reads_google_once_and_then_only_the_store():
    service = build_service(SHEETS)
    first = GoogleSheetRepository(service, "sheet-id", stored_cache())
    assert first.read_values("MPB") == SHEETS["MPB"]
    assert batch_calls(service) == 1
    # Otra peticion (otro repositorio): ni hojas ni IDs vuelven a Google.
    second = GoogleSheetRepository(service, "sheet-id", stored_cache())
    assert second.read_values("MPB") == SHEETS["MPB"]
    assert second.sheet_exists("MPB")
    assert batch_calls(service) == 1
    assert service.spreadsheets.return_value.get.call_count == 1


def test_an_app_write_makes_the_next_read_fetch_a_fresh_copy():
    service = build_service(SHEETS)
    repository = GoogleSheetRepository(service, "sheet-id", stored_cache())
    repository.read_values("MPB")
    repository.write_cell("MPB", 2, 2, 250)
    assert not SheetSnapshot.objects.filter(name="MPB").exists()
    service.spreadsheets.return_value.values.return_value.batchGet.reset_mock()
    GoogleSheetRepository(service, "sheet-id", stored_cache()).read_values(
        "MPB"
    )
    assert batch_calls(service) == 1
    assert SheetSnapshot.objects.filter(name="MPB").exists()


def test_sync_saves_present_sheets_in_one_call_and_drops_missing_ones():
    stale = StoredSheetReadCache("sheet-id", 0, ["Faltante"])
    stale.set_values("Faltante", [["x"]])
    service = build_service(SHEETS)
    repository = GoogleSheetRepository(service, "sheet-id")
    saved = sync_sheets(repository, ["MPB", "Faltante"])
    assert saved == ["MPB"]
    assert batch_calls(service) == 1
    assert SheetSnapshot.objects.get(name="MPB").rows == SHEETS["MPB"]
    assert not SheetSnapshot.objects.filter(name="Faltante").exists()
    assert SheetSnapshot.objects.get(name=SHEET_IDS_NAME).rows == {
        "MPB": 0,
        "Otra": 1,
    }
