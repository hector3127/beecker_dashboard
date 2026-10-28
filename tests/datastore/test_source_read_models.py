"""Lecturas locales, publicación atómica y coherencia de resultados."""

from datetime import date
from io import StringIO
from unittest.mock import Mock

import pytest
from django.core.cache.backends.locmem import LocMemCache
from django.core.management import CommandError, call_command
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.clockify.services.clockify_client import ClockifyProject
from apps.clockify.services.time_entry_loader import ClockifyTimeEntryLoader
from apps.daily.services.ixs_panel import (
    IxsAzure,
    fetch_raw_items,
    load_raw_items,
)
from apps.daily.services.ixs_raid import RaidContext, load_relation_details
from apps.datastore.models import AzureProject, ClockifyCatalog, DataRevision
from apps.datastore.services import (
    azure_panel_store,
    azure_store,
    clockify_catalog,
)
from core.data_cache import (
    SourceCacheMiddleware,
    bump_revision,
    make_key,
    revision_scope,
)
from core.sheets.store_read_cache import (
    SnapshotValidationError,
    delete_snapshot,
    read_snapshot,
    save_snapshot,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def versioned_cache(settings):
    settings.CLOCKIFY_STORE_ENABLED = True
    return LocMemCache("source-read-tests", {"KEY_FUNCTION": make_key})


def test_old_inflight_result_cannot_replace_new_generation(versioned_cache):
    cache = versioned_cache
    with revision_scope():
        cache.set("portal:financial:test", "before")
        with transaction.atomic():
            bump_revision()
        # A request started before the commit finishes late.
        cache.set("portal:financial:test", "late old result")
    with revision_scope():
        assert cache.get("portal:financial:test") is None
        cache.set("portal:financial:test", "new")
    with revision_scope():
        assert cache.get("portal:financial:test") == "new"


def test_rollback_and_non_data_keys_are_preserved(versioned_cache):
    cache = versioned_cache
    with revision_scope():
        cache.set("portal:test", "valid")
        cache.set("session:person", "session")
        cache.set("portal:executive-refresh:v1", "running")
    with pytest.raises(ValueError), transaction.atomic():
        bump_revision()
        raise ValueError("rollback")
    assert cache.get("portal:test") == "valid"
    with transaction.atomic():
        bump_revision()
    assert cache.get("session:person") == "session"
    assert cache.get("portal:executive-refresh:v1") == "running"
    assert cache.get("portal:test") is None


def test_sheet_publication_and_delete_invalidate_results(versioned_cache):
    cache = versioned_cache
    cache.set("portal:test", 1)
    save_snapshot("MPB", [["ID"], ["P"]])
    assert cache.get("portal:test") is None
    cache.set("portal:test", 2)
    delete_snapshot("MPB")
    assert cache.get("portal:test") is None


def test_catalog_scoped_order_empty_and_failure():
    client = Mock()
    client.list_projects.return_value = [
        ClockifyProject("b", "B"),
        ClockifyProject("a", "A"),
    ]
    clockify_catalog.sync_catalog(client, "w")
    assert [p.project_id for p in clockify_catalog.read_projects("w")] == [
        "b",
        "a",
    ]
    assert clockify_catalog.read_projects("other") is None
    clockify_catalog.save_tasks("w", "a", [])
    assert clockify_catalog.read_tasks("w", "a") == []
    assert clockify_catalog.read_tasks("other", "a") is None
    client.list_projects.side_effect = ValueError("offline")
    with pytest.raises(ValueError):
        clockify_catalog.sync_catalog(client, "w")
    assert len(clockify_catalog.read_projects("w")) == 2
    client.list_projects.side_effect = None
    client.list_projects.return_value = []
    clockify_catalog.sync_catalog(client, "w")
    assert clockify_catalog.read_projects("w") == []


def test_loader_uses_local_catalog_and_tasks_with_empty_cache(settings):
    settings.CLOCKIFY_STORE_ENABLED = True
    client = Mock()
    client.list_projects.return_value = [ClockifyProject("p", "P")]
    clockify_catalog.sync_catalog(client, "w")
    tasks = [{"id": "t", "name": "CR1"}]
    clockify_catalog.save_tasks("w", "p", tasks)
    forbidden = Mock(side_effect=AssertionError("Network attempted"))
    loader = ClockifyTimeEntryLoader(
        Mock(), forbidden, "w", date(2026, 10, 27), Mock(), "test"
    )
    assert loader._load_clockify_projects() == [ClockifyProject("p", "P")]
    assert loader.load_project_tasks("p") == tasks
    forbidden.assert_not_called()


def item(value):
    return {
        "id": value,
        "fields": {
            "System.Title": f"P Task {value}",
            "System.WorkItemType": "Task",
            "System.State": "Active",
        },
        "relations": [
            {"rel": "System.LinkTypes.Related", "url": "https://example.org/1"}
        ],
    }


def project():
    return AzureProject.objects.create(
        name="P", position=0, synced_at=timezone.now()
    )


def test_panel_local_matches_live_mapping_without_http():
    project()
    rows = [item(2), item(1)]
    azure_panel_store.save("P", 2, rows)
    client = Mock()
    client.project_url.return_value = "https://example.org/"
    client.send.side_effect = [
        {"workItems": [{"id": 2}, {"id": 1}]},
        {"value": rows},
    ]
    azure = IxsAzure(
        "org", "pat", "P", lambda _: "P", lambda: client, Mock(), lambda: {}
    )
    expected = fetch_raw_items(azure, "P", "P")
    azure.use_store = True
    azure.build_client = Mock(side_effect=AssertionError("Network attempted"))
    actual, notice = load_raw_items(azure, ("P", "P"), False, 123)
    assert {k: v for k, v in actual.items() if k != "obtenidoEn"} == expected
    assert actual["obtenidoEn"] > 123
    assert notice == ""
    context = RaidContext("P", "org", "P", Mock(), True)
    assert load_relation_details(context, [2]) == {"2": rows[0]}
    azure.build_client.assert_not_called()


def test_panel_empty_is_distinct_from_missing_and_main_sync_keeps_payloads():
    project()
    assert azure_panel_store.read("P") is None
    azure_panel_store.save("P", 0, [])
    assert azure_panel_store.read("P")[1] == []
    azure_panel_store.save("P", 1, [item(1)])
    azure_store.save_project("P", 0, ([], [], [], []), 0)
    assert azure_panel_store.read("P")[1] == [item(1)]
    azure_panel_store.invalidate()
    assert azure_panel_store.read("P") is None


def test_incomplete_azure_batch_does_not_publish_or_bump_revision():
    project()
    azure_panel_store.save("P", 1, [item(1)])
    revision = DataRevision.objects.get(pk=1).version
    client = Mock()
    client.project_url.return_value = "https://example.org/"
    client.send.side_effect = [
        {"workItems": [{"id": 2}, {"id": 3}]},
        {"value": [item(2)]},
    ]
    with pytest.raises(ValueError, match="incompleto"):
        total, items = azure_panel_store.download(client, "P")
        azure_panel_store.save("P", total, items)
    assert azure_panel_store.read("P")[1] == [item(1)]
    assert DataRevision.objects.get(pk=1).version == revision


def test_download_preserves_api_batch_order_and_original_limit():
    client = Mock()
    client.project_url.return_value = "https://example.org/"
    responses = [{"workItems": [{"id": i} for i in range(752)]}]
    responses += [
        {"value": [item(i) for i in reversed(range(start, start + 150))]}
        for start in range(0, 750, 150)
    ]
    client.send.side_effect = responses
    total, items = azure_panel_store.download(client, "P")
    assert total == 752
    assert [row["id"] for row in items] == [
        i
        for start in range(0, 750, 150)
        for i in reversed(range(start, start + 150))
    ]
    assert client.send.call_count == 6


def test_middleware_pins_one_revision_for_the_entire_request(settings):
    settings.CLOCKIFY_STORE_ENABLED = True

    def response(_):
        return make_key("portal:first", "", 1), make_key("portal:second", "", 1)

    with CaptureQueriesContext(connection) as queries:
        keys = SourceCacheMiddleware(response)(None)
    assert len(queries) == 1
    assert all("sources:" in key for key in keys)


def test_forced_panel_publishes_new_snapshot_for_next_normal_read():
    project()
    azure_panel_store.save("P", 1, [item(1)])
    client = Mock()
    client.project_url.return_value = "https://example.org/"
    client.send.side_effect = [
        {"workItems": [{"id": 2}]},
        {"value": [item(2)]},
    ]
    azure = IxsAzure(
        "org",
        "pat",
        "P",
        lambda _: "P",
        lambda: client,
        Mock(),
        lambda: {},
        True,
    )
    forced, _ = load_raw_items(azure, ("P", "P"), True, 123)
    client.send.side_effect = AssertionError("Unexpected HTTP")
    normal, _ = load_raw_items(azure, ("P", "P"), False, 456)
    assert normal["workItems"] == forced["workItems"]
    assert azure_panel_store.read("P")[1] == [item(2)]


def test_source_command_keeps_failed_project_and_continues(
    monkeypatch, settings
):
    from apps.datastore.management.commands import sync_read_sources as command

    settings.AZURE_DEVOPS_ORGANIZATION = "org"
    settings.AZURE_DEVOPS_PAT = "test"
    project()
    AzureProject.objects.create(name="Q", position=1, synced_at=timezone.now())
    azure_panel_store.save("P", 1, [item(1)])
    fetch = Mock(side_effect=["P failed", (1, [item(2)])])
    monkeypatch.setattr(command, "fetch_panel", fetch)
    # Core tests cover pool concurrency; publish in the main test thread.
    monkeypatch.setattr(
        command, "map_in_parallel", lambda fn, names, _: [fn(n) for n in names]
    )
    with pytest.raises(CommandError, match="P failed"):
        call_command("sync_read_sources", fuente="azure", stdout=StringIO())
    assert azure_panel_store.read("P")[1] == [item(1)]
    assert azure_panel_store.read("Q")[1] == [item(2)]


def test_read_source_health_detects_missing_or_stale_panel(settings):
    settings.CLOCKIFY_WORKSPACE_ID = "w"
    ClockifyCatalog.objects.create(workspace_id="w", synced_at=timezone.now())
    project()
    # The old sources are absent as well; the new failure must be included.
    with pytest.raises(CommandError, match="sin panel sincronizado"):
        call_command("check_datastore", lecturas=True, stdout=StringIO())


def test_corrupt_source_header_preserves_valid_sheet_and_cache_revision():
    save_snapshot(
        "Historico_Proyectos", [["ID", "Delivery Manager"], ["P", "DM"]]
    )
    revision = DataRevision.objects.get(pk=1).version
    with pytest.raises(SnapshotValidationError, match="encabezado 2"):
        save_snapshot(
            "Historico_Proyectos", [["ID", "#REF! Array not expanded"]]
        )
    assert read_snapshot("Historico_Proyectos")[0] == ["ID", "Delivery Manager"]
    assert DataRevision.objects.get(pk=1).version == revision


def test_bad_header_rolls_back_the_entire_sheet_sync():
    from apps.datastore.services.sheet_sync import sync_sheets

    save_snapshot("MPB", [["ID"], ["before"]])
    revision = DataRevision.objects.get(pk=1).version
    repository = Mock()
    repository.sheet_exists.return_value = True
    repository.read_values.side_effect = [
        [["ID"], ["after"]],
        [["ID", "#REF! Array not expanded"]],
    ]
    with pytest.raises(SnapshotValidationError):
        sync_sheets(repository, ["MPB", "Historico_Proyectos"])
    assert read_snapshot("MPB") == [["ID"], ["before"]]
    assert DataRevision.objects.get(pk=1).version == revision


def test_production_azure_endpoint_uses_database_with_http_blocked(
    client, monkeypatch, settings
):
    settings.ROOT_URLCONF = "config.urls"
    settings.AZURE_STORE_ENABLED = True
    settings.CSP_ENFORCE = True
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "source-api-test",
            "KEY_FUNCTION": "core.data_cache.make_key",
        }
    }
    project()
    azure_panel_store.save("P", 1, [item(1)])
    azure = IxsAzure(
        "org", "pat", "P", lambda _: "P", Mock(), Mock(), lambda: {}, True
    )
    monkeypatch.setattr("apps.daily.ixs_rpc.build_ixs_azure", lambda: azure)
    monkeypatch.setattr(
        "requests.sessions.Session.request",
        Mock(side_effect=AssertionError("HTTP")),
    )
    response = client.get("/api/v1/screens/proyectos/P/azure/")
    assert response.status_code == 200
    assert response.json()["data"]["ok"] is True
    assert response.json()["data"]["allItems"][0]["id"] == 1
    assert "Content-Security-Policy" in response.headers


