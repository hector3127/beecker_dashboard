"""Operativa en un navegador real: estructura, filtros, bloques y alcance."""

import re

import pytest
from playwright.sync_api import expect

from apps.access.scope import AccessScope
from apps.portal import views
from apps.portal.schemas import MonthFacturability
from apps.portal.services.operations_summary import build_operations_summary
from tests.access.fake_provider import DictProvider
from tests.e2e.conftest import watch

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/operativa/"
SLOW = 20000


def month(key, label, percent, fixed=None, variable=None):
    return MonthFacturability(
        month=key,
        label=label,
        short_label=label[:3],
        person_hours=0,
        capacity=0,
        fixed_hours=0,
        fixed_percent=fixed,
        fixed_hc=0,
        variable_capacity=0,
        variable_hours=0,
        variable_percent=variable,
        variable_hc=0,
        service_hours=(),
        free_hours=0,
        free_fte=0,
        global_percent=percent,
    )


@pytest.fixture
def billing(monkeypatch):
    """Tres meses de facturabilidad; el ultimo es el destacado."""
    summary = build_operations_summary(
        [
            month("2026-07", "Julio 2026", 66.0, 10.0, 56.0),
            month("2026-08", "Agosto 2026", 74.5, 12.0, 62.5),
            month("2026-09", "Septiembre 2026", 68.5, 11.0, 57.5),
        ],
        month_closed=True,
    )
    monkeypatch.setattr(
        views, "operations_summary_data", lambda refresh=False: summary
    )


def ready(portal):
    """Espera a que terminen todos los bloques de la actualizacion."""
    expect(portal.locator("#ops-refresh-button")).to_be_enabled(timeout=SLOW)


def test_structure_has_the_sections_in_order_and_one_main(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)

    assert portal.locator("main").count() == 1
    assert portal.locator("h1").inner_text() == "Operativo"
    titles = portal.eval_on_selector_all(
        "main h2", "els => els.map(e => e.textContent)"
    )
    assert titles == [
        "Resumen",
        "Salud del portafolio",
        "Delivery manager",
        "EVA",
        "Facturabilidad",
        "Capacidad del equipo",
    ]
    assert portal.locator("#ops-metrics .ops-metric").count() == 5
    expect(
        portal.get_by_label("Filtrar portafolio por servicio")
    ).to_be_visible()
    expect(portal.get_by_label("Abrir detalle de cuenta")).to_be_visible()


def test_first_paint_shows_the_saved_cut_then_refreshes_by_blocks(
    portal, datos
):
    portal.goto(portal.base + PAGE)

    # Sin corte guardado: hay cifras de proyectos pero no de consumo.
    expect(portal.locator("#ops-metric-progress")).to_contain_text("3")
    expect(portal.locator("#ops-refresh-status")).to_contain_text(
        re.compile("Calculando|Actualizando|Proyectos y estados")
    )
    ready(portal)
    expect(portal.locator("#ops-metric-on-time")).to_contain_text("1")
    expect(portal.locator("#ops-refresh-status")).to_contain_text(
        re.compile("Consulta completada|Actualización parcial")
    )
    expect(portal.locator("#ops-cut")).to_contain_text("Corte calculado al")


def test_service_filter_updates_indicators_url_and_history(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)
    service = portal.get_by_label("Filtrar portafolio por servicio")
    assert "T&M" in service.locator("option").all_inner_texts()

    service.select_option("T&M")
    ready(portal)

    assert "servicio=T%26M" in portal.url
    expect(service).to_have_value("T&M")
    expect(portal.locator("#ops-metric-progress")).to_contain_text("1")
    expect(portal.locator("#ops-managers")).not_to_contain_text("Laura Vega")
    expect(portal.locator("#ops-investment-operational")).to_contain_text(
        "T&M activos"
    )

    portal.go_back()
    ready(portal)
    assert "servicio" not in portal.url
    expect(service).to_have_value("")
    expect(portal.locator("#ops-metric-progress")).to_contain_text("3")
    expect(portal.locator("#ops-managers")).to_contain_text("Laura Vega")


