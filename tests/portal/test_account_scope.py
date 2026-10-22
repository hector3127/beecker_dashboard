"""La cuenta y sus datos financieros respetan el alcance de la persona."""

import pytest

from apps.access.scope import AccessScope
from tests.portal.test_views import portfolio, stub_portfolio

pytestmark = pytest.mark.django_db

OPS = frozenset({"view_operations"})
COSTS = frozenset({"view_costs"})


@pytest.fixture(autouse=True)
def account_data(monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    monkeypatch.setattr(
        "apps.ejecutivo.account_rpc.get_account_view",
        lambda name: {"ok": True, "proyectos": []},
    )
    monkeypatch.setattr(
        "apps.portal.services.account_profitability.load_account_profitability",
        lambda: {"accounts": [{"name": "Clinica Sur"}]},
    )


def test_own_account_opens(client, enforced):
    enforced("ana", OPS, AccessScope.limited(accounts=["Clinica Sur"]))

    response = client.get("/cuenta/clinica-sur/?nombre=Clinica+Sur")

    assert response.status_code == 200


def test_foreign_account_does_not_exist_even_with_its_name(client, enforced):
    enforced("ana", OPS, AccessScope.limited(accounts=["Otra"]))

    for url in (
        "/cuenta/clinica-sur/",
        "/cuenta/clinica-sur/?nombre=Clinica+Sur",
        "/cuenta/clinica-sur/?nombre=Clinica+Sur&bloque=consumos",
    ):
        assert client.get(url).status_code == 404, url


def test_account_needs_operations_or_agreements(client, enforced):
    enforced("ana", COSTS)

    assert (
        client.get("/cuenta/clinica-sur/?nombre=Clinica+Sur").status_code == 403
    )