def test_warm_refresh_does_not_clear_config_or_session_cache(
    monkeypatch, settings
):
    from django.core.cache import cache

    from core.management.commands.warm_cache import Command

    settings.AZURE_STORE_ENABLED = True
    cache.set("daily:azure:active_project", "P")
    cache.set("session:person", "person")
    monkeypatch.setattr(
        cache, "clear", Mock(side_effect=AssertionError("Cache clear"))
    )
    monkeypatch.setattr(Command, "warm", Mock())
    call_command("warm_cache", refresh=True, stdout=StringIO())
    assert cache.get("daily:azure:active_project") == "P"
    assert cache.get("session:person") == "person"
    assert DataRevision.objects.get(pk=1).version == 1


def test_invalidating_one_project_keeps_the_other_local_panels():
    project()
    AzureProject.objects.create(name="Q", position=1, synced_at=timezone.now())
    azure_panel_store.save("P", 1, [item(1)])
    azure_panel_store.save("Q", 1, [item(2)])
    azure_panel_store.invalidate("P")
    assert azure_panel_store.read("P") is None
    assert azure_panel_store.read("Q")[1] == [item(2)]
    assert not AzureProject.objects.get(name="P").risk_fields_ok
    assert AzureProject.objects.get(name="Q").risk_fields_ok


