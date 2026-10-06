import pytest

from apps.azure_devops.services.raid_cache import clear_raid_cache, read_raid
from core.exceptions import DashboardError


class DictStore:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value, timeout):
        self.data[key] = value


class FakeClient:
    def __init__(self, fields_error=None):
        self.item_calls = 0
        self.field_calls = 0
        self._fields_error = fields_error

    def list_raid_items(self, project):
        self.item_calls += 1

        return [{"id": 1, "project": project}]

    def list_risk_fields(self, project):
        self.field_calls += 1

        if self._fields_error:
            raise self._fields_error

        return [{"referenceName": "Custom.Field"}]


def test_second_read_comes_from_cache():
    store = DictStore()
    client = FakeClient()

    first = read_raid(store, "azure:v1:org", lambda: client, "GPO")
    second = read_raid(store, "azure:v1:org", lambda: client, "GPO")

    assert first == second
    assert client.item_calls == 1
    assert client.field_calls == 1


def test_each_project_has_its_own_entry():
    store = DictStore()
    client = FakeClient()

    read_raid(store, "p", lambda: client, "GPO")
    read_raid(store, "p", lambda: client, "AER")

    assert client.item_calls == 2


def test_clear_forces_a_new_download():
    store = DictStore()
    client = FakeClient()
    read_raid(store, "p", lambda: client, "GPO")

    clear_raid_cache(store)
    read_raid(store, "p", lambda: client, "GPO")

    assert client.item_calls == 2


def test_clear_twice_keeps_counting():
    store = DictStore()

    clear_raid_cache(store)
    clear_raid_cache(store)

    assert store.data["azure:v1:raid_version"] == 2


def test_missing_risk_fields_are_not_cached():
    store = DictStore()
    client = FakeClient(fields_error=DashboardError("sin permiso"))

    items, fields = read_raid(store, "p", lambda: client, "GPO")
    read_raid(store, "p", lambda: client, "GPO")

    assert items == [{"id": 1, "project": "GPO"}]
    assert fields == []
    assert client.item_calls == 2


def test_item_errors_propagate_and_are_not_cached():
    class Broken(FakeClient):
        def list_raid_items(self, project):
            raise DashboardError("Azure no responde")

    store = DictStore()

    with pytest.raises(DashboardError):
        read_raid(store, "p", lambda: Broken(), "GPO")

    assert store.data == {}
