"""The retired dictionary URL keeps the modular page and login contract."""

import pytest


@pytest.fixture(autouse=True)
def no_background_refresh(monkeypatch):
    monkeypatch.setattr(
        "apps.portal.services.executive_refresh.request_refresh",
        lambda **k: None,
    )


@pytest.mark.parametrize("previous", [False, True])
def test_dictionary_uses_modular_shell_without_loading_definitions(
    client, monkeypatch, settings, previous
):
    settings.PORTAL_LOGIN_REQUIRED = False

    def forbidden():
        pytest.fail("Definitions must be loaded through the API, not the page")

    monkeypatch.setattr(
        "apps.portal.services.data_dictionary.glossary_groups", forbidden
    )
    response = client.get(
        "/diccionario-datos/",
        {"q": "margen", **({"vista": "anterior"} if previous else {})},
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert 'id="dictionary-search"' in html
    assert "/static/app/scripts/pages/dictionary/main.js" in html
    assert "portal/js/" not in html
    assert 'data-portal-back href="/"' in html


@pytest.mark.parametrize("previous", [False, True])
def test_dictionary_keeps_login_requirement(client, settings, previous):
    settings.PORTAL_LOGIN_REQUIRED = True
    response = client.get(
        "/diccionario-datos/", {"vista": "anterior"} if previous else {}
    )
    assert response.status_code == 302
    assert "/admin/login/" in response.url