def test_raid_cache_reset_does_not_discard_valid_database_data():
    azure_store.save_project("P", 0, ([], [item(1)], [], []), 4)
    # A cache reset returns its volatile version to zero.
    assert azure_store.read_raid("P", 0) == ([item(1)], [])
    azure_panel_store.invalidate("P")
    assert azure_store.read_raid("P", 0) is None


def test_ixs_risk_write_invalidates_the_resolved_project_only(
    settings, monkeypatch
):
    from apps.daily import ixs_rpc

    settings.AZURE_STORE_ENABLED = True
    project()
    AzureProject.objects.create(name="Q", position=1, synced_at=timezone.now())
    azure_panel_store.save("P", 1, [item(1)])
    azure_panel_store.save("Q", 1, [item(2)])
    azure = IxsAzure(
        "org", "pat", "Q", lambda _: "P", Mock(), Mock(), lambda: {}, True
    )
    monkeypatch.setattr(ixs_rpc, "build_ixs_azure", lambda: azure)
    monkeypatch.setattr(ixs_rpc.risk_form, "clear_work_item_cache", Mock())
    result = {"ok": True, "id": 3}
    monkeypatch.setattr(
        ixs_rpc.ixs_raid, "create_raid_record", lambda *_: result
    )
    assert ixs_rpc.create_raid_record("P_CR", "Risk", {}) == result
    assert azure_panel_store.read("P") is None
    assert azure_panel_store.read("Q")[1] == [item(2)]


@pytest.mark.parametrize("ok", [True, False])
def test_daily_risk_write_invalidates_only_after_success(
    settings, monkeypatch, ok
):
    from apps.daily import rpc

    settings.AZURE_STORE_ENABLED = True
    project()
    azure_panel_store.save("P", 1, [item(1)])
    azure = Mock()
    azure.connection.project = "P"
    monkeypatch.setattr(rpc, "build_daily_azure", lambda: azure)
    result = {"ok": ok, "id": 2}
    monkeypatch.setattr(
        rpc.risk_form, "create_risk_work_item", lambda *_: result
    )
    assert rpc.create_risk({}) == result
    assert (azure_panel_store.read("P") is None) is ok
