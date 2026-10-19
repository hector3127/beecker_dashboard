from io import StringIO

import pytest
from django.core.cache import cache
from django.core.management import call_command

from apps.azure_devops.exceptions import AzureDevOpsRequestError
from apps.azure_devops.gateway import AzureDevOpsGateway
from apps.azure_devops.services import raid_cache
from apps.datastore.models import AzureProject, AzureWorkItem
from apps.datastore.services import azure_store
from apps.datastore.services.azure_sync import sync_azure
from core.exceptions import DashboardError

pytestmark = pytest.mark.django_db


def item(item_id, kind="Task", state="Active", assigned="Ana Ruiz", **fields):
    return {
        "id": item_id,
        "rev": 3,
        "fields": {
            "System.Id": item_id,
            "System.WorkItemType": kind,
            "System.State": state,
            "System.Title": f"Item {item_id}",
            "System.IterationPath": "P\\Sprint 1",
            "System.AssignedTo": {"displayName": assigned, "url": "x"},
            "System.ChangedDate": "2026-10-01T15:30:00.5Z",
            **fields,
        },
    }


ITERATION = {
    "nombre": "Sprint 1",
    "path": "P\\Sprint 1",
    "fechaInicio": "2026-09-01T00:00:00Z",
    "fechaFin": "2026-09-14T00:00:00Z",
}
FIELDS = [
    {"name": "Severity", "referenceName": "Microsoft.VSTS.Common.Severity"}
]


def save(name="P", position=0, version=0, ok=True, **data):
    save_data = (
        data.get("items", [item(2), item(1)]),
        data.get("raid", [item(9, "Risk")]),
        data.get("fields", FIELDS),
        data.get("iterations", [ITERATION]),
    )
    azure_store.save_project(name, position, save_data, version, ok)


def test_what_is_read_is_exactly_what_azure_returned_in_the_same_order():
    save()
    assert [i["id"] for i in azure_store.read_work_items("P")] == [2, 1]
    assert azure_store.read_work_items("P")[0] == item(2)
    assert azure_store.read_iterations("P") == [ITERATION]
    assert azure_store.read_raid("P", 0) == ([item(9, "Risk")], FIELDS)
    assert azure_store.read_project_names() == ["P"]


def test_columns_make_the_work_items_queryable():
    save()
    row = AzureWorkItem.objects.get(work_item_id=9)
    assert (row.kind, row.item_type, row.state) == ("raid", "Risk", "Active")
    assert row.assigned_to == "Ana Ruiz"
    assert row.iteration_path == "P\\Sprint 1"
    assert row.changed_at.year == 2026 and row.changed_at.month == 10
    assert AzureWorkItem.objects.filter(kind="latest").count() == 2


def test_saving_again_replaces_the_previous_copy():
    save(items=[item(1), item(2), item(3)])
    save(items=[item(7)], raid=[], iterations=[])
    assert [i["id"] for i in azure_store.read_work_items("P")] == [7]
    assert azure_store.read_iterations("P") == []
    assert AzureProject.objects.count() == 1


def test_unknown_projects_are_not_in_the_store():
    assert azure_store.read_work_items("nadie") is None
    assert azure_store.read_iterations("nadie") is None
    assert azure_store.read_raid("nadie", 0) is None
    assert azure_store.read_project_names() is None
    assert azure_store.has_project("nadie") is False


def test_raid_is_ignored_when_the_app_created_a_record_after_the_sync():
    save(version=4)
    assert azure_store.read_raid("P", 4) is not None
    assert azure_store.read_raid("P", 5) is None


def test_raid_is_ignored_when_the_risk_fields_could_not_be_read():
    save(ok=False, fields=[])
    assert azure_store.read_raid("P", 0) is None
    # Los work items y las iteraciones si se pueden usar.
    assert azure_store.read_work_items("P") is not None


def test_projects_that_left_the_organization_are_dropped():
    save("A", 0)
    save("B", 1)
    assert azure_store.drop_projects_except(["A"]) == 1
    assert azure_store.read_project_names() == ["A"]
    assert not AzureWorkItem.objects.filter(project__name="B").exists()


class FakeClient:
    def __init__(self, projects, fail=(), no_fields=()):
        self.projects = projects
        self.fail = set(fail)
        self.no_fields = set(no_fields)
        self.calls = []

    def list_project_names(self):
        return list(self.projects)

    def list_work_items(self, name):
        self.calls.append(("work_items", name))
        if name in self.fail:
            raise AzureDevOpsRequestError("Azure respondio 500.")
        return self.projects[name]["items"]

    def list_raid_items(self, name):
        return self.projects[name].get("raid", [])

    def list_risk_fields(self, name):
        if name in self.no_fields:
            raise AzureDevOpsRequestError("sin campos")
        return FIELDS

    def list_iterations(self, name):
        return [ITERATION]


class FakeGateway:
    def __init__(self, client):
        self.client = client

    def create_client(self):
        return self.client