def test_filter_from_the_url_is_applied_on_load(portal, datos):
    portal.goto(f"{portal.base}{PAGE}?servicio=T%26M")
    ready(portal)

    expect(
        portal.get_by_label("Filtrar portafolio por servicio")
    ).to_have_value("T&M")
    expect(portal.locator("#ops-metric-progress")).to_contain_text("1")


def test_a_filter_with_no_projects_says_so(portal, datos):
    portal.goto(f"{portal.base}{PAGE}?servicio=IXB")
    ready(portal)

    expect(portal.locator("#ops-managers .vacio")).to_have_text(
        "Ningún proyecto coincide con los filtros."
    )


def test_choosing_an_account_opens_its_detail_with_the_name(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)

    portal.get_by_label("Abrir detalle de cuenta").select_option("Clinica Sur")

    portal.wait_for_url(
        re.compile(r"/cuenta/clinica-sur/\?nombre=Clinica(%20|\+)Sur")
    )


def test_refresh_button_forces_the_blocks_and_reports_the_result(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)
    forced = []
    portal.on(
        "request",
        lambda r: forced.append(r.url) if "actualizar=1" in r.url else None,
    )

    portal.locator("#ops-refresh-button").click()
    expect(portal.locator("#ops-refresh-button")).to_be_disabled()
    expect(portal.locator("#ops-refresh-button")).to_have_text("Actualizando…")
    ready(portal)

    blocks = {
        re.search(r"bloque=(\w+)", u).group(1) for u in forced if "bloque=" in u
    }
    assert blocks == {"eva3", "inversion", "capacidad", "eva4"}
    assert any("facturabilidad" in u for u in forced)
    expect(portal.locator("#ops-refresh-button")).to_have_text(
        "Actualizar datos"
    )


def test_a_block_that_fails_keeps_what_is_shown_and_is_named(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)
    portal.route(
        re.compile(r".*/screens/operativa/datos/.*bloque=eva3.*"),
        lambda route: route.fulfill(status=502, body="<html>"),
    )

    portal.locator("#ops-refresh-button").click()
    ready(portal)

    status = portal.locator("#ops-refresh-status")
    expect(status).to_contain_text("Actualización parcial")
    expect(status).to_contain_text("EVA 3")
    expect(portal.locator("#ops-metric-progress")).to_contain_text("3")  # sigue


def test_snapshot_failure_offers_a_retry(portal, datos):
    portal.route(
        re.compile(r".*/screens/operativa/(\?.*)?$"),
        lambda route: route.fulfill(status=502, body="<html>"),
    )
    portal.goto(portal.base + PAGE)

    alert = portal.get_by_role("alert")
    expect(alert).to_contain_text("El servidor no pudo completar la consulta")

    portal.unroute(re.compile(r".*/screens/operativa/(\?.*)?$"))
    alert.get_by_role("button", name="Reintentar").click()
    ready(portal)
    expect(portal.locator("#ops-metric-progress")).to_contain_text("3")


def test_health_card_shows_the_donut_and_the_breakdown(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)

    card = portal.locator("#ops-health")
    expect(
        card.get_by_role("heading", name="Salud del portafolio")
    ).to_be_visible()
    expect(card).to_contain_text("3 proyectos en ejecución")
    rows = card.locator("tbody tr")
    assert rows.count() == 3
    expect(rows.nth(0)).to_contain_text("En tiempo")
    assert card.locator("svg circle.donut-arc").count() >= 1
    expect(card.locator(".donut-value")).to_have_text(re.compile(r"\d+%"))
    card.get_by_label("Cómo se calcula la salud del portafolio").click()
    expect(card).to_contain_text("suspendidos no se cuentan")


def test_manager_cards_link_to_their_detail_and_the_carousel_scrolls(
    portal, datos
):
    portal.goto(portal.base + PAGE)
    ready(portal)

    link = portal.locator("#ops-managers").get_by_role("link", name="Alberto")
    assert link.get_attribute("href") == (
        "/operativa/delivery-manager/alberto/?nombre=Alberto"
    )
    track = portal.locator(".dm-track")
    portal.set_viewport_size({"width": 600, "height": 900})
    portal.get_by_role(
        "button", name="Ver siguientes Delivery Managers"
    ).click()
    portal.wait_for_timeout(600)
    assert track.evaluate("e => e.scrollLeft") > 0


