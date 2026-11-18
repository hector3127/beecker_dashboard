"""Business Overview en un navegador real: cifras, periodo, avisos y corte."""

import json
import re
from pathlib import Path

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
        "capacity_consumed_hours": 36890,
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
    expect(portal.locator("#executive-ops-cut")).to_have_count(0)
    expect(portal.locator("#commercial-won")).to_have_text("1.49M")
    expect(portal.locator("#commercial-delivery-note")).to_contain_text("Poly")
    expect(portal.locator("#portal-freshness-text")).to_have_text(
        "Datos al 22/10/2026, 10:00"
    )
    assert portal.locator("main").count() == 1
    expect(portal.locator("#monthly-profit-chart svg")).to_be_visible()
    expect(portal.locator("#executive-cut-status")).to_have_text("")


def test_pending_lists_open_in_a_dialog_and_return_focus(portal, served):
    portal.goto(portal.base + PAGE)

    blockers = portal.locator("#executive-cost-blockers")
    expect(blockers).to_have_text("1 proyecto con costos por revisar")
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


def test_cards_have_no_information_buttons_and_keep_the_glossary(
    portal, served
):
    portal.goto(portal.base + PAGE)
    expect(
        portal.locator(".executive-cards .executive-info-button")
    ).to_have_count(0)
    expect(portal.locator(".executive-cards [data-method]")).to_have_count(0)
    expect(
        portal.get_by_role("link", name="Glosario de indicadores")
    ).to_be_visible()
    expect(portal.locator("#executive-method-dialog")).to_be_hidden()


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_ranking_compares_every_account_and_keeps_the_choice_in_the_url(
    portal, served, width
):

    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)

    expect(portal.locator("#healthy-account-count")).to_have_text(
        "1 de 1 cuentas"
    )
    portal.select_option("#ranking-sort", "revenue")
    expect(portal.locator("#healthy-financial-accounts")).to_contain_text(
        "Grande"
    )
    assert "ranking_criterio=revenue" in portal.url
    panel = portal.locator(".ranking-section")
    search_box = portal.locator("#ranking-search").bounding_box()
    sort_box = portal.locator("#ranking-sort").bounding_box()
    button_box = panel.locator(".ranking-all").bounding_box()
    assert sort_box and button_box and search_box
    assert abs(sort_box["y"] - button_box["y"]) <= 1
    assert abs(sort_box["height"] - button_box["height"]) <= 1
    if width > 700:
        assert abs(search_box["y"] - button_box["y"]) <= 1
    expect(panel.locator(".ranking-open")).to_have_count(0)
    account = portal.locator(
        "#healthy-financial-accounts .ranking-account"
    ).first
    assert panel.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
    output = Path("tmp/design/account-rankings")
    output.mkdir(parents=True, exist_ok=True)
    panel.screenshot(path=str(output / f"rankings-{width}.png"))
    account.click()
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


def test_prepared_cut_requires_no_manual_refresh_or_extra_requests(
    portal, served
):
    requests = []
    portal.on(
        "request",
        lambda request: requests.append((request.method, request.url)),
    )
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#executive-revenue")).to_have_text("1.89M")
    expect(portal.locator("#executive-prepare")).to_have_count(0)
    assert not [
        request
        for request in requests
        if "/executive/actualizar/" in request[1]
    ]


def test_period_picker_applies_a_range_and_validates_it(portal, served):
    portal.goto(portal.base + PAGE)
    portal.locator("#executive-date-picker summary").click()
    form = portal.locator("#executive-period-form")
    expect(
        form.locator("[data-quick], [data-tab], #picker-year, #picker-quarter")
    ).to_have_count(0)
    expect(portal.locator("#picker-preview")).not_to_be_empty()
    form.locator("#picker-month-left [data-date]:not(.outside)").nth(9).click()
    expect(portal.locator("#executive-date-picker")).to_have_attribute(
        "open", ""
    )
    form.locator("#picker-month-left [data-date]:not(.outside)").nth(19).click()
    expect(portal.locator("#executive-date-picker")).to_have_attribute(
        "open", ""
    )
    expect(form.get_by_role("button", name="Aplicar periodo")).to_be_visible()

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


