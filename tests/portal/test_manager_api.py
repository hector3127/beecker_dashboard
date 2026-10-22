"""API del Delivery Manager: contrato, pasos, permisos y alcance."""

import pytest
from django.core.cache import cache

from apps.access.scope import AccessScope
from apps.portal import views
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva_loader import Eva1Load
from tests.portal.test_views import portfolio, stub_portfolio

pytestmark = pytest.mark.django_db

URL = "/api/v1/screens/delivery-managers/alberto/"
OPS = frozenset({"view_operations"})


@pytest.fixture(autouse=True)
def sources(monkeypatch):
    cache.clear()
    stub_portfolio(monkeypatch, portfolio())
    monkeypatch.setattr(
        views,
        "load_eva1",
        lambda *a, **k: Eva1Load(view=build_eva1_view([]), error=""),
    )
    yield
    cache.clear()


def data(client, **params):
    response = client.get(URL, params)
    assert response.status_code == 200
    return response.json()["data"]


def test_base_has_the_summary_and_rows_with_pending_blocks(client):
    body = data(client)

    assert body["name"] == "Alberto"
    assert body["summary"]["total"] == 2
    assert {r["project_id"] for r in body["rows"]} == {"2", "3"}
    assert body["investment"]["state"] == "pending"
    assert body["investment"]["commercial"] is None  # pendiente no es cero
    assert body["hours"] == {
        "state": "pending",
        "complete": False,
        "error": "",
        "months": [],
        "has_data": False,
    }


def test_rows_expose_named_fields_and_the_account_link(client):
    row = next(r for r in data(client)["rows"] if r["project_id"] == "2")

    assert row["client"] == "Clinica Sur"
    assert row["account_slug"] == "clinica-sur"
    assert row["status_code"] == "r"
    assert isinstance(row["risk"], str)


def test_late_and_over_budget_projects_say_why(client):
    rows = {r["project_id"]: r for r in data(client)["rows"]}

    assert rows["2"]["detail"] == "12 días de vencido"
    assert rows["3"]["detail"] == "Presupuesto usado: 125%"


def test_unknown_stage_is_a_400(client):
    assert client.get(URL, {"bloque": "todo"}).status_code == 400


def test_an_unknown_manager_does_not_exist(client):
    assert (
        client.get("/api/v1/screens/delivery-managers/nadie/").status_code
        == 404
    )


def test_unreadable_sources_without_a_manager_are_a_502(client, monkeypatch):
    stub_portfolio(monkeypatch, error="Falta configurar el dashboard.")
    cache.clear()

    response = client.get("/api/v1/screens/delivery-managers/nadie/")

    assert response.status_code == 502
    assert response.json()["error"]["code"] == "upstream"


# ---------- Permisos y alcance ----------


def test_without_operations_nothing_is_read(client, enforced, monkeypatch):
    enforced("sin", caps=frozenset({"view_costs"}))
    monkeypatch.setattr(views, "_dm_base", lambda *a: pytest.fail("fuentes"))

    assert client.get(URL).status_code == 403


def test_limited_scope_sees_only_its_accounts_projects(client, enforced):
    enforced(
        "ana", caps=OPS, scope=AccessScope.limited(accounts=["Clinica Sur"])
    )

    body = data(client)

    assert [r["project_id"] for r in body["rows"]] == ["2"]
    assert body["summary"]["total"] == 1


def test_a_manager_with_no_visible_project_does_not_exist(client, enforced):
    enforced("ana", caps=OPS, scope=AccessScope.limited(accounts=["Otra"]))

    assert client.get(URL).status_code == 404


def test_each_scope_has_its_own_cached_cut(client, enforced):
    enforced(
        "ana", caps=OPS, scope=AccessScope.limited(accounts=["Clinica Sur"])
    )
    data(client)
    enforced("beto", caps=OPS)

    assert data(client)["summary"]["total"] == 2