def test_capacity_and_eva_cards_show_their_numbers(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)

    capacity = portal.locator("#ops-capacity")
    expect(capacity).to_contain_text("96")
    expect(capacity).to_contain_text("horas disponibles")
    expect(capacity).to_contain_text(
        "Capacidad base del mes: 160 h (20 días × 8 h)"
    )
    expect(capacity).to_contain_text("1 personas sobre jornada")
    meter = capacity.locator(".ops-meter i")
    assert meter.evaluate("e => e.style.width") == "40%"
    eva4 = portal.locator("#ops-eva4-card")
    expect(eva4).to_contain_text("Activos")
    expect(portal.locator("#ops-eva-cards")).to_contain_text("EVA 1")
    expect(portal.locator("#ops-eva-cards")).to_contain_text("EVA 3")


def test_billing_shows_the_latest_month_and_a_bar_changes_it(
    portal, datos, billing
):
    portal.goto(portal.base + PAGE)
    ready(portal)

    summary = portal.locator("#facturability-summary")
    expect(summary.locator(".billing-value")).to_have_text("68.5%")
    expect(summary.locator(".billing-gap")).to_have_text(
        "↓ 1.5 puntos abajo de la meta"
    )
    expect(summary.locator(".billing-label")).to_have_text(
        "Septiembre 2026 · último mes cerrado"
    )
    assert summary.locator(".billing-bar").count() == 3

    summary.get_by_role("button", name=re.compile("Agosto 2026")).click()

    expect(summary.locator(".billing-value")).to_have_text("74.5%")
    expect(summary.locator(".billing-gap")).to_have_text(
        "↑ 4.5 puntos arriba de la meta"
    )
    expect(summary.locator(".billing-label")).to_have_text(
        "Agosto 2026 · mes seleccionado"
    )
    expect(
        summary.get_by_role("button", name=re.compile("Agosto 2026"))
    ).to_have_attribute("aria-pressed", "true")
    # Con teclado tambien.
    bar = summary.get_by_role("button", name=re.compile("Julio 2026"))
    bar.focus()
    portal.keyboard.press("Enter")
    expect(summary.locator(".billing-value")).to_have_text("66%")


def test_billing_failure_is_explained_and_does_not_block_the_rest(
    portal, datos, monkeypatch
):
    def broken(refresh=False):
        raise RuntimeError("sin fuentes")

    monkeypatch.setattr(views, "operations_summary_data", broken)
    portal.goto(portal.base + PAGE)
    ready(portal)

    expect(portal.locator("#facturability-summary")).to_contain_text(
        "No se pudo cargar facturabilidad"
    )
    expect(portal.locator("#ops-metric-progress")).to_contain_text("3")
    expect(portal.locator("#ops-refresh-status")).to_contain_text(
        "no se pudo actualizar facturabilidad"
    )


def test_source_errors_are_reported_with_the_cut_still_visible(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)
    from apps.portal.services.eva2 import build_eva2_view
    from apps.portal.services.eva_loader import Eva2Load

    views.load_eva2 = lambda **k: Eva2Load(
        view=build_eva2_view([]), error="Azure no responde."
    )
    portal.locator("#ops-refresh-button").click()
    ready(portal)

    expect(portal.locator("#ops-alerts")).to_contain_text("Azure no responde.")


def test_capture_button_downloads_the_screen(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)

    with portal.expect_download(timeout=60000) as download:
        portal.get_by_role("button", name="↓ Descargar captura").click()

    assert re.fullmatch(
        r"operativa-\d{4}-\d{2}-\d{2}\.png", download.value.suggested_filename
    )


def test_page_has_no_errors_or_csp_violations(portal, datos, billing, settings):
    settings.CSP_REPORT_ONLY = True
    problems = watch(portal)

    portal.goto(portal.base + PAGE)
    ready(portal)
    portal.get_by_label("Filtrar portafolio por servicio").select_option("T&M")
    ready(portal)

    assert problems == []