def test_one_glossary_link_and_no_broken_capture_control(portal, served):
    portal.goto(portal.base + PAGE)
    expect(
        portal.locator(
            ".executive-report-actions #executive-capture-actions .capture-button"
        )
    ).to_be_visible()
    expect(portal.locator("header.top .capture-button")).to_have_count(0)
    expect(
        portal.get_by_role("link", name="Glosario de indicadores")
    ).to_have_attribute("href", "/diccionario-datos/")
    expect(portal.locator(".executive-glossary")).to_have_count(0)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_agreements_are_part_of_the_page(portal, served, width):

    item = {
        "id": 101,
        "account": "Heineken México",
        "title": "Prueba",
        "meeting_source": "direction",
        "meeting_date": "2026-10-21",
        "kind": "pending",
        "owner": "",
        "due_date": "2026-10-29",
        "status": "progress",
        "notes": "Dar seguimiento a consumos de horas proyecto.",
        "actions": {"edit": True, "change_status": True},
    }
    records = [item]
    writes = []

    def agreements(route):
        method = route.request.method
        if method == "GET":
            reply(route, {"items": records, "can_edit": True})
        else:
            values = json.loads(route.request.post_data)
            writes.append((method, values))
            if method == "PATCH":
                item.update(values)
                reply(route, item)
            else:
                created = {**values, "id": 102, "actions": item["actions"]}
                records.append(created)
                reply(route, created, status=201)

    portal.route("**/api/v1/agreements/**", agreements)
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    section = portal.locator("#executive-agreements")
    expect(section.locator(".agreement-kind")).to_have_text("Pendiente")
    expect(section.locator("select[name=account]")).to_contain_text(
        "Heineken México"
    )
    expect(section.locator(".agreement-status-select")).to_have_value(
        "progress"
    )
    assert section.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
    output = Path("tmp/design/agreements")
    output.mkdir(parents=True, exist_ok=True)
    section.screenshot(path=str(output / f"followup-{width}.png"))

    toggle = section.locator(".agreement-group-toggle")
    toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "false")
    expect(section.locator(".agreement-status-select")).to_be_hidden()
    toggle.click()
    expect(section.locator(".agreement-status-select")).to_be_visible()
    section.locator("#agreement-search").fill("no coincide")
    expect(section.locator("#agreement-rows")).to_contain_text("Sin acuerdos")
    section.locator("#agreement-search").fill("")
    section.locator("#agreement-filter").select_option("open")
    expect(section.locator("#agreement-rows")).to_contain_text("Sin acuerdos")
    section.locator("#agreement-filter").select_option("")

    section.get_by_role("button", name="Editar", exact=True).click()
    form = section.locator("#agreement-form")
    expect(form).to_be_visible()
    form.locator('[name="title"]').fill("Prueba editada")
    form.locator("#agreement-save").click()
    expect(form).to_be_hidden()
    expect(section.locator("#agreement-rows")).to_contain_text("Prueba editada")
    section.locator(".agreement-status-select").select_option("open")
    expect(section.locator("#agreement-feedback")).to_contain_text(
        "Estado actualizado"
    )
    section.get_by_role("button", name="Completar Prueba editada").click()
    expect(section.locator(".agreement-status-select")).to_have_value("done")
    assert writes[-1] == ("PATCH", {"status": "done"})

    section.locator("#agreement-new").click()
    form.locator('[name="account"]').select_option("Heineken México")
    form.locator('[name="meeting_date"]').fill("2026-10-24")
    form.locator('[name="title"]').fill("Nuevo pendiente")
    form.locator("#agreement-save").click()
    expect(form).to_be_hidden()
    expect(section.locator("#agreement-rows")).to_contain_text(
        "Nuevo pendiente"
    )
    assert writes[-1][0] == "POST"


