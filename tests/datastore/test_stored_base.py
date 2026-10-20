from datetime import UTC, date, datetime

import pytest

from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry, SyncRun
from apps.datastore.services import stored_base
from apps.datastore.services.stored_base import (
    StoredBaseStore,
    build_hour_index_from_store,
    read_hour_records,
)
from apps.gse.services.base_store import (
    BaseStore,
    Connection,
    build_base_store,
)
from apps.portal.services import eva4_index
from apps.portal.services.eva4_hours import build_hour_index
from tests.fakes import InMemorySheetRepository

pytestmark = pytest.mark.django_db
NOW = datetime(2026, 10, 19, tzinfo=UTC)
CONNECTION = Connection("ws", "ws_key")


def add(
    entry_id,
    day,
    *,
    tags=(),
    task="Monitoreo bot",
    seconds=3600,
    user="u1",
    billable=True,
    project="AMK.008",
):
    ClockifyTimeEntry.objects.create(
        entry_id=entry_id,
        project_id="p1",
        project_name=project,
        task_name=task,
        user_id=user,
        user_name="Ana Ruiz",
        tags=list(tags),
        billable=billable,
        entry_date=day,
        month=day.replace(day=1) if day else date(2026, 9, 1),
        duration_seconds=seconds,
    )


def synced(month):
    ClockifyMonthSync.objects.create(
        month=month,
        entries_count=0,
        total_seconds=0,
        synced_at=NOW,
        run=SyncRun.objects.create(kind="test"),
    )


def test_records_are_ordered_by_id_and_keep_the_sheet_format():
    add("b2", date(2026, 9, 3), tags=["Monitoreo"], seconds=5400)
    add("a1", date(2026, 9, 2), tags=["Análisis", "gestión"], billable=False)
    records = read_hour_records("2026-09")
    assert [r.record_id for r in records] == ["a1", "b2"]
    first = records[0]
    assert (first.day, first.hours, first.billable) == (
        "2026-09-02",
        1.0,
        False,
    )
    assert (first.resource, first.project, first.user_id) == (
        "Ana Ruiz",
        "AMK.008",
        "u1",
    )
    assert records[1].hours == 1.5


def test_a_tag_with_a_comma_is_split_like_the_sheet_did():
    add("a1", date(2026, 9, 2), tags=["Análisis, gestión y presentación"])
    [record] = read_hour_records("2026-09")
    assert record.tags == ["Análisis", "gestión y presentación"]


def test_users_filter_and_entries_without_a_start_day_are_left_out():
    add("a1", date(2026, 9, 2), user="u1")
    add("a2", date(2026, 9, 2), user="u2")
    ClockifyTimeEntry.objects.create(
        entry_id="x",
        project_id="p",
        user_id="u1",
        month=date(2026, 9, 1),
        duration_seconds=1,
    )
    assert [r.record_id for r in read_hour_records("2026-09", ["u2"])] == ["a2"]
    assert len(read_hour_records("2026-09")) == 2


def test_store_reads_synced_months_without_touching_sheets():
    add("a1", date(2026, 9, 2))
    synced(date(2026, 9, 1))
    store = StoredBaseStore(InMemorySheetRepository({}), CONNECTION, NOW)
    assert [
        r.record_id for r in store.read_stored_month("2026-09", None, False)
    ] == ["a1"]
    assert store.read_stored_month("2026-09", ["nadie"], False) == []


def test_store_falls_back_to_the_sheet_for_months_not_synced():
    store = StoredBaseStore(InMemorySheetRepository({}), CONNECTION, NOW)
    # Sin la hoja de la base ni el mes sincronizado no hay de donde leer.
    assert store.read_stored_month("2026-08", None, False) is None


def test_factory_follows_the_setting(settings):
    reader = InMemorySheetRepository({})
    settings.CLOCKIFY_STORE_ENABLED = False
    assert type(build_base_store(reader, CONNECTION, NOW)) is BaseStore
    settings.CLOCKIFY_STORE_ENABLED = True
    assert isinstance(
        build_base_store(reader, CONNECTION, NOW), StoredBaseStore
    )


