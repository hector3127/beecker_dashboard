"""La API de capacidad entrega el mes completo y rechaza accesos antes."""

from unittest.mock import Mock

import pytest

from apps.access.scope import AccessScope
from core.exceptions import SheetsError

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/capacidad/diaria/"
SERVICE = "apps.portal.api.capacity_daily.build_team_capacity"
READER = "apps.portal.api.capacity_daily.build_sheet_repository"


@pytest.fixture(autouse=True)
def reader(monkeypatch):
    monkeypatch.setattr(READER, lambda: "lector")


def test_month_and_default_workday_reach_the_service(client, monkeypatch):
    source = Mock(return_value={"ok": True, "mes": "2026-10", "filas": []})
    monkeypatch.setattr(SERVICE, source)

    response = client.get(BASE, {"mes": "2026-10"})

    assert response.status_code == 200
    assert response.json()["data"] == source.return_value
    source.assert_called_once_with("lector", "2026-10", 8.0)


def test_workday_is_forwarded(client, monkeypatch):
    source = Mock(return_value={"ok": True})
    monkeypatch.setattr(SERVICE, source)

    client.get(BASE, {"mes": "2026-10", "jornada": "6.5"})

    source.assert_called_once_with("lector", "2026-10", 6.5)


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"mes": "2026-13"},
        {"mes": "26-10"},
        {"mes": "2026-10-01"},
        {"mes": "2026-10", "jornada": "0"},
        {"mes": "2026-10", "jornada": "25"},
        {"mes": "2026-10", "jornada": "ocho"},
    ],
)
def test_invalid_input_never_reads_sources(client, monkeypatch, params):
    source = Mock(side_effect=AssertionError("Source read"))
    monkeypatch.setattr(SERVICE, source)

    assert client.get(BASE, params).status_code == 400
    source.assert_not_called()


def test_missing_sheets_answer_ok_false(client, monkeypatch):
    monkeypatch.setattr(SERVICE, Mock(side_effect=SheetsError("sin conexion")))

    data = client.get(BASE, {"mes": "2026-10"}).json()["data"]

    assert data["ok"] is False and data["error"]


@pytest.mark.parametrize("grant", ["anonymous", "limited", "wrong"])
def test_access_is_checked_before_sources(client, enforced, monkeypatch, grant):
    source = Mock(side_effect=AssertionError("Source read"))
    monkeypatch.setattr(SERVICE, source)
    enforced(
        "Ana",
        caps=frozenset(
            {"view_costs"} if grant == "wrong" else {"view_operations"}
        ),
        scope=AccessScope.limited(accounts=["Acme"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()

    response = client.get(BASE, {"mes": "2026-10"})

    assert response.status_code in {401, 403}
    source.assert_not_called()


def test_page_is_modular_and_does_not_read_sources(client, monkeypatch):
    monkeypatch.setattr(
        SERVICE, Mock(side_effect=AssertionError("Source read"))
    )

    response = client.get("/capacidad-instalada/")
    html = response.content.decode()

    assert "app/scripts/pages/capacity_daily/main.js" in html
    assert "gas_shim" not in html
    assert "csrftoken" in response.cookies
