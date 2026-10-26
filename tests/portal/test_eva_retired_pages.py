"""Los enlaces guardados de EVA sirven frontend y conservan el contexto."""

import pytest
from django.urls import reverse

from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view


@pytest.mark.parametrize("screen", [1, 3])
@pytest.mark.parametrize("previous", [False, True])
def test_pages_keep_current_template(client, monkeypatch, screen, previous):
    view = build_eva2_view([]) if screen == 1 else build_eva1_view([])
    monkeypatch.setattr(
        f"apps.portal.views.eva{2 if screen == 1 else 3}_data",
        lambda: {"eva": view, "error": "Fuente no disponible"},
    )
    response = client.get(
        reverse(f"portal:eva{screen}"),
        {"vista": "anterior"} if previous else {},
    )
    assert response.status_code == 200
    assert f"pages/eva{screen}.html" in {t.name for t in response.templates}
    html = response.content.decode()
    assert f"app/scripts/pages/eva{screen}/main.js" in html
    assert "Fuente no disponible" in html
    assert "core/js/gas_shim.js" not in html
    if screen == 3:
        assert "csrftoken" in response.cookies


@pytest.mark.parametrize("screen", [1, 3])
@pytest.mark.parametrize("previous", [False, True])
def test_history_keeps_current_fragment(client, monkeypatch, screen, previous):
    monkeypatch.setattr(
        f"apps.portal.views.eva{screen}_closed_data",
        lambda: {"projects": [], "historic_rows": [], "error": ""},
    )
    response = client.get(
        reverse(f"portal:eva{screen}_cerrados"),
        {"vista": "anterior"} if previous else {},
    )
    assert response.status_code == 200
    template = "eva_closed" if screen == 1 else "eva3_closed"
    assert f"partials/{template}.html" in {t.name for t in response.templates}
    assert "<table" in response.content.decode()


@pytest.mark.parametrize("screen,status", [(1, 401), (3, 302)])
@pytest.mark.parametrize("previous", [False, True])
def test_history_keeps_original_login_response(
    client, settings, monkeypatch, screen, status, previous
):
    settings.PORTAL_LOGIN_REQUIRED = True
    settings.ACCESS_ENFORCED = False

    def unexpected():
        pytest.fail("Se consultó el histórico antes de iniciar sesión")

    monkeypatch.setattr(
        f"apps.portal.views.eva{screen}_closed_data", unexpected
    )
    response = client.get(
        reverse(f"portal:eva{screen}_cerrados"),
        {"vista": "anterior"} if previous else {},
    )
    assert response.status_code == status
