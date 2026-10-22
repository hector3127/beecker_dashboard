"""Pagina de guia del frontend nuevo y su API de prueba."""

import json
import re

import pytest

PAGE = "/guia-de-interfaz/"


@pytest.fixture
def anonymous(settings):
    settings.PORTAL_LOGIN_REQUIRED = True


def test_page_renders_layout_and_entry_module(client):
    html = client.get(PAGE).content.decode()

    assert html.count("<main") == 1
    assert 'class="skip-link" href="#main-content"' in html
    assert "app/styles/tokens.css" in html
    assert 'type="module" src="/static/app/scripts/pages/guia/main.js"' in html
    assert "<style" not in html


def test_page_gives_the_script_its_configuration(client, settings):
    settings.FRONTEND_API_BASE = "/genesis/api/v1/"
    html = client.get(PAGE).content.decode()
    raw = re.search(r'<script id="app-config"[^>]*>(.*?)</script>', html, re.S)

    config = json.loads(raw.group(1))

    assert config["apiBase"] == "/genesis/api/v1/"
    assert config["csrfCookie"] == "csrftoken"
    assert config["loginUrl"] == "/admin/login/"
    assert "csrfToken" not in config  # el token nunca va en el HTML


def test_page_sets_the_csrf_cookie_and_legacy_pages_do_not(client):
    assert "csrftoken" in client.get(PAGE).cookies
    assert "csrftoken" not in client.get("/api/v1/ping/").cookies


def test_page_requires_login_when_configured(client, anonymous):
    response = client.get(PAGE)

    assert response.status_code == 302
    assert response.url.startswith("/admin/login/")


def test_page_only_allows_get(client):
    assert client.post(PAGE).status_code == 405


def test_ping_answers_with_the_standard_envelope(client):
    body = client.get("/api/v1/ping/").json()

    assert body["data"] == {"status": "ok"}
    assert body["meta"]["generated_at"]


def test_ping_is_not_the_rpc_catch_all(client):
    """/api/rpc/<funcion>/ sigue funcionando junto a /api/v1/."""
    response = client.post(
        "/api/rpc/noExiste/", {}, content_type="application/json"
    )

    assert response.status_code == 404
