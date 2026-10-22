"""API de Business Overview: contrato, permisos y alcance."""

import pytest

from apps.access.scope import AccessScope

pytestmark = pytest.mark.django_db

URL = "/api/v1/screens/executive/"
EXEC = frozenset({"view_executive"})
SNAPSHOT = {
    "loaded_at": "2026-10-22T10:00:00-06:00",
    "revenue": {"invoiced": 1000, "collections_percent": 80},
    "costs": {"cost": 400, "complete": True, "projects": []},
    "commercial": {"won": 500, "open": 200},
    "profitability": {"months": [], "complete": True},
    "opportunities": {"opportunities": [{"account": "Secreta"}]},
    "accounts": {
        "ranking_version": 4,
        "accounts": [
            {
                "name": "Acme",
                "revenue": 600,
                "gross_profit": 300,
                "margin": 50,
                "projects": 2,
            },
            {
                "name": "Beta",
                "revenue": 400,
                "gross_profit": 100,
                "margin": 25,
                "projects": 1,
                "pending": 1,
                "url": "/cuenta/beta/",
            },
        ],
    },
}
OPERATIONS = {"projects": [], "etc": 120, "advance": 40, "partial": False}


@pytest.fixture(autouse=True)
def cut(monkeypatch):
    monkeypatch.setattr(
        "apps.portal.services.financial_cache.cached_financial_snapshot",
        lambda: SNAPSHOT,
    )
    monkeypatch.setattr(
        "apps.portal.services.executive_operations.cached_operations_snapshot",
        lambda: OPERATIONS,
    )


def test_full_scope_gets_company_figures_and_every_account(client):
    body = client.get(URL).json()
    data = body["data"]

    assert data["finance"]["revenue"]["invoiced"] == 1000
    assert data["operations"]["etc"] == 120
    assert data["commercial"]["won"] == 500
    assert [a["name"] for a in data["accounts"]] == ["Acme", "Beta"]
    assert data["accounts"][1] == {
        "name": "Beta",
        "slug": "beta",
        "revenue": 400,
        "gross_profit": 100,
        "margin": 25,
        "projects": 1,
        "partial": True,
    }
    assert body["meta"]["blocks"] == {
        "financial": True,
        "operations": True,
        "commercial": True,
        "accounts": True,
    }


def test_opportunity_detail_never_travels_with_the_overview(client):
    assert "Secreta" not in client.get(URL).content.decode()


def test_limited_scope_gets_its_accounts_and_no_company_figures(
    client, enforced
):
    enforced("ana", caps=EXEC, scope=AccessScope.limited(accounts=["Beta"]))

    body = client.get(URL).json()
    data = body["data"]

    assert [a["name"] for a in data["accounts"]] == ["Beta"]
    for block in ("finance", "operations", "commercial", "monthly"):
        assert data[block] is None, block
    assert body["meta"]["scope"] == "limited"
    text = client.get(URL).content.decode()
    assert "1000" not in text and "Acme" not in text


def test_a_block_not_prepared_yet_is_null_not_zero(client, monkeypatch):
    monkeypatch.setattr(
        "apps.portal.services.financial_cache.cached_financial_snapshot",
        lambda: {},
    )
    monkeypatch.setattr(
        "apps.portal.services.executive_operations.cached_operations_snapshot",
        lambda: {},
    )

    body = client.get(URL).json()

    assert body["data"]["finance"] is None
    assert body["data"]["accounts"] is None
    assert body["meta"]["blocks"]["financial"] is False


def test_the_capability_is_required(client, enforced):
    enforced("sin", caps=frozenset({"view_operations"}))

    assert client.get(URL).status_code == 403


def test_an_invalid_period_is_a_400(client):
    assert client.get(URL, {"periodo": "siglo"}).status_code == 400


def test_refresh_reports_state_and_which_blocks_exist(client, monkeypatch):
    from apps.portal.services import executive_refresh

    monkeypatch.setattr(
        executive_refresh, "refresh_status", lambda: {"state": "running"}
    )
    monkeypatch.setattr(
        executive_refresh,
        "request_refresh",
        lambda force=False: {"state": "queued", "partial": True},
    )

    status = client.get(URL + "actualizar/").json()["data"]
    started = client.post(URL + "actualizar/").json()["data"]

    assert status["state"] == "running"
    assert started["state"] == "queued" and started["partial"] is True
    assert status["blocks"] == {
        "financial": True,
        "commercial": True,
        "operations": True,
    }


def test_refresh_needs_the_capability(client, enforced):
    enforced("sin", caps=frozenset({"view_operations"}))

    assert client.post(URL + "actualizar/").status_code == 403
