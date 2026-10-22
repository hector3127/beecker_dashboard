"""Base del frontend nuevo en un navegador real: layout, tokens y estados."""

import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/guia-de-interfaz/"
PING = "**/api/v1/ping/"


def watch(portal):
    """Anota lo que sale mal en la pagina; las fuentes de Google se ignoran."""
    problems = []
    portal.on(
        "console",
        lambda m: (
            problems.append(m.text)
            if m.text.startswith("[Report Only]")
            or "Content Security" in m.text
            else None
        ),
    )
    portal.on("pageerror", lambda e: problems.append(str(e)))
    portal.on(
        "requestfailed",
        lambda r: problems.append(r.url) if portal.base in r.url else None,
    )
    return problems


def test_page_loads_without_errors_or_csp_violations(portal, settings):
    settings.CSP_REPORT_ONLY = True
    problems = watch(portal)

    portal.goto(portal.base + PAGE)

    expect(portal.locator("#guia-api")).to_contain_text("API disponible")
    assert problems == []


def test_styles_match_the_current_design_system(portal):
    portal.goto(portal.base + PAGE)

    def style(selector, prop):
        return portal.eval_on_selector(
            selector, f"e => getComputedStyle(e).{prop}"
        )

    assert style("body", "backgroundColor") == "rgb(243, 244, 253)"
    assert "Plus Jakarta Sans" in style("body", "fontFamily")
    assert style(".top", "backgroundColor") == "rgb(255, 255, 255)"
    assert style(".card", "borderRadius") == "16px"
    assert style(".card", "padding") == "20px 24px"
    assert style(".card h2", "color") == "rgb(27, 26, 158)"
    assert style(".kv", "fontSize") == "38px"
    assert style("th", "backgroundColor") == "rgb(244, 240, 255)"
    assert style(".nav a", "minHeight") == "44px"


def test_keyboard_reaches_the_skip_link_first(portal):
    portal.goto(portal.base + PAGE)
    portal.keyboard.press("Tab")

    link = portal.locator(":focus")
    expect(link).to_have_text("Saltar al contenido")
    portal.keyboard.press("Enter")
    expect(portal.locator("#main-content")).to_be_focused()


def test_loading_state_shows_while_the_request_is_pending(portal):
    def slow(route):
        portal.wait_for_timeout(800)
        route.continue_()

    portal.route(PING, slow)
    portal.goto(portal.base + PAGE)

    region = portal.locator("#guia-api")
    expect(region).to_contain_text("Consultando la API")
    expect(region).to_have_attribute("aria-busy", "true")
    expect(region).to_contain_text("API disponible")
    expect(region).not_to_have_attribute("aria-busy", "true")


def test_error_state_offers_a_retry_that_recovers(portal):
    portal.route(PING, lambda route: route.fulfill(status=502, body="<html>"))
    portal.goto(portal.base + PAGE)

    alert = portal.get_by_role("alert")
    expect(alert).to_contain_text("El servidor no pudo completar la consulta")

    portal.unroute(PING)
    alert.get_by_role("button", name="Reintentar").click()
    expect(portal.locator("#guia-api")).to_contain_text("API disponible")
    expect(portal.get_by_role("alert")).to_have_count(0)


def test_expired_session_is_explained(portal):
    portal.route(
        PING,
        lambda route: route.fulfill(
            status=403, json={"detail": "Authentication credentials"}
        ),
    )
    portal.goto(portal.base + PAGE)

    expect(portal.get_by_role("alert")).to_have_text(
        re.compile("No tienes acceso a esta información")
    )


def test_text_from_the_server_is_never_rendered_as_html(portal):
    """El cliente muestra el mensaje como texto: un <img> no se crea."""
    portal.route(
        PING,
        lambda route: route.fulfill(
            status=400,
            json={"detail": '<img src=x onerror="window.hackeado=1">'},
        ),
    )
    portal.goto(portal.base + PAGE)

    expect(portal.get_by_role("alert")).to_contain_text("<img src=x")
    assert portal.evaluate("window.hackeado") is None
    assert portal.locator("#guia-api img").count() == 0
