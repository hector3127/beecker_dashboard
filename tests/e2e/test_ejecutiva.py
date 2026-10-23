"""Business Overview en un navegador real: cifras, periodo, avisos y corte."""

import json
import re

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)

PAGE = "/"
SCREEN = "**/api/v1/screens/executive/?*"
SCREEN_BARE = "**/api/v1/screens/executive/"
REFRESH = "**/api/v1/screens/executive/actualizar/**"

FIGURES = {
    "finance": {
        "revenue": {"invoiced": 1897644.14, "collections_percent": 68},
        "costs": {
            "cost": 500000,
            "complete": False,
            "projects": [
                {"id": "A", "cost": 500000, "complete": True},
                {
                    "id": "B",
                    "cost": None,
                    "complete": False,
                    "error": "Sin tarifa",
                },
            ],
            "pending": 1,
        },
    },
    "operations": {
        "partial": False,
        "projects": 10,
        "etc": 36890,
        "advance": 40.58,
        "fte": 34.16,
        "facturability": 75.2,
        "investment_operational": 111.8,
        "pending_ids": ["P9"],
        "missing_budget_ids": ["P8"],
    },
    "commercial": {
        "won": 1490000,
        "won_count": 4,
        "delivery": 800,
        "open": 900,
        "delivery_note": "Poly revenue",
        "open_note": "Abiertas",
        "open_rule": True,
        "delivery_rule": True,
    },
    "monthly": {
        "complete": True,
        "months": [
            {"month": "2026-01", "revenue": 100, "cost": 40},
            {"month": "2026-02", "revenue": 200, "cost": None},
        ],
    },
    "accounts": [
        {
            "name": "Grande",
            "slug": "grande",
            "revenue": 1000,
            "gross_profit": 100,
            "margin": 10,
            "projects": 4,
            "partial": False,
        },
        {
            "name": "Heineken México",
            "slug": "heineken-mexico",
            "revenue": 500,
            "gross_profit": 200,
            "margin": 40,
            "projects": 3,
            "partial": True,
        },
    ],
}


def reply(route, data, meta=None, status=200):
    route.fulfill(
        status=status,
        content_type="application/json",
        body=json.dumps({"data": data, "meta": meta or {}}),
    )


@pytest.fixture
def served(portal, datos):
    """Un corte completo y conocido."""
    meta = {"loaded_at": "2026-10-22T10:00:00-06:00", "blocks": {}}
    portal.route(SCREEN, lambda r: reply(r, FIGURES, meta))
    portal.route(SCREEN_BARE, lambda r: reply(r, FIGURES, meta))
    portal.route(
        REFRESH,
        lambda r: reply(
            r,
            {
                "state": "ready",
                "partial": False,
                "blocks": {
                    "financial": True,
                    "commercial": True,
                    "operations": True,
                },
            },
        ),
    )


def test_the_prepared_cut_fills_every_card_without_extra_queries(
    portal, served
):
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#executive-revenue")).to_have_text("1.89M")
    expect(portal.locator("#executive-collections")).to_have_text("68%")
    expect(portal.locator("#executive-margin")).to_have_text("74%*")
    expect(portal.locator("#executive-margin-note")).to_contain_text(
        "Parcial con costos disponibles"
    )
    expect(portal.locator("#executive-ops-etc")).to_have_text("36,890 h")
    expect(portal.locator("#executive-ops-advance")).to_have_text("41%")
    expect(portal.locator("#executive-ops-cut")).to_have_text("Corte completo")
    expect(portal.locator("#commercial-won")).to_have_text("1.49M")
    expect(portal.locator("#commercial-delivery-note")).to_contain_text("Poly")
    expect(portal.locator("#portal-freshness-text")).to_have_text(
        "Datos al 22/10/2026, 10:00"
    )
    assert portal.locator("main").count() == 1
    expect(portal.locator("#monthly-profit-chart svg")).to_be_visible()
    expect(portal.locator("#executive-cut-status")).to_contain_text(
        "Última consulta"
    )


def test_pending_lists_open_in_a_dialog_and_return_focus(portal, served):
    portal.goto(portal.base + PAGE)

    blockers = portal.locator("#executive-cost-blockers")
    expect(blockers).to_have_text("1 costos pendientes")
    blockers.click()
    dialog = portal.locator("dialog.portal-pending-dialog")
    expect(dialog).to_be_visible()
    expect(dialog).to_contain_text("Sin tarifa")
    portal.keyboard.press("Escape")
    expect(dialog).to_have_count(0)
    expect(blockers).to_be_focused()

    portal.locator("#executive-ops-status").click()
    expect(portal.locator("dialog.portal-pending-dialog")).to_contain_text(
        "Sin presupuesto"
    )
    expect(portal.locator("dialog.portal-pending-dialog")).to_contain_text(
        "Consumo pendiente"
    )


def test_method_drawer_explains_each_card(portal, served):
    portal.goto(portal.base + PAGE)
    portal.locator('[data-method="operations"]').click()
    drawer = portal.locator("#executive-method-dialog")
    expect(drawer).to_be_visible()
    expect(portal.locator("#method-context")).to_have_text("Operaciones")
    expect(portal.locator('[data-method-panel="operations"]')).to_be_visible()
    expect(portal.locator('[data-method-panel="financial"]')).to_be_hidden()
    portal.locator("[data-method-close]").first.click()
    expect(drawer).to_be_hidden()


