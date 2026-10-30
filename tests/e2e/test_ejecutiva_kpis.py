"""Línea base de Business Overview (glosario y comparación de cuentas) y de
KPIs de Delivery Managers, antes de migrarlos al frontend nuevo."""

import re
from datetime import date

import pytest
from playwright.sync_api import expect

from tests.e2e.conftest import rows, visible
from tests.portal.test_kpi_eva import stub_compliance_history

pytestmark = pytest.mark.django_db(transaction=True)

TODAY = date(2026, 10, 22)


def account(name, revenue, profit, margin, projects, slug, **extra):
    return {
        "name": name,
        "revenue": revenue,
        "gross_profit": profit,
        "margin": margin,
        "projects": projects,
        "url": f"/cuenta/{slug}/?nombre={name}",
        **extra,
    }


ACCOUNTS = [
    account("Grande", 1000, 100, 10, 4, "grande"),
    account("Pequeña", 100, 90, 90, 1, "pequena"),
    account("Sin facturación", 0, -20, None, 2, "sin-facturacion"),
    account("Heineken México", 500, 200, 40, 3, "heineken"),
    account("Parcial", 300, 50, 16, 1, "parcial", pending=2),
]


@pytest.fixture
def executive(monkeypatch, datos):
    """Business Overview con un corte de cuentas conocido."""
    monkeypatch.setattr(
        "apps.portal.services.financial_cache.cached_financial_snapshot",
        lambda: {
            "loaded_at": "2026-10-22T10:00:00-06:00",
            "accounts": {"accounts": ACCOUNTS, "ranking_version": 4},
        },
    )


def without_position(lines):
    """El número de fila cambia al invertir el orden; la cuenta no."""
    return [re.sub(r"^\d+\s+", "", line) for line in lines]


def groups(portal):
    return {
        kind: rows(portal.locator(f"#{kind}-financial-accounts"))
        for kind in ("healthy", "unhealthy")
    }


def test_glossary_opens_with_the_three_groups_and_the_dictionary_link(
    portal, executive, snapshot
):
    portal.goto(portal.base + "/")
    glossary = portal.locator(".executive-glossary")
    expect(glossary.locator(".executive-glossary-grid")).to_be_hidden()

    glossary.get_by_text("¿Qué significa cada indicador?").click()

    expect(glossary.locator(".executive-glossary-grid")).to_be_visible()
    assert glossary.locator("h2").all_inner_texts() == [
        "Financiera",
        "Operaciones",
        "Comercial",
    ]
    link = glossary.get_by_role(
        "link", name="Ver fórmulas, fuentes y validaciones"
    )
    assert link.get_attribute("href") == "/diccionario-datos/"
    snapshot("ejecutiva_glosario", {"glosario": visible(glossary)})


def test_account_comparison_searches_sorts_and_keeps_the_url(
    portal, executive, snapshot
):
    portal.goto(portal.base + "/")
    coverage = portal.locator("#ranking-coverage")
    expect(coverage).to_contain_text("5 cuentas comparadas por utilidad bruta")
    assert (
        portal.locator("#healthy-account-count").inner_text()
        == "3 de 3 cuentas"
    )
    assert (
        portal.locator("#unhealthy-account-count").inner_text()
        == "2 de 2 cuentas"
    )
    default = groups(portal)

    portal.get_by_label("Comparar por").select_option("margin")
    expect(coverage).to_contain_text("4 cuentas comparadas por margen bruto")
    expect(coverage).to_contain_text("1 sin dato para este criterio")
    by_margin = groups(portal)
    assert "ranking_criterio=margin" in portal.url
    # «Sin facturación» no tiene margen: no entra a ningún grupo, ni como cero.
    assert "Sin facturación" not in " ".join(
        by_margin["healthy"] + by_margin["unhealthy"]
    )

    heading = portal.locator(".ranking-card.healthy").get_by_role(
        "button", name=re.compile("Margen bruto")
    )
    heading.click()
    assert without_position(groups(portal)["healthy"]) == list(
        reversed(without_position(by_margin["healthy"]))
    )
    assert "ranking_healthy=ascending" in portal.url

    portal.get_by_label("Buscar cuenta").fill("mexico")  # sin acentos
    expect(coverage).to_contain_text("1 cuenta comparada")
    assert "ranking_buscar=mexico" in portal.url
    assert (
        "Heineken" in portal.locator("#healthy-financial-accounts").inner_text()
    )

    snapshot(
        "ejecutiva_comparacion",
        {"por_defecto": default, "por_margen": by_margin},
    )