def test_followup_read_only_keeps_writes_unavailable(portal, served):
    record = {
        "id": 1,
        "account": "Heineken México",
        "title": "Solo lectura",
        "status": "open",
        "kind": "pending",
        "actions": {"edit": False, "change_status": False},
    }
    portal.route(
        "**/api/v1/agreements/**",
        lambda r: reply(r, {"items": [record], "can_edit": False}),
    )
    portal.goto(portal.base + PAGE)
    section = portal.locator("#executive-agreements")
    expect(section.locator(".agreement-status-select")).to_be_disabled()
    expect(section.locator("#agreement-new")).to_be_hidden()
    expect(
        section.get_by_role("button", name="Editar", exact=True)
    ).to_have_count(0)
    expect(section.locator(".agreement-close")).to_have_count(0)


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


@pytest.mark.parametrize("width", [1450, 1120, 900, 390, 320])
def test_soft_card_design_keeps_values_actions_and_mobile_layout(
    portal, served, width
):

    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#executive-revenue")).to_have_text("1.89M")
    cards = portal.locator(".executive-cards")
    expect(cards.locator(".executive-card-art")).to_have_count(3)
    expect(cards.locator(".metric-gauge")).to_have_count(3)
    expect(
        cards.locator(
            '[aria-label="Facturación mensual del periodo seleccionado"]'
        )
    ).to_be_visible()
    # Only one month has costs in this fixture: never invent a margin trend.
    expect(
        cards.locator(
            '[aria-label="Margen mensual con los costos disponibles '
            'del periodo seleccionado"]'
        )
    ).to_have_count(0)
    expect(cards).not_to_contain_text("vs. mismo periodo")
    expect(cards).not_to_contain_text("Meta 60%")
    for card in cards.locator(".executive-card").all():
        bounds = card.bounding_box()
        assert (
            bounds
            and bounds["x"] >= 0
            and bounds["x"] + bounds["width"] <= width + 1
        )
        assert card.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
        expect(card.locator(".executive-detail-link")).to_be_visible()
    expect(cards.locator(".executive-info-button")).to_have_count(0)
    output = Path("tmp/design/executive-cards")
    output.mkdir(parents=True, exist_ok=True)
    cards.screenshot(path=str(output / f"cards-{width}.png"))


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_monthly_reference_design_preserves_financial_measures(
    portal, served, width
):

    figures = json.loads(json.dumps(FIGURES))
    revenues = [
        232000,
        192000,
        190000,
        211000,
        208000,
        195000,
        152000,
        197000,
        183000,
    ]
    costs = [110000, 101000, 100000, 85000, 88000, 88000, 94000, 85000, 90000]
    revenues += [None, None, None]
    costs += [None, None, None]
    figures["monthly"]["complete"] = False
    figures["monthly"]["months"] = [
        {"month": f"2026-{i + 1:02}", "revenue": r, "cost": c, "future": i >= 9}
        for i, (r, c) in enumerate(zip(revenues, costs, strict=True))
    ]
    meta = {"loaded_at": "2026-10-24T10:00:00-06:00", "blocks": {}}
    portal.route(SCREEN, lambda r: reply(r, figures, meta))
    portal.route(SCREEN_BARE, lambda r: reply(r, figures, meta))
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE + "?periodo=anio&anio=2026")
    panel = portal.locator(".executive-monthly")
    chart = panel.locator("#monthly-profit-chart svg")
    expect(chart).to_be_visible()
    expect(chart.locator(".monthly-revenue-bar")).to_have_count(9)
    expect(chart.locator(".monthly-cost-bar")).to_have_count(9)
    expect(chart.locator("circle")).to_have_count(9)
    expect(chart.locator(".monthly-margin-label")).to_have_count(9)
    for label in chart.locator(".monthly-margin-label").all():
        expect(label).to_be_visible()
    expect(panel.locator(".monthly-frequency")).to_have_count(0)
    expect(panel.locator(".executive-chart-legend")).to_contain_text("Costos")
    expect(panel.locator("#monthly-profit-state")).to_contain_text("parcial")
    expect(chart).to_contain_text("300K")
    for name in [
        "ene",
        "feb",
        "mar",
        "abr",
        "may",
        "jun",
        "jul",
        "ago",
        "sep",
        "oct",
        "nov",
        "dic",
    ]:
        expect(
            chart.locator("text").filter(has_text=re.compile(f"^{name}$"))
        ).to_have_count(1)
    expect(chart.locator("text").filter(has_text="Futuro")).to_have_count(3)
    panel.locator(".monthly-panel-info summary").click()
    expect(panel.locator("#monthly-profit-note")).to_be_visible()
    expect(panel.locator("#monthly-profit-note")).to_contain_text(
        "DataRevenue G"
    )
    panel.locator(".monthly-panel-info summary").click()
    assert panel.evaluate("e => e.scrollWidth <= e.clientWidth + 1")
    if width > 900:
        assert panel.locator("#monthly-profit-chart").evaluate(
            "e => e.scrollWidth <= e.clientWidth + 1"
        )
    output = Path("tmp/design/monthly-profit")
    output.mkdir(parents=True, exist_ok=True)
    panel.screenshot(path=str(output / f"monthly-{width}.png"))


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_indicator_glossary_is_available_without_repeating_the_definitions(
    portal, served, width
):
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    expect(
        portal.get_by_role("link", name="Glosario de indicadores")
    ).to_be_visible()
    expect(portal.locator(".indicator-glossary")).to_have_count(0)
    assert portal.evaluate(
        "document.documentElement.scrollWidth <= window.innerWidth"
    )