def test_limited_scope_hides_team_figures_and_other_accounts(
    portal, datos, settings, client, django_user_model
):
    settings.ACCESS_ENFORCED = True
    settings.ACCESS_PROVIDER = "tests.access.fake_provider.DictProvider"
    DictProvider.GRANTS = {
        "ana": (
            frozenset({"view_operations"}),
            AccessScope.limited(accounts=["ACME"]),
        )
    }
    client.force_login(django_user_model.objects.create_user("ana"))
    portal.context.add_cookies(
        [
            {
                "name": "sessionid",
                "value": client.cookies["sessionid"].value,
                "url": portal.base,
            }
        ]
    )
    try:
        portal.goto(portal.base + PAGE)
        ready(portal)

        expect(portal.locator("#ops-metric-progress")).to_contain_text("2")
        body = portal.locator("body")
        expect(body).not_to_contain_text("Clinica Sur")
        assert (
            "Clinica Sur"
            not in portal.get_by_label("Abrir detalle de cuenta").inner_text()
        )
        expect(portal.locator("#ops-capacity")).to_contain_text(
            "no disponibles con tu acceso"
        )
        expect(portal.locator("#facturability-summary")).to_contain_text(
            "no disponibles con tu acceso"
        )
        expect(portal.locator("#ops-eva-cards")).to_contain_text(
            "no disponibles con tu acceso"
        )
    finally:
        DictProvider.GRANTS = {}


def test_a_person_without_the_capability_cannot_open_the_page(
    portal, settings, client, django_user_model
):
    settings.ACCESS_ENFORCED = True
    settings.ACCESS_PROVIDER = "tests.access.fake_provider.DictProvider"
    DictProvider.GRANTS = {
        "sin": (frozenset({"view_executive"}), AccessScope.everything())
    }
    client.force_login(django_user_model.objects.create_user("sin"))
    portal.context.add_cookies(
        [
            {
                "name": "sessionid",
                "value": client.cookies["sessionid"].value,
                "url": portal.base,
            }
        ]
    )
    try:
        response = portal.goto(portal.base + PAGE)
        assert response.status == 403
    finally:
        DictProvider.GRANTS = {}


def hrefs(portal, selector):
    return portal.eval_on_selector_all(
        selector, "els => els.map(e => e.getAttribute('href'))"
    )


def test_navigation_and_detail_links(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)

    assert hrefs(portal, ".nav a") == ["/", "/operativa/", "/comercial/"]
    eva = hrefs(portal, "#ops-eva-cards a")
    assert {
        "/operativa/eva-1/",
        "/operativa/eva-3/",
        "/operativa/eva-4/",
    } <= set(eva)
    assert "/operativa/eva-2/" not in eva
    buttons = hrefs(portal, "a.ops-button")
    assert "/capacidad-instalada/" in buttons
    assert "/operativa/facturabilidad/" in buttons
    assert "/operativa/facturabilidad/especialidad/" in buttons
    assert "/operativa/facturabilidad/recurso/" in buttons
    assert "/operativa/kpis-delivery-managers/" in buttons
    assert "/operativa/inversion/" in hrefs(portal, ".dm-investment-link")
    assert all(h != "/legacy/" for h in hrefs(portal, "a"))


def test_eva_cards_show_real_numbers(portal, datos):
    portal.goto(portal.base + PAGE)
    ready(portal)

    eva1 = portal.locator("#ops-eva-cards .eva-card").nth(0)
    expect(eva1).to_contain_text("EVA 1")
    stats = eva1.locator(".eva-value").all_inner_texts()
    assert stats == ["4", "4 d", "50%"]
    eva3 = portal.locator("#ops-eva-cards .eva-card").nth(1)
    assert eva3.locator(".eva-value").all_inner_texts() == ["0", "—", "—"]


def test_empty_portfolio_says_so(portal, datos, monkeypatch):
    from tests.portal.test_views import stub_portfolio

    stub_portfolio(monkeypatch)
    portal.goto(portal.base + PAGE)
    ready(portal)

    expect(portal.locator("#ops-managers .vacio")).to_have_text(
        "Sin proyectos que mostrar todavía."
    )
    expect(portal.locator("#ops-metric-progress")).to_contain_text("0")
