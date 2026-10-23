"""La API diaria reutiliza los servicios y rechaza accesos antes de leer."""

from unittest.mock import Mock

import pytest

from apps.access.scope import AccessScope

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/capacidad/diaria/"


def test_base_passes_the_month_without_changing_fields(client, monkeypatch):
    source = Mock(return_value={"ok": True, "mes": "2026-10", "filas": []})
    monkeypatch.setattr(
        "apps.portal.api.capacity_daily.get_capacity_base", source
    )
    response = client.get(BASE, {"mes": "2026-10"})
    assert response.status_code == 200
    assert response.json()["data"] == source.return_value
    source.assert_called_once_with("2026-10")


def test_project_keeps_iteration_month_and_force(client, monkeypatch):
    result = {"ok": True, "daily": {"ana": {"2026-10-01": 10}}}
    source = Mock(return_value=result)
    monkeypatch.setattr(
        "apps.portal.api.capacity_daily.get_capacity_project_data", source
    )
    response = client.get(
        BASE + "proyecto/",
        {
            "mes": "2026-10",
            "proyecto": "P1",
            "iteration": "Sprint/1",
            "actualizar": "1",
        },
    )
    assert response.status_code == 200
    assert response.json()["data"] == result
    source.assert_called_once_with("P1", "Sprint/1", "2026-10", True)


@pytest.mark.parametrize("month", ["", "2026-13", "26-10", "2026-10-01"])
def test_invalid_month_never_reads_sources(client, monkeypatch, month):
    source = Mock(side_effect=AssertionError("Source read"))
    monkeypatch.setattr(
        "apps.portal.api.capacity_daily.get_capacity_base", source
    )
    assert client.get(BASE, {"mes": month}).status_code == 400
    source.assert_not_called()


@pytest.mark.parametrize("suffix", ["", "proyecto/"])
@pytest.mark.parametrize("grant", ["anonymous", "limited", "wrong"])
def test_access_is_checked_before_sources(
    client, enforced, monkeypatch, suffix, grant
):
    source = Mock(side_effect=AssertionError("Source read"))
    monkeypatch.setattr(
        "apps.portal.api.capacity_daily.get_capacity_base", source
    )
    monkeypatch.setattr(
        "apps.portal.api.capacity_daily.get_capacity_project_data", source
    )
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
    response = client.get(BASE + suffix, {"mes": "2026-10", "proyecto": "P1"})
    assert response.status_code in {401, 403}
    source.assert_not_called()


def test_page_is_modular_and_does_not_read_sources(client, monkeypatch):
    monkeypatch.setattr(
        "apps.portal.api.capacity_daily.get_capacity_base",
        Mock(side_effect=AssertionError("Source read")),
    )
    html = client.get("/capacidad-instalada/").content.decode()
    assert "app/scripts/pages/capacity_daily/main.js" in html
    assert "gas_shim" not in html
    assert "portal/js/capacidad_instalada.js" not in html