def test_ranking_uses_account_logo_without_date_titles(portal, served):
    from io import BytesIO

    from PIL import Image

    from apps.portal.models import AccountLogo

    picture = BytesIO()
    Image.new("RGB", (50, 50), "green").save(picture, "PNG")
    AccountLogo.objects.create(
        key="heineken mexico",
        account="Heineken México",
        image=picture.getvalue(),
    )
    portal.goto(portal.base + PAGE)
    expect(portal.locator(".ranking-card.healthy h3")).to_have_text(
        "Cuentas sanas"
    )
    expect(portal.locator(".ranking-card.unhealthy h3")).to_have_text(
        "Cuentas no sanas"
    )
    image = portal.locator("#healthy-financial-accounts .ranking-logo img")
    expect(image).to_be_visible()
    assert image.evaluate("node=>node.complete && node.naturalWidth>0")
    portal.select_option("#ranking-sort", "revenue")
    expect(
        portal.locator("#unhealthy-financial-accounts .ranking-logo img")
    ).to_be_visible()
    expect(
        portal.locator("#healthy-financial-accounts .ranking-logo")
    ).to_have_attribute("data-initials", "GRA")
    folder = Path("tmp/design/ranking-logos")
    folder.mkdir(parents=True, exist_ok=True)
    portal.locator(".ranking-section").screenshot(
        path=str(folder / "rankings.png")
    )


def test_failed_preparation_keeps_figures_without_a_manual_refresh_control(
    portal, datos, enforced_csp
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
    requests = []

    def refresh(route):
        requests.append(route.request.method)
        reply(route, {"state": "failed", "blocks": {}})

    portal.route(REFRESH, refresh)
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#executive-cut-status")).to_have_text(
        "No se pudo completar. Se conserva el corte mostrado."
    )
    expect(portal.locator("#executive-revenue")).to_have_text("1.89M")
    expect(portal.locator("#executive-prepare")).to_have_count(0)
    assert requests == ["GET"]