def test_ranking_compares_every_account_and_keeps_the_choice_in_the_url(
    portal, served
):
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#healthy-account-count")).to_have_text(
        "1 de 1 cuentas"
    )
    portal.select_option("#ranking-sort", "revenue")
    expect(portal.locator("#healthy-financial-accounts")).to_contain_text(
        "Grande"
    )
    assert "ranking_criterio=revenue" in portal.url
    portal.locator("#healthy-financial-accounts a").first.click()
    portal.wait_for_url(re.compile(r"/cuenta/grande/\?nombre=Grande"))


def test_absent_blocks_show_loading_and_a_ready_cut_is_applied_once(
    portal, datos
):
    state = {"calls": 0}
    partial = {**FIGURES, "commercial": None}

    def screen(route):
        ready = state["calls"] > 0
        reply(
            route,
            FIGURES if ready else partial,
            {"loaded_at": "2026-10-22T10:00:00-06:00"},
        )

    def refresh(route):
        state["calls"] += 1
        reply(
            route,
            {
                "state": "ready",
                "partial": False,
                "blocks": {
                    "financial": True,
                    "commercial": True,
                    "operations": True,
                },
            },
        )

    portal.route(SCREEN, screen)
    portal.route(SCREEN_BARE, screen)
    portal.route(REFRESH, refresh)
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#commercial-won")).to_have_text(
        "1.49M", timeout=20000
    )
    expect(portal.locator("#executive-revenue")).to_have_text("1.89M")
    assert state["calls"] >= 1


def test_a_failed_preparation_removes_the_skeleton_and_keeps_valid_data(
    portal, datos
):
    partial = {**FIGURES, "commercial": None}
    portal.route(
        SCREEN,
        lambda r: reply(r, partial, {"loaded_at": "2026-10-22T10:00:00-06:00"}),
    )
    portal.route(
        SCREEN_BARE,
        lambda r: reply(r, partial, {"loaded_at": "2026-10-22T10:00:00-06:00"}),
    )
    portal.route(REFRESH, lambda r: reply(r, {"state": "failed", "blocks": {}}))
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#commercial-won")).to_have_text("No disponible")
    expect(portal.locator("#executive-revenue")).to_have_text("1.89M")
    expect(portal.locator("#executive-cut-status")).to_have_text(
        "No se pudo completar. Se conserva el corte mostrado."
    )


def test_update_button_prepares_a_new_cut_and_reloads_to_show_it(portal, datos):
    loads = []
    meta = {"loaded_at": "2026-10-22T10:00:00-06:00", "blocks": {}}

    def screen(route):
        loads.append(route.request.url)
        reply(route, FIGURES, meta)

    portal.route(SCREEN, screen)
    portal.route(SCREEN_BARE, screen)
    portal.route(
        REFRESH,
        lambda r: reply(
            r,
            {
                "state": "ready",
                "partial": False,
                "blocks": {
                    "financial": True,
                    "commercial": True,
                    "operations": True,
                },
            },
        ),
    )
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#executive-revenue")).to_have_text("1.89M")
    assert len(loads) == 1

    portal.locator("#executive-prepare").click()

    portal.wait_for_function(
        "window.performance.getEntriesByType('navigation').length > 0"
    )
    portal.wait_for_timeout(1500)
    assert len(loads) > 1  # la pagina se recargo con el corte nuevo


def test_period_picker_applies_a_range_and_validates_it(portal, served):
    portal.goto(portal.base + PAGE)
    portal.locator("#executive-date-picker summary").click()
    form = portal.locator("#executive-period-form")
    portal.locator('[data-quick="year"]').click()
    expect(portal.locator("#picker-preview")).to_contain_text("01/01/")

    form.locator('input[name="desde"]').fill("2026-03-10")
    form.locator('input[name="hasta"]').fill("2026-03-01")
    form.get_by_role("button", name="Aplicar periodo").click()
    expect(portal.locator("#picker-error")).to_have_text(
        "Selecciona una fecha inicial y una fecha final posterior."
    )

    form.locator('input[name="hasta"]').fill("2026-03-31")
    form.get_by_role("button", name="Aplicar periodo").click()
    portal.wait_for_url(re.compile(r"desde=2026-03-10&hasta=2026-03-31"))
    assert "periodo=rango" in portal.url and "vista=custom" in portal.url


def test_capture_button_and_the_way_to_the_dictionary(portal, served):
    portal.goto(portal.base + PAGE)

    expect(
        portal.get_by_role("button", name="↓ Descargar captura")
    ).to_be_visible()
    expect(
        portal.get_by_role("link", name="Glosario de indicadores")
    ).to_have_attribute("href", "/diccionario-datos/")
    portal.locator(".executive-glossary summary").click()
    expect(portal.locator(".executive-glossary-grid")).to_be_visible()


def test_agreements_are_part_of_the_page(portal, served):
    portal.goto(portal.base + PAGE)

    section = portal.locator("#executive-agreements")
    expect(section).to_be_visible()
    expect(section.locator("select[name=account]")).to_contain_text(
        "Heineken México"
    )


def test_amounts_sent_as_decimal_text_are_not_shown_as_pending(portal, served):
    # El servidor manda los importes Decimal como texto, no como número.
    figures = json.loads(json.dumps(FIGURES))
    figures["finance"]["revenue"]["invoiced"] = "1897644.14"
    figures["commercial"]["delivery"] = "415926.17"
    meta = {"loaded_at": "2026-10-22T10:00:00-06:00", "blocks": {}}
    portal.route(SCREEN, lambda r: reply(r, figures, meta))
    portal.route(SCREEN_BARE, lambda r: reply(r, figures, meta))

    portal.goto(portal.base + PAGE)

    expect(portal.locator("#executive-revenue")).to_have_text("1.89M")
    expect(portal.locator("#commercial-delivery")).to_have_text("415K")