def test_sync_saves_every_project_and_reports_counts():
    client = FakeClient(
        {
            "A": {"items": [item(1), item(2)], "raid": [item(5, "Risk")]},
            "B": {"items": [item(3)]},
        }
    )
    result = sync_azure(FakeGateway(client))
    assert (result.projects, result.work_items, result.iterations) == (2, 4, 2)
    assert azure_store.read_project_names() == ["A", "B"]
    assert result.failed == [] and result.removed == 0


def test_a_failing_project_keeps_its_previous_copy_and_is_reported():
    save("A", 0, items=[item(1)])
    client = FakeClient(
        {"A": {"items": [item(99)]}, "B": {"items": [item(3)]}}, fail=["A"]
    )
    result = sync_azure(FakeGateway(client))
    assert result.projects == 1
    assert result.failed == ["A: Azure respondio 500."]
    assert [i["id"] for i in azure_store.read_work_items("A")] == [1]
    assert azure_store.read_work_items("B") is not None


def test_missing_risk_fields_are_reported_but_the_project_is_still_saved():
    client = FakeClient({"A": {"items": [item(1)]}}, no_fields=["A"])
    result = sync_azure(FakeGateway(client))
    assert result.no_risk_fields == ["A"]
    assert azure_store.read_raid("A", 0) is None
    assert azure_store.read_work_items("A") is not None


def test_only_a_full_sync_removes_projects_that_no_longer_exist():
    save("viejo", 5)
    client = FakeClient({"A": {"items": [item(1)]}})
    sync_azure(FakeGateway(client), only=["A"])
    assert azure_store.has_project("viejo")
    result = sync_azure(FakeGateway(client))
    assert result.removed == 1 and not azure_store.has_project("viejo")


@pytest.fixture
def gateway(settings):
    settings.AZURE_DEVOPS_ORGANIZATION = "org"
    settings.AZURE_DEVOPS_PAT = "token"
    settings.AZURE_STORE_ENABLED = True
    cache.clear()
    yield AzureDevOpsGateway()
    cache.clear()


class LiveClient:
    def __init__(self):
        self.calls = []

    def list_project_names(self):
        self.calls.append("names")
        return ["vivo"]

    def list_work_items(self, name):
        self.calls.append("work_items")
        return [item(50)]

    def list_iterations(self, name):
        self.calls.append("iterations")
        return [{"nombre": "vivo", "path": "vivo"}]

    def list_raid_items(self, name):
        self.calls.append("raid")
        return [item(51, "Risk")]

    def list_risk_fields(self, name):
        return FIELDS


@pytest.fixture
def live(monkeypatch):
    client = LiveClient()
    monkeypatch.setattr(
        AzureDevOpsGateway, "_build_client", lambda self: client
    )
    return client


def test_the_gateway_reads_the_store_without_calling_azure(gateway, live):
    save("P")
    assert gateway.list_project_names() == ["P"]
    assert [i["id"] for i in gateway.list_work_items("P")] == [2, 1]
    assert gateway.list_iterations("P") == [ITERATION]
    assert gateway.list_raid("P") == ([item(9, "Risk")], FIELDS)
    assert live.calls == []


def test_a_project_that_is_not_stored_is_read_live(gateway, live):
    save("P")
    assert [i["id"] for i in gateway.list_work_items("otro")] == [50]
    assert live.calls == ["work_items"]


def test_force_refresh_of_iterations_goes_to_azure(gateway, live):
    save("P")
    assert (
        gateway.list_iterations("P", force_refresh=True)[0]["nombre"] == "vivo"
    )
    assert live.calls == ["iterations"]


def test_creating_a_risk_makes_the_stored_raid_read_live_again(gateway, live):
    save("P", version=raid_cache.read_version(cache))
    assert gateway.list_raid("P")[0][0]["id"] == 9 and live.calls == []
    raid_cache.clear_raid_cache(cache)
    assert gateway.list_raid("P")[0][0]["id"] == 51
    assert "raid" in live.calls


def test_with_the_store_off_nothing_is_read_from_the_database(
    gateway, live, settings
):
    save("P")
    settings.AZURE_STORE_ENABLED = False
    assert gateway.list_project_names() == ["vivo"]
    assert live.calls == ["names"]


def test_prefetch_only_loads_the_projects_that_are_not_stored(gateway, live):
    save("P")
    gateway.prefetch(["P", "otro"], include_iterations=False)
    assert live.calls == ["work_items"]


def test_the_command_skips_azure_when_it_is_not_configured(settings):
    settings.AZURE_DEVOPS_ORGANIZATION = ""
    settings.AZURE_DEVOPS_PAT = ""
    out = StringIO()
    call_command("sync_datastore", "--solo-azure", stdout=out)
    assert "omitido" in out.getvalue()


def test_the_command_reports_a_dashboard_error_as_a_failure(
    settings, monkeypatch
):
    settings.AZURE_DEVOPS_ORGANIZATION = "org"
    settings.AZURE_DEVOPS_PAT = "token"

    def boom(gateway):
        raise DashboardError("sin red")

    monkeypatch.setattr(
        "apps.datastore.management.commands.sync_datastore.sync_azure", boom
    )
    with pytest.raises(Exception, match="sin red"):
        call_command("sync_datastore", "--solo-azure", stdout=StringIO())
