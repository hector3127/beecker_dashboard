"""Business Overview: lo que la pagina incrusta respeta el alcance."""

import pytest

from apps.access.scope import AccessScope
from apps.portal.services.executive_screen import scoped_snapshots

pytestmark = pytest.mark.django_db

FINANCIAL = {
    "loaded_at": "2026-10-22T10:00:00-06:00",
    "revenue": {"invoiced": 7_654_321},
    "commercial": {"won": 1},
    "opportunities": {"opportunities": [{"account": "Secreta"}]},
    "accounts": {
        "accounts": [
            {"name": "Acme", "revenue": 600, "url": "/cuenta/acme/"},
            {"name": "Beta", "revenue": 400, "pending": 1},
        ]
    },
}


def test_full_scope_keeps_the_cut_without_the_opportunity_detail():
    financial, operations = scoped_snapshots(
        FINANCIAL, {"etc": 5}, AccessScope.everything()
    )

    assert financial["revenue"] == FINANCIAL["revenue"]
    assert "opportunities" not in financial
    assert operations == {"etc": 5}


def test_limited_scope_gets_no_company_figures_and_only_its_accounts():
    financial, operations = scoped_snapshots(
        FINANCIAL, {"etc": 5}, AccessScope.limited(accounts=["Beta"])
    )

    assert set(financial) == {"loaded_at", "accounts"}
    assert [a["name"] for a in financial["accounts"]["accounts"]] == ["Beta"]
    assert financial["accounts"]["pending_accounts"] == 1
    assert operations == {}


def test_the_page_never_ships_other_accounts_or_company_totals(
    client, enforced, monkeypatch
):
    monkeypatch.setattr(
        "apps.portal.services.financial_cache.cached_financial_snapshot",
        lambda: FINANCIAL,
    )
    monkeypatch.setattr(
        "apps.portal.services.executive_operations.cached_operations_snapshot",
        lambda: {"etc": 5, "projects": []},
    )
    enforced(
        "ana",
        caps=frozenset({"view_executive", "view_agreements"}),
        scope=AccessScope.limited(accounts=["Beta"]),
    )

    page = client.get("/").content.decode()
    api = client.get("/api/v1/screens/executive/").content.decode()

    assert "Beta" in api
    for secret in ("Acme", "7654321", "Secreta"):
        assert secret not in page + api, secret


def test_the_page_needs_the_executive_capability(client, enforced):
    enforced("sin", caps=frozenset({"view_operations"}))

    assert client.get("/").status_code == 403
