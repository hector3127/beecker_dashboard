"""API de la cuenta: contrato, permisos y alcance."""

import pytest

from apps.access.scope import AccessScope
from apps.portal.services import account_screen

pytestmark = pytest.mark.django_db

URL = "/api/v1/screens/cuenta/"
OPS = frozenset({"view_operations"})
COSTS = frozenset({"view_costs"})
VIEW = {
    "ok": True,
    "cliente": "Clinica Sur",
    "fechaCorte": "2026-10-22",
    "nps": 8,
    "npsMuestra": 1,
    "rocActivos": 2,
    "mpbPendientes": 1,
    "proyectos": [
        {
            "id": "P1",
            "nombre": "Portal",
            "servicio": "RaaS",
            "etapa": "Completed",
            "estado": "Producción",
            "deliveryManager": "Ana",
            "budget": 100,
            "burn": None,
            "nps": 8,
            "clockifyPending": True,
            "excedido": False,
            "atrasado": False,
            "campoInterno": "no sale",
        }
    ],
    "roc": [
        {
            "proceso": "Altas",
            "botId": "B1",
            "servicio": "RPA",
            "estado": "Activo",
        }
    ],
    "oportunidades": [
        {"account": "Clinica Sur", "name": "OP.7", "stage": "Won"}
    ],
}


@pytest.fixture(autouse=True)
def source(monkeypatch):
    monkeypatch.setattr(account_screen, "get_account_view", lambda c: VIEW)
    monkeypatch.setattr(
        account_screen,
        "get_account_consumption",
        lambda c, offset, limit, ids: {
            "ok": True,
            "items": [{"id": "P1", "burn": 12.5}],
            "next": 1,
            "total": 1,
        },
    )
    monkeypatch.setattr(
        "apps.portal.services.account_profitability.load_account_profitability",
        lambda: {
            "accounts": [{"name": "Clinica Sur", "revenue": 10, "margin": 40}]
        },
    )


def test_contract_exposes_named_fields_only(client):
    body = client.get(URL, {"nombre": "Clinica Sur"}).json()
    data = body["data"]

    assert data["available"] is True
    assert (data["nps"], data["nps_sample"], data["roc_active"]) == (8, 1, 2)
    [project] = data["projects"]
    assert project["manager"] == "Ana"
    assert project["clockify_pending"] is True
    assert "campoInterno" not in project
    assert data["roc"][0]["process"] == "Altas"
    assert data["opportunities"][0]["name"] == "OP.7"
    assert body["meta"] == {"client": "Clinica Sur", "cutoff": "2026-10-22"}


def test_an_unreadable_account_is_available_false_with_the_reason(
    client, monkeypatch
):
    monkeypatch.setattr(
        account_screen,
        "get_account_view",
        lambda c: {"ok": False, "error": "Sin Sheets"},
    )

    data = client.get(URL, {"nombre": "X"}).json()["data"]

    assert data == {"available": False, "error": "Sin Sheets"}


def test_the_account_name_is_required(client):
    assert client.get(URL).status_code == 400


def test_consumption_batches_keep_their_shape(client):
    body = client.get(URL + "consumos/", {"nombre": "Clinica Sur"}).json()

    assert body["data"]["items"] == [{"id": "P1", "burn": 12.5, "error": ""}]
    assert body["data"]["next"] == 1


def test_finance_returns_the_account_or_null(client):
    url = URL + "finanzas/"
    own = client.get(url, {"nombre": "Clinica Sur"}).json()["data"]["account"]
    other = client.get(url, {"nombre": "Otra"}).json()["data"]["account"]

    assert own["revenue"] == 10 and "name" not in own
    assert other is None


# ---------- Permisos y alcance ----------


def test_without_operations_or_agreements_nothing_is_read(
    client, enforced, monkeypatch
):
    enforced("sin", caps=COSTS)
    monkeypatch.setattr(account_screen, "get_account_view", lambda c: 1 / 0)

    assert client.get(URL, {"nombre": "Clinica Sur"}).status_code == 403


def test_agreements_only_person_can_read_the_account(client, enforced):
    enforced("ana", caps=frozenset({"view_agreements"}))

    assert client.get(URL, {"nombre": "Clinica Sur"}).status_code == 200


def test_foreign_account_is_a_404_in_every_endpoint(client, enforced):
    enforced(
        "ana",
        caps=OPS | COSTS,
        scope=AccessScope.limited(accounts=["Otra"]),
    )

    for path in ("", "consumos/", "finanzas/"):
        response = client.get(URL + path, {"nombre": "Clinica Sur"})
        assert response.status_code == 404, path


def test_finance_needs_the_costs_capability(client, enforced):
    enforced("ana", caps=OPS)

    assert (
        client.get(URL + "finanzas/", {"nombre": "Clinica Sur"}).status_code
        == 403
    )