def test_comparison_state_is_restored_from_the_url(portal, executive):
    portal.goto(
        portal.base
        + "/?ranking_buscar=gr&ranking_criterio=revenue"
        + "&ranking_healthy=ascending"
    )

    expect(portal.get_by_label("Buscar cuenta")).to_have_value("gr")
    expect(portal.get_by_label("Comparar por")).to_have_value("revenue")
    expect(portal.locator("#ranking-coverage")).to_contain_text("facturación")


def test_entering_an_account_and_coming_back_keeps_search_and_order(
    portal, executive
):
    portal.goto(portal.base + "/")
    portal.get_by_label("Comparar por").select_option("revenue")
    portal.get_by_label("Buscar cuenta").fill("mexico")
    expect(portal.locator("#ranking-coverage")).to_contain_text(
        "1 cuenta comparada"
    )

    portal.locator("#healthy-financial-accounts").get_by_role(
        "link", name=re.compile("Heineken")
    ).click()
    portal.wait_for_url(re.compile(r"/cuenta/heineken-mexico/"))
    assert "volver=" in portal.url

    portal.get_by_role("link", name=re.compile("^← Regresar a")).click()
    portal.wait_for_url(re.compile(r"ranking_buscar=mexico"))
    expect(portal.get_by_label("Buscar cuenta")).to_have_value("mexico")
    expect(portal.get_by_label("Comparar por")).to_have_value("revenue")
    expect(portal.locator("#ranking-coverage")).to_contain_text("facturación")


def test_without_the_full_list_the_comparison_says_it_is_pending(
    portal, datos, monkeypatch
):
    monkeypatch.setattr(
        "apps.portal.services.financial_cache.cached_financial_snapshot",
        lambda: {"loaded_at": "2026-10-22T10:00:00-06:00"},
    )
    portal.goto(portal.base + "/")

    expect(portal.locator("#ranking-coverage")).to_contain_text(
        "pendiente de preparar"
    )
    expect(portal.get_by_label("Buscar cuenta")).to_be_disabled()


# ---------- KPIs de Delivery Managers ----------


@pytest.fixture
def kpis(monkeypatch, datos):
    from django.utils import timezone

    monkeypatch.setattr(timezone, "localdate", lambda: TODAY)
    stub_compliance_history(monkeypatch, TODAY)


def test_kpis_open_on_the_whole_year_with_tp_t_c_history(
    portal, kpis, snapshot
):
    portal.goto(portal.base + "/operativa/kpis-delivery-managers/")

    month = portal.locator("#kpi-month-history")
    quarter = portal.locator("#kpi-quarter-history")
    expect(month).to_be_visible()
    subheaders = (
        month.locator("thead tr").nth(1).locator("th").all_inner_texts()
    )
    assert subheaders[:3] == ["TP", "T", "C"]
    assert (
        month.locator("thead tr").nth(0).locator("th").first.inner_text()
        == "DM"
    )
    first_quarter = quarter.locator("thead th").all_inner_texts()[1]
    assert first_quarter.startswith("T1")
    snapshot(
        "kpis_dm_historico",
        {"mensual": rows(month), "trimestral": rows(quarter)},
    )


def test_kpis_explain_the_units_without_changing_the_numbers(portal, kpis):
    portal.goto(portal.base + "/operativa/kpis-delivery-managers/")

    note = portal.locator(".kpi-definition-note")
    note.get_by_text("Cómo interpretar TP, T y C en esta pantalla").click()
    expect(note).to_contain_text("T: proyectos con desviación ≤ 0 / TP × 100")
    expect(note).to_contain_text("C: proyectos con avance ≤ 100% / TP × 100")
    assert portal.locator(".kc .kl").all_inner_texts() == [
        "Cumplimiento en costo (C)",
        "Carga total (TP)",
        "Mayor proporción en tiempo",
        "Menor proporción en tiempo",
    ]
