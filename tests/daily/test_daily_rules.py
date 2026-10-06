import pytest

from apps.daily.exceptions import AzureConnectionError, AzureHttpError
from apps.daily.services import azure_config
from apps.daily.services.azure_connection import ConnectionStore
from apps.daily.services.daily_azure_client import DailyAzureClient
from apps.daily.services.daily_sheets import clamp_pct, js_string
from apps.daily.services.project_links import resolve_internal_project
from apps.daily.services.work_items import js_json
from tests.daily.fakes import FakeResponse, MemoryCache


def build_store(token="pat-1234"):
    return ConnectionStore(MemoryCache(), "beecker", token, "RAS.001")


def test_config_comes_from_env_and_only_project_changes():
    store = build_store()
    cache = MemoryCache()

    assert azure_config.save_azure_config(
        store,
        cache,
        ("otra", "AMK.008", ""),
    ) == {"ok": False, "error": azure_config.ENV_ONLY_MESSAGE}
    assert azure_config.save_azure_config(
        store,
        cache,
        ("beecker", "AMK.008", ""),
    ) == {"ok": True}
    assert azure_config.read_azure_config(store)["proyecto"] == "AMK.008"
    assert azure_config.read_azure_config(store)["global"] is True

    azure_config.disconnect_azure(store, cache)

    assert store.active_project() == "RAS.001"


def test_missing_token_messages():
    store = build_store(token="")
    cache = MemoryCache()

    assert (
        azure_config.save_azure_config(store, cache, ("beecker", "A", ""))[
            "error"
        ]
        == "Falta el Personal Access Token."
    )
    assert azure_config.change_active_project(store, cache, "A")["error"] == (
        "Primero conecta tu cuenta de Azure DevOps."
    )
    assert azure_config.list_saved_projects(store) == {
        "ok": True,
        "proyectos": [],
        "sinPAT": True,
    }


class StubSession:
    def __init__(self, response=None, error=None):
        self.headers = {}
        self.response = response
        self.error = error

    def request(self, *args, **kwargs):
        if self.error:
            raise self.error
        return self.response


def test_client_treats_203_as_error_and_wraps_network_errors():
    import requests

    client = DailyAzureClient(
        "org",
        "pat",
        session=StubSession(FakeResponse(203, "<html>")),
    )

    with pytest.raises(AzureHttpError) as error:
        client.list_projects()

    assert error.value.status_code == 203

    offline = DailyAzureClient(
        "org",
        "pat",
        session=StubSession(error=requests.ConnectionError("sin red")),
    )

    with pytest.raises(AzureConnectionError):
        offline.list_projects()


def test_resolve_internal_project_prefers_open_projects():
    rows = [
        {"ID_Proyecto": "RAS.001_S1", "Estado": "Cerrado"},
        {"ID_Proyecto": "RAS.001_S2", "Estado": "Development"},
    ]

    assert resolve_internal_project("RAS.001_S1", rows) == "RAS.001_S1"
    assert resolve_internal_project("RAS.001", rows) == "RAS.001_S2"
    assert resolve_internal_project("", rows) is None
    assert resolve_internal_project("XYZ", rows) is None


def test_small_helpers():
    assert clamp_pct("abc") == 0
    assert clamp_pct(-5) == 0
    assert clamp_pct(None) == 0
    assert js_string(None) == "null"
    assert js_json({"a": 1.0, "b": [2.5]}) == '{"a":1,"b":[2.5]}'