SHEET_HEADER = [
    "ID Registro",
    "Task",
    "Start Date",
    "Tags",
    "Duration (decimal)",
    "Workspace",
]


def sheet_row(entry_id, task, day, tags, hours):
    return [entry_id, task, day, tags, hours, "ws"]


def test_hour_index_from_the_database_equals_the_one_from_the_sheet():
    entries = [
        ("1", " Monitoreo  Bot ", date(2026, 3, 4), ["Monitoreo"], 5400),
        ("2", "Monitoreo Bot", date(2026, 3, 9), ["Monitoreo"], 1800),
        ("3", "Otra tarea", date(2026, 3, 9), ["Ajustes L1"], 3600),
        # Etiquetas distintas o varias: no cuentan.
        ("4", "Otra tarea", date(2026, 3, 9), ["Ajustes L1", "Otra"], 3600),
        ("5", "Otra tarea", date(2026, 3, 9), ["Reunion"], 3600),
        # Las etiquetas extra solo cuentan desde septiembre.
        ("6", "Cambios", date(2026, 8, 9), ["Change Request"], 3600),
        ("7", "Cambios", date(2026, 9, 9), ["Change Request"], 7200),
        # Una tarea sin horas validas igual se conoce; otro ano no entra.
        ("8", "Vieja", date(2025, 12, 31), ["Monitoreo"], 3600),
    ]
    for entry_id, task, day, tags, seconds in entries:
        add(entry_id, day, task=task, tags=tags, seconds=seconds)
    sheet = [SHEET_HEADER] + [
        sheet_row(
            entry_id, task, day.isoformat(), ", ".join(tags), seconds / 3600
        )
        for entry_id, task, day, tags, seconds in entries
        if day.year == 2026
    ]
    from_sheet = build_hour_index(sheet, 2026)
    from_store = build_hour_index_from_store(2026)
    assert from_store["totals"] == from_sheet["totals"]
    assert from_store["tasks"] == from_sheet["tasks"]
    assert from_store["errors"] == set()
    assert from_store["totals"]["2026-03"]["monitoreo bot"] > 0
    assert "2026-08" not in from_store["totals"]
    assert "vieja" not in from_store["tasks"]


def test_hour_index_groups_hours_by_project_and_task():
    day = date(2026, 10, 5)
    add(
        "1",
        day,
        project="ROC.NSC.001",
        task="3634 - Gestión",
        tags=["Monitoreo"],
    )
    add("2", day, project="ROC.NSC.001", task="3634 - Otra", tags=["Monitoreo"])
    add(
        "3",
        day,
        project="ROC.OTRO.001",
        task="3634 - Gestión",
        tags=["Monitoreo"],
    )
    add(
        "4", day, project="ROC.NSC.001", task="3634 - Gestión", tags=["Reunion"]
    )
    index = build_hour_index_from_store(2026)
    month = index["project_tasks"]["2026-10"]
    assert month["roc.nsc.001"] == {"3634 - gestión": 1, "3634 - otra": 1}
    assert month["roc.otro.001"] == {"3634 - gestión": 1}
    assert {"roc.nsc.001", "roc.otro.001"} <= index["projects"]


def test_eva4_uses_the_database_only_for_synced_years(settings, monkeypatch):
    settings.CLOCKIFY_STORE_ENABLED = True
    add("1", date(2026, 3, 4), tags=["Monitoreo"])
    reader = InMemorySheetRepository({})
    # Sin ningun mes sincronizado el ano se lee de la hoja (que no existe).
    assert eva4_index.use_store(2026) is False
    synced(date(2026, 3, 1))
    assert eva4_index.use_store(2026) is True
    assert eva4_index.use_store(2025) is False
    index = eva4_index.load_hour_index(reader, 2026)
    assert "monitoreo bot" in index["tasks"]
    monkeypatch.setattr(
        stored_base,
        "build_hour_index_from_store",
        lambda year: pytest.fail("deberia salir de la cache"),
    )
    assert eva4_index.load_hour_index(reader, 2026) is not None
