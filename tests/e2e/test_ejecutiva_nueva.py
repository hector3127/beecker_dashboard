"""Business Overview nuevo en el navegador: tarjetas, periodo y alcance."""

import re
from urllib.parse import parse_qs, urlsplit

import pytest
from playwright.sync_api import expect

from apps.access.scope import AccessScope
from tests.e2e.test_acuerdos import browser_session

pytestmark = pytest.mark.django_db(transaction=True)

HOME = "/?vista=nueva"
SNAPSHOT = {
    "loaded_at": "2026-10-22T10:00:00-06:00",
    "revenue": {"invoiced": 1_897_644.14, "collections_percent": 80},
    "costs": {
        "cost": 400_000,
        "complete": False,
        "projects": [
            {"id": "P1", "cost": 100, "complete": False, "error": "Sin tarifa"},
            {"id": "P2", "cost": 300, "complete": True},
        ],
    },
    "commercial": {
        "won": 500_000,
        "won_count": 3,
        "delivery": 90_000,
        "open": 200_000,
    },
    "profitability": {
        "complete": False,
        "months": [
            {"month": "2026-01", "revenue": 100, "cost": 40},
            {"month": "2026-02", "revenue": 120, "cost": None},
        ],
    },
    "accounts": {
        "ranking_version": 4,
        "accounts": [
            {
                "name": "Acme",
                "revenue": 600,
                "gross_profit": 300,
                "margin": 50,
                "projects": 2,
            },
            {
                "name": "Beta",
                "revenue": 400,
                "gross_profit": 100,
                "margin": 25,
                "projects": 1,
            },
        ],
    },
}
OPERATIONS = {
    "projects": [],
    "partial": True,
    "etc": 1200,
    "advance": 40,
    "fte": 1.5,
    "facturability": 71,
    "investment_operational": 300,
    "missing_budget_ids": ["X1"],
    "pending_ids": [],
}


@pytest.fixture
def cut(monkeypatch, datos):
    monkeypatch.setattr(
        "apps.portal.services.financial_cache.cached_financial_snapshot",
        lambda: SNAPSHOT,
    )
    monkeypatch.setattr(
        "apps.portal.services.executive_operations.cached_operations_snapshot",
        lambda: OPERATIONS,
    )


def test_las_tarjetas_muestran_las_cifras_del_corte(portal, cut):
    portal.goto(portal.base + HOME)
    cards = portal.locator("#exec-cards")

    expect(cards).to_contain_text(
        "1.89M"
    )  # facturación, truncada como el resto
    expect(cards).to_contain_text("80%")
    expect(cards).to_contain_text("1,200 h*")  # corte parcial
    expect(cards).to_contain_text("500K")
    # 1.897M - 0.4M = 78.9% -> 79%, con asterisco por costos parciales
    expect(cards).to_contain_text("79%*")
    expect(portal.locator("#exec-monthly")).to_contain_text("Margen parcial")


def test_los_costos_pendientes_se_listan_en_una_ventana(portal, cut):
    portal.goto(portal.base + HOME)

    portal.get_by_role("button", name="1 costos pendientes").click()
    dialog = portal.get_by_role("dialog", name="Pendientes de costos")

    expect(dialog).to_contain_text("P1")
    expect(dialog).to_contain_text("Sin tarifa")
    expect(dialog).not_to_contain_text("P2")


def test_fuentes_y_calculo_salen_del_diccionario(portal, cut):
    portal.goto(portal.base + HOME)
    portal.get_by_role(
        "button", name="Ver fuentes y cálculo de Comercial"
    ).click()

    dialog = portal.get_by_role("dialog", name=re.compile("Fuentes y cálculo"))
    expect(dialog).to_contain_text("Trabajo por entregar")
    expect(dialog).to_contain_text("Fuente / validación")
    expect(
        dialog.get_by_role("link", name="Abrir glosario completo")
    ).to_be_visible()


def test_aplicar_un_rango_rapido_pone_el_periodo_en_la_url(portal, cut):
    portal.goto(portal.base + HOME)
    portal.locator("#period-picker summary").click()
    portal.get_by_role("button", name="Este año").click()
    portal.get_by_role("button", name="Aplicar periodo").click()

    portal.wait_for_url(re.compile(r"periodo=rango"))
    query = parse_qs(urlsplit(portal.url).query)
    assert query["desde"][0].endswith("-01-01")
    assert query["hasta"][0].endswith("-12-31")


def test_un_rango_invertido_no_se_envia(portal, cut):
    portal.goto(portal.base + HOME)
    portal.locator("#period-picker summary").click()
    portal.get_by_label("Desde").fill("2026-05-01")
    portal.get_by_label("Hasta").fill("2026-04-01")
    portal.get_by_role("button", name="Aplicar periodo").click()

    expect(
        portal.get_by_role("alert").filter(has_text="fecha final")
    ).to_be_visible()
    assert "desde=" not in portal.url


def test_con_alcance_limitado_no_hay_cifras_de_empresa_y_solo_sus_cuentas(
    portal, cut, enforced, client
):
    enforced(
        "ana",
        caps=frozenset({"view_executive", "view_agreements"}),
        scope=AccessScope.limited(accounts=["Beta"]),
    )
    browser_session(portal, client)
    portal.goto(portal.base + HOME)

    cards = portal.locator("#exec-cards")
    expect(cards).to_contain_text("no disponible para tu alcance")
    expect(cards).not_to_contain_text("1.89M")
    accounts = portal.locator("#exec-accounts")
    expect(accounts).to_contain_text("Beta")
    expect(accounts).not_to_contain_text("Acme")
    assert "1.89M" not in portal.content()
    assert "Acme" not in portal.content()


def test_los_acuerdos_de_todas_las_cuentas_se_agrupan_y_se_pueden_agregar(
    portal, cut, enforced, client
):
    from apps.portal.models import ExecutiveAgreement

    ExecutiveAgreement.objects.create(account="Acme", title="Revisar fase 2")
    enforced(
        "ana",
        caps=frozenset(
            {"view_executive", "view_agreements", "edit_agreements"}
        ),
    )
    browser_session(portal, client)
    portal.goto(portal.base + HOME)

    section = portal.locator("#executive-agreements")
    expect(section.locator(".agreement-group")).to_contain_text("Acme")
    expect(section).to_contain_text("Revisar fase 2")

    section.get_by_role("button", name="+ Agregar acuerdo o pendiente").click()
    form = section.locator("#agreement-form")
    form.get_by_label("Cuenta").select_option("Beta")
    form.get_by_label("Fecha de sesión").fill("2026-10-20")
    form.get_by_label("Título").fill("Definir renovación")
    form.get_by_role("button", name="Guardar").click()

    expect(section).to_contain_text("Guardado.")
    saved = ExecutiveAgreement.objects.get(title="Definir renovación")
    assert saved.account == "Beta"