def test_finance_detail_reconciles_and_capacity_excess_has_clear_label(
    portal, served, enforced_csp
):
    figures = json.loads(json.dumps(FIGURES))
    figures["finance"]["revenue"].update(collected=1290000, total=2397644.14)
    figures["operations"]["etc"] = -500
    figures["operations"]["capacity_consumed_hours"] = 6500
    portal.route(
        SCREEN_BARE,
        lambda r: reply(r, figures, {"loaded_at": "2026-10-22T10:00:00-06:00"}),
    )
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#executive-ops-balance-label")).to_have_text(
        "Capacidad consumida (h)"
    )
    expect(portal.locator("#executive-ops-etc")).to_have_text("6,500 h")
    expect(portal.locator("#executive-method-dialog")).to_be_hidden()
    expect(portal.locator("#executive-collected")).to_have_text("1.29M")
    expect(portal.locator("#executive-contracted")).to_have_text("2.39M")
    expect(portal.locator("#executive-gross-profit")).to_have_text("1.39M*")
    expect(portal.locator("#executive-cost-coverage")).to_contain_text(
        "1 completos · 0 parciales · 1 sin costo disponible · "
        "2 proyectos incluidos"
    )
    folder = Path("tmp/design/revision-finanzas")
    folder.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(folder / "resumen.png"))
    ids = portal.locator("[id]").evaluate_all(
        "nodes => nodes.map(node => node.id)"
    )
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("width", [1450, 390])
def test_png_export_preserves_icons_and_excludes_calendar_and_help(
    portal, served, enforced_csp, width
):
    from PIL import Image

    from tests.e2e.conftest import watch

    problems = watch(portal)
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#executive-revenue")).to_have_text("1.89M")
    expect(portal.locator(".executive-currency-label")).to_have_text(
        ["Importes en USD", "Importes en USD"]
    )
    portal.locator("#executive-date-picker summary").click()
    portal.keyboard.press("Escape")
    portal.locator(".monthly-panel-info summary").click()
    portal.locator(".ranking-help summary").click()
    portal.add_script_tag(
        url=portal.base + "/static/app/vendor/html2canvas-1.4.1.min.js"
    )
    portal.evaluate("""() => {
      const capture = window.html2canvas;
      window.html2canvas = (target, options) => capture(target, {...options,
        async onclone(doc) {
          await options.onclone(doc);
          window.iconPixels = [...doc.querySelectorAll(
            '.executive-metric-art')].map(icon => ({
              tag: icon.tagName, width: icon.width, height: icon.height,
              box: [icon.getBoundingClientRect().x,
                icon.getBoundingClientRect().y,
                icon.getBoundingClientRect().width,
                icon.getBoundingClientRect().height],
              colored: [...icon.getContext('2d').getImageData(
                0, 0, icon.width, icon.height).data]
                .filter((value, index) => index % 4 === 3 && value > 0).length,
          }));
          const origin = doc.getElementById(target.id)
            .getBoundingClientRect();
          window.captureOrigin = [origin.x, origin.y, origin.width];
          window.captureProof = {
            calendar: doc.querySelectorAll(
              '#executive-date-picker form').length,
            help: doc.querySelectorAll(
              '.monthly-panel-info > div, .ranking-help > p').length,
            icons: doc.querySelectorAll('.executive-metric-art').length,
            unresolved: [...doc.querySelectorAll('.executive-cards svg *')]
              .some(node => ['fill', 'stroke', 'stop-color'].some(name =>
                ['var(', 'currentColor'].some(token =>
                  (node.getAttribute(name) || '').includes(token)))),
          };
        }
      });
    }""")
    folder = Path("tmp/design/executive-export")
    folder.mkdir(parents=True, exist_ok=True)
    with portal.expect_download(timeout=60000) as download:
        portal.locator("#executive-capture-actions .capture-button").click()
    path = folder / f"resumen-{width}.png"
    download.value.save_as(path)
    icons = portal.evaluate("window.iconPixels")
    assert len(icons) == 5
    assert all(icon["colored"] > 100 for icon in icons)
    assert portal.evaluate("window.captureProof") == {
        "calendar": 0,
        "help": 0,
        "icons": 5,
        "unresolved": False,
    }
    with Image.open(path) as image:
        assert image.width >= width
        assert image.height > image.width
        origin_x, origin_y, content_width = portal.evaluate(
            "window.captureOrigin"
        )
        scale = image.width / content_width
        for icon in icons:
            x, y, box_width, box_height = icon["box"]
            crop = image.crop(
                (
                    round((x - origin_x) * scale),
                    round((y - origin_y) * scale),
                    round((x - origin_x + box_width) * scale),
                    round((y - origin_y + box_height) * scale),
                )
            ).convert("RGB")
            assert (
                sum(
                    max(pixel) - min(pixel) > 12 and min(pixel) < 242
                    for pixel in crop.getdata()
                )
                > 100
            )
    expect(portal.locator("#executive-date-picker")).not_to_have_attribute(
        "open", ""
    )
    expect(portal.locator("#executive-revenue")).to_have_text("1.89M")
    expect(
        portal.locator("#executive-capture-actions .capture-status")
    ).to_have_text("Captura descargada.")
    assert problems == []
