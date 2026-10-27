"""Lecturas iniciales del proyecto: contratos y permisos iguales al RPC."""

from unittest.mock import Mock

import pytest

from apps.access.scope import AccessScope
from apps.portal.api import project_detail as api
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/proyectos/"
SOURCES = [
    ("filtros/", "get_available_filters", ()),
    ("AER.001/ejecutivo/", "get_executive_dashboard", ("AER.001",)),
    ("AER.001/aer/", "aer_dashboard", ("AER.001",)),
    (
        "AER.001/aer/registros/?desde=2026-10-01&hasta=2026-10-24",
        "aer_records_dashboard",
        ("AER.001", "2026-10-01", "2026-10-24"),
    ),
    ("AMK.008/raid/", "get_project_raid", ("AMK.008",)),
    ("AMK.008/tasks/", "tasks_dashboard", ("AMK.008",)),
    ("AMK.008/clockify-rango/", "clockify_range", ("AMK.008",)),
    ("AMK.008/etapas/", "stages_dashboard", ("AMK.008",)),
    ("AMK.008/recursos/", "resources_dashboard", ("AMK.008",)),
    ("AMK.008/registros/", "records_dashboard", ("AMK.008",)),
    ("AMK.008/planeacion/", "planning_dashboard", ("AMK.008",)),
    ("AMK.008/planeacion/azure/", "get_ixs_panel", ("AMK.008", False)),
]


@pytest.mark.parametrize("suffix,source,args", SOURCES)
@pytest.mark.parametrize(
    "payload",
    [
        {"proyecto": {"id": "AER.001"}, "horas": 23.75, "cerrado": True},
        {"ok": False, "error": "Sin Clockify."},
    ],
)
def test_same_payload(client, monkeypatch, suffix, source, args, payload):
    load = Mock(return_value=payload)
    monkeypatch.setattr(api, source, load)
    response = client.get(BASE + suffix)
    assert response.status_code == 200
    assert response.json() == {"data": payload, "meta": {}}
    load.assert_called_once_with(*args)
    assert client.post(BASE + suffix).status_code == 405


@pytest.mark.parametrize("suffix,source,args", SOURCES)
@pytest.mark.parametrize("grant", ["anonymous", "wrong", "limited"])
def test_no_sources_without_rpc_scope(
    client, enforced, monkeypatch, suffix, source, args, grant
):
    load = Mock(side_effect=AssertionError("Source called without scope"))
    monkeypatch.setattr(api, source, load)
    enforced(
        "Ana",
        caps=frozenset(
            {"view_costs"} if grant == "wrong" else {"view_operations"}
        ),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()
    assert client.get(BASE + suffix).status_code in {401, 403}
    load.assert_not_called()


@pytest.mark.parametrize("suffix,source,args", SOURCES)
def test_full_scope_and_source_error(
    client, enforced, monkeypatch, suffix, source, args
):
    enforced("Ana", caps=frozenset({"view_operations"}))
    monkeypatch.setattr(api, source, Mock(side_effect=SheetsError("secret")))
    response = client.get(BASE + suffix)
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "ERR_SHEETS"
    assert "secret" not in response.content.decode()


def test_exact_cr_id(client, monkeypatch):
    source = Mock(return_value={"proyecto": None})
    monkeypatch.setattr(api, "get_executive_dashboard", source)
    assert client.get(BASE + "CCO.001%20%7C%20CR/ejecutivo/").status_code == 200
    source.assert_called_once_with("CCO.001 | CR")


def test_aer_uses_same_store_hours_and_builder(monkeypatch):
    store, hours = object(), object()
    monkeypatch.setattr(api.aer, "build_store", lambda: store)
    load_hours = Mock(return_value=hours)
    monkeypatch.setattr(api.aer, "build_hours", load_hours)
    build = Mock(return_value={"ok": True, "kpis": {"burn": 12.25}})
    monkeypatch.setattr(api.dashboard, "build_dashboard", build)
    assert api.aer_dashboard("AER.001") == build.return_value
    load_hours.assert_called_once_with(store)
    build.assert_called_once_with(store, "AER.001", hours)


def test_aer_records_keep_provider_exact_id_and_range(client, monkeypatch):
    store, hours = object(), object()
    monkeypatch.setattr(api.aer, "build_store", lambda: store)
    load = Mock(return_value=hours)
    monkeypatch.setattr(api.aer, "build_hours", load)
    records = Mock(return_value={"ok": True, "total": 0, "registros": []})
    monkeypatch.setattr(api.dashboard, "entries_in_range", records)
    response = client.get(
        BASE + "AER.001%20%7C%20CR/aer/registros/",
        {"desde": "2026-10-01", "hasta": "2026-10-24", "idProyecto": "OTRO"},
    )
    assert response.status_code == 200
    assert response.json()["data"] == records.return_value
    load.assert_called_once_with(store)
    records.assert_called_once_with(
        "AER.001 | CR", ("2026-10-01", "2026-10-24"), hours
    )


def test_aer_records_missing_dates_still_use_service_validation(
    client, monkeypatch
):
    load = Mock(return_value={"ok": False, "error": "Selecciona fechas"})
    monkeypatch.setattr(api, "aer_records_dashboard", load)
    response = client.get(BASE + "AER.001/aer/registros/")
    assert response.json()["data"]["ok"] is False
    load.assert_called_once_with("AER.001", "", "")


def test_active_entry_and_comparison(client, monkeypatch, reference_site):
    current = client.get(
        "/proyectos/CCO.001%20%7C%20CR/?volver=%2Foperativa%2F"
    )
    assert "pages/project_detail.html" in [t.name for t in current.templates]
    assert "csrftoken" in current.cookies
    html = current.content.decode()
    assert "app/scripts/pages/project_detail/main.js" in html
    assert '"id": "CCO.001 | CR"' in html
    previous = client.get("/proyectos/CCO.001/?vista=anterior")
    assert "portal/proyecto_detalle.html" in [
        t.name for t in previous.templates
    ]


@pytest.mark.parametrize(
    "service,wrapper",
    [
        ("tasks_summary", "tasks_dashboard"),
        ("project_stages", "stages_dashboard"),
        ("project_entries", "records_dashboard"),
        ("project_range", "clockify_range"),
    ],
)
def test_clockify_wrappers_keep_repository_and_exact_id(
    monkeypatch, service, wrapper
):
    repository = object()
    monkeypatch.setattr(api, "build_sheet_repository", lambda: repository)
    source = Mock(return_value={"ok": True, "horas": 12.75})
    monkeypatch.setattr(api.project_rpc, service, source)
    assert getattr(api, wrapper)("CCO.001 | CR") == source.return_value
    source.assert_called_once_with(repository, "CCO.001 | CR")


def test_resources_keep_same_store_and_exact_id(monkeypatch):
    store = object()
    monkeypatch.setattr(api, "build_store_sheets", lambda: store)
    source = Mock(return_value={"ok": True, "filas": []})
    monkeypatch.setattr(api, "read_resources", source)
    assert api.resources_dashboard("CCO.001_S1") == source.return_value
    source.assert_called_once_with(store, "CCO.001_S1")
