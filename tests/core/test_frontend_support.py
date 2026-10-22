"""Soporte del frontend: CSP, importmap y tokens del sistema de diseno."""

import json
import logging
import re
from pathlib import Path

import pytest
from django.test import Client

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PORTAL_CSS = ROOT / "apps/portal/static/portal/css/portal.css"
PAGE = "/guia-de-interfaz/"
HEADER = "Content-Security-Policy-Report-Only"


def nonce_of(html: str) -> str:
    found = re.search(r'<script type="importmap" nonce="([^"]+)"', html)
    assert found, "El importmap debe llevar nonce"
    return found.group(1)


def test_policy_is_only_announced_when_the_flag_is_on(client, settings):
    settings.CSP_REPORT_ONLY = False
    assert HEADER not in client.get(PAGE)

    settings.CSP_REPORT_ONLY = True
    response = client.get(PAGE)
    policy = response[HEADER]

    assert f"'nonce-{nonce_of(response.content.decode())}'" in policy
    assert "'unsafe-inline'" not in policy
    assert "report-uri /csp-report/" in policy


def test_each_request_gets_its_own_nonce(client):
    first = nonce_of(client.get(PAGE).content.decode())
    second = nonce_of(client.get(PAGE).content.decode())

    assert first != second


def test_admin_is_not_reported(client, settings):
    settings.CSP_REPORT_ONLY = True

    assert HEADER not in client.get("/admin/login/")


def test_csp_report_is_logged_without_session_or_csrf(caplog):
    body = {"csp-report": {"violated-directive": "script-src"}}
    with caplog.at_level(logging.WARNING, logger="csp"):
        response = Client(enforce_csrf_checks=True).post(
            "/csp-report/",
            json.dumps(body),
            content_type="application/csp-report",
        )

    assert response.status_code == 204
    assert "script-src" in caplog.text


@pytest.mark.parametrize(
    ("body", "status"),
    [("no es json", 400), ("x" * 9000, 413)],
)
def test_csp_report_rejects_bad_bodies(client, body, status):
    response = client.post(
        "/csp-report/", body, content_type="application/json"
    )

    assert response.status_code == status


def test_csp_report_only_accepts_post(client):
    assert client.get("/csp-report/").status_code == 405


def test_csp_report_log_cannot_be_split_into_lines(client, caplog):
    forged = {"csp-report": {"x": "a\nWARNING falso"}}
    with caplog.at_level(logging.WARNING, logger="csp"):
        client.post(
            "/csp-report/", json.dumps(forged), content_type="application/json"
        )

    assert len(caplog.records) == 1
    assert "\n" not in caplog.records[0].getMessage()


def test_importmap_lists_every_shared_module():
    layout = (FRONTEND / "templates/layouts/base.html").read_text("utf-8")
    mapped = set(re.findall(r'"#app/([^"]+)":', layout))
    scripts = FRONTEND / "static/scripts"
    modules = {
        path.relative_to(scripts).as_posix()
        for path in scripts.rglob("*.js")
        if "pages" not in path.relative_to(scripts).parts
    }

    assert mapped == modules


def declarations(css: str) -> dict[str, str]:
    return dict(re.findall(r"(--[\w-]+):\s*([^;]+);", css))


def test_tokens_keep_the_values_of_the_current_design_system():
    portal = PORTAL_CSS.read_text("utf-8")
    block = portal.split("body.ds {", 1)[1].split("}", 1)[0]
    tokens = (FRONTEND / "static/styles/tokens.css").read_text("utf-8")
    current = declarations(block)
    new = declarations(tokens)

    assert current  # el bloque existe
    for name, value in current.items():
        assert new.get(name) == value, name


def test_new_styles_do_not_define_loose_colors():
    """Los colores viven en tokens.css; las demas hojas usan variables."""
    for sheet in (FRONTEND / "static/styles").glob("*.css"):
        if sheet.name == "tokens.css":
            continue
        loose = re.findall(r"#[0-9a-fA-F]{3,8}\b", sheet.read_text("utf-8"))
        assert set(loose) <= {"#fff"}, (sheet.name, loose)
