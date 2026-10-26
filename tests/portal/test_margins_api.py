"""API y pagina de la comparativa de margenes: contrato, permisos y alcance."""

from datetime import date

import pytest

from apps.access.scope import AccessScope
from apps.portal.services import executive_refresh
from apps.portal.services import opportunity_profitability as opp
from tests.portal.test_opportunity_profitability import reader

pytestmark = pytest.mark.django_db

URL = "/api/v1/screens/margenes/"
COSTS = frozenset({"view_costs"})
RANGE = {"periodo": "rango", "desde": "2026-01-01", "hasta": "2026-12-31"}


@pytest.fixture(autouse=True)
def sources(monkeypatch):
    """Dos oportunidades de cuentas distintas; ninguna fuente real."""
    from django.core.cache import cache

    cache.clear()
    monkeypatch.setattr(opp.timezone, "localdate", lambda: date(2026, 10, 22))
    monkeypatch.setattr(executive_refresh, "request_refresh", lambda **k: None)
    monkeypatch.setattr(
        opp,
        "build_sheet_repository",
        lambda: reader(
            [
                "Confirmed",
                "Acme",
                "OP.1",
                "RaaS",
                "A1",
                0,
                "2026-03-01",
                100,
                "60%",
            ],
            [
                "Collected",
                "Beta",
                "OP.2",
                "RaaS",
                "B1",
                0,
                "2026-04-01",
                50,
                "40%",
            ],
        ),
    )


def rows(client, **params):
    response = client.get(URL, {**RANGE, **params})
    assert response.status_code == 200
    return {o["name"]: o for o in response.json()["data"]["opportunities"]}


def test_contract_separates_bookings_operated_invoiced_and_collected(client):
    row = rows(client)["OP.2"]

    assert row["bookings"] == 50
    assert row["period_revenue"] == 50
    assert (row["operated_revenue"], row["invoiced"], row["collected"]) == (
        50,
        50,
        50,
    )
    # El dato operado declara de donde sale mientras Finanzas no lo valide.
    assert row["operated_revenue_status"] == "assumed_service_date_g"


def test_sold_cost_rate_is_pending_and_never_computed(client):
    for row in rows(client).values():
        assert row["sold_cost_rate"] == {
            "value": None,
            "status": "pending_validation",
        }


def test_meta_tells_the_period_and_the_exclusions(client):
    meta = client.get(URL, RANGE).json()["meta"]

    assert (meta["start"], meta["end"]) == ("2026-01-01", "2026-12-31")
    assert meta["excluded"] == "Licencias, SaaS y servicios especializados"
    assert meta["account"] is None


def test_account_filter_keeps_only_that_account(client):
    assert set(rows(client, nombre="Acme")) == {"OP.1"}
    accounts = client.get(URL, {**RANGE, "nombre": "Acme"}).json()["data"][
        "accounts"
    ]
    assert [a["account"] for a in accounts] == ["Acme"]
    assert accounts[0]["period_revenue"] == 100


def test_invalid_period_is_a_400(client):
    assert (
        client.get(URL, {"periodo": "rango", "desde": "x"}).status_code == 400
    )
    assert client.get(URL, {"periodo": "siglo"}).status_code == 400


# ---------- Permisos y alcance ----------


def test_without_costs_capability_nothing_is_read(
    client, enforced, monkeypatch
):
    enforced("sin", caps=frozenset({"view_operations"}))
    monkeypatch.setattr(opp, "build_sheet_repository", lambda: pytest.fail())

    response = client.get(URL, RANGE)

    assert response.status_code == 403
    assert "OP." not in response.content.decode()


def test_anonymous_is_refused_when_enforced(client, enforced):
    assert client.get(URL, RANGE).status_code == 403


def test_limited_scope_only_sees_its_accounts(client, enforced):
    enforced("ana", caps=COSTS, scope=AccessScope.limited(accounts=["Beta"]))

    assert set(rows(client)) == {"OP.2"}
    accounts = client.get(URL, RANGE).json()["data"]["accounts"]
    assert [a["account"] for a in accounts] == ["Beta"]
    assert accounts[0]["period_revenue"] == 50


def test_account_outside_scope_does_not_exist(client, enforced):
    enforced("ana", caps=COSTS, scope=AccessScope.limited(accounts=["Beta"]))

    assert client.get(URL, {**RANGE, "nombre": "Acme"}).status_code == 404


def test_summary_is_computed_from_the_visible_rows_only(client, enforced):
    enforced("ana", caps=COSTS, scope=AccessScope.limited(accounts=["Beta"]))

    summary = client.get(URL, RANGE).json()["data"]["summary"]

    assert summary["total"] == 1


# ---------- Costos por proyecto y actualizacion ----------


def test_project_cost_requires_an_id(client):
    assert client.get("/api/v1/costs/project/").status_code == 400


def test_project_cost_is_refused_without_costs_capability(client, enforced):
    enforced("sin", caps=frozenset({"view_operations"}))

    response = client.get(
        "/api/v1/costs/project/", {"id": "A1", "nombre": "Acme"}
    )

    assert response.status_code == 403


def test_project_cost_of_a_foreign_account_is_a_404(client, enforced):
    enforced("ana", caps=COSTS, scope=AccessScope.limited(accounts=["Beta"]))

    response = client.get(
        "/api/v1/costs/project/", {"id": "A1", "nombre": "Acme"}
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_refresh_reports_state_without_reading_sources(client, monkeypatch):
    monkeypatch.setattr(
        executive_refresh, "request_refresh", lambda **k: {"state": "queued"}
    )
    monkeypatch.setattr(
        executive_refresh, "refresh_status", lambda: {"state": "running"}
    )

    started = client.post(URL + "actualizar/", content_type="application/json")
    status = client.get(URL + "actualizar/")

    assert started.json()["data"]["state"] == "queued"
    assert status.json()["data"]["state"] == "running"


# ---------- Pagina ----------


def test_page_for_a_foreign_account_is_a_404(client, enforced):
    enforced("ana", caps=COSTS, scope=AccessScope.limited(accounts=["Beta"]))

    assert (
        client.get("/ejecutiva/oportunidades/", {"nombre": "Acme"}).status_code
        == 404
    )


def test_page_without_costs_capability_is_forbidden(client, enforced):
    enforced("sin", caps=frozenset({"view_operations"}))

    assert client.get("/ejecutiva/oportunidades/").status_code == 403
