"""Capacidad diaria: API, matriz, recursos y misma apariencia anterior."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.portal.test_capacity import make_row

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/capacidad-instalada/?mes=2026-10"


@pytest.fixture
def daily(monkeypatch, datos):
    calls = []
    rows = [
        make_row(idProyecto="P1", iteration=""),
        make_row(
            recurso="Luis", idProyecto="P2", tecnologia="QA", iteration=""
        ),
    ]

    def base(_reader, month, _today):
        return {
            "ok": True,
            "mes": month,
            "filas": rows,
            "bandaColumna": "Octubre",
            "fuentes": ["Recursos", "MPB"],
        }

    def project(args, *unused):
        pid, iteration, month, force = args
        calls.append(args)
        person = "ana perez" if pid == "P1" else "luis"
        return {
            "ok": True,
            "inicio": month + "-01",
            "fin": month + "-28",
            "daily": {person: {month + "-01": 10 if pid == "P1" else 6}},
        }

    monkeypatch.setattr("apps.capacidad.rpc.load_capacity_base", base)
    monkeypatch.setattr("apps.capacidad.rpc.load_project_data", project)
    return calls


def ready(portal):
    expect(portal.locator("#ci-status")).to_contain_text(
        "Mes 2026-10 · Recursos + MPB + Clockify"
    )


@pytest.mark.parametrize(
    "saved_link", [False, True], ids=["current_url", "obsolete_url"]
)
def test_matrix_filters_resources_csv_and_refresh(portal, daily, saved_link):
    errors = []
    portal.on("pageerror", lambda error: errors.append(str(error)))
    portal.goto(portal.base + PAGE + ("&vista=anterior" if saved_link else ""))
    ready(portal)
    expect(portal.locator(".ci-stat strong")).to_have_text(
        ["2", "352 h", "16 h", "338 h", "1"]
    )
    assert portal.locator("script[src*='gas_shim']").count() == 0
    expect(portal.locator(".ci-table tbody tr")).to_have_count(2)
    portal.locator("#ci-search").fill("Ana")
    expect(portal.locator(".ci-table tbody tr")).to_have_count(1)
    expect(portal.locator(".ci-table")).not_to_contain_text("Luis")
    with portal.expect_download() as download:
        portal.get_by_role("button", name="↓ Exportar CSV").click()
    text = Path(download.value.path()).read_text(encoding="utf-8-sig")
    assert "Ana Perez" in text and "Luis" not in text
    assert "01/10/2026" in text
    portal.locator("#ci-search").fill("")
    portal.get_by_role("button", name="Capacidad por recurso").click()
    expect(portal.locator(".ci-resource")).to_have_count(2)
    expect(portal.locator(".ci-resource").first).to_contain_text(
        "Sobre jornada"
    )
    portal.locator("#ci-jornada").fill("6")
    portal.locator("#ci-jornada").dispatch_event("change")
    expect(portal.locator(".ci-stat strong").nth(1)).to_have_text("264 h")
    with portal.expect_response(
        lambda response: (
            "/diaria/proyecto/" in response.url
            and "actualizar=1" in response.url
        )
    ):
        portal.get_by_role("button", name="↻ Actualizar datos").click()
    ready(portal)
    assert any(args[3] for args in daily)
    assert not errors


def test_change_month_and_partial_failure(portal, daily, monkeypatch):
    def failed(args, *unused):
        return {"ok": False, "error": "Clockify no disponible"}

    monkeypatch.setattr("apps.capacidad.rpc.load_project_data", failed)
    portal.goto(portal.base + PAGE)
    ready(portal)
    expect(portal.locator(".ci-stat strong").nth(3)).to_have_text("Pendiente")
    expect(portal.locator(".ci-alert")).to_contain_text(
        "totales de horas son parciales"
    )
    expect(portal.locator(".ci-day.pending").first).to_have_text("—")
    portal.locator("#ci-month").fill("2026-09")
    expect(portal.locator("#ci-status")).to_contain_text("Mes 2026-09")
    expect(portal.locator(".ci-section-head h3")).to_contain_text("2026-09")


def test_failed_base_can_be_retried_without_rpc(portal, daily, monkeypatch):
    from apps.capacidad import rpc

    original = rpc.load_capacity_base
    attempts = []

    def base(*args):
        attempts.append(1)
        if len(attempts) == 1:
            return {"ok": False, "error": "Hojas no disponibles"}
        return original(*args)

    monkeypatch.setattr(rpc, "load_capacity_base", base)
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#ci-status")).to_contain_text("Hojas no disponibles")
    portal.get_by_role("button", name="↻ Actualizar datos").click()
    ready(portal)
    expect(portal.locator(".ci-table tbody tr")).to_have_count(2)


def test_project_reads_use_the_month_resolved_by_the_source(
    portal, daily, monkeypatch
):
    from apps.capacidad import rpc

    original = rpc.load_capacity_base

    def base(reader, month, today):
        return original(reader, "2026-09", today)

    monkeypatch.setattr(rpc, "load_capacity_base", base)
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#ci-status")).to_contain_text("Mes 2026-09")
    expect(portal.locator("#ci-month")).to_have_value("2026-09")
    assert daily and all(args[2] == "2026-09" for args in daily)


def test_pagination_and_resource_names_are_plain_text(
    portal, daily, monkeypatch
):
    unsafe = '<img src=x onerror="window.injected=true">'

    def base(_reader, month, _today):
        rows = [
            make_row(recurso=f"Persona {i}", idProyecto="", iteration="")
            for i in range(30)
        ]
        rows.append(make_row(recurso=unsafe, idProyecto="", iteration=""))
        return {
            "ok": True,
            "mes": month,
            "filas": rows,
            "bandaColumna": "Octubre",
            "fuentes": ["Recursos", "MPB"],
        }

    monkeypatch.setattr("apps.capacidad.rpc.load_capacity_base", base)
    portal.goto(portal.base + PAGE)
    ready(portal)
    expect(portal.locator(".ci-table tbody tr")).to_have_count(30)
    portal.get_by_role("button", name="Siguiente →").click()
    expect(portal.locator(".ci-table tbody tr")).to_have_count(1)
    expect(portal.locator(".ci-table tbody")).to_contain_text(unsafe)
    assert portal.locator(".ci-table img").count() == 0
    portal.locator("#ci-search").fill("Persona 0")
    expect(portal.locator(".ci-foot")).to_contain_text("Página 1 de 1")
    expect(portal.locator(".ci-table tbody")).to_contain_text("Persona 0")


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("view", ["matrix", "people"])
def test_layout_keeps_approved_reference(
    portal, daily, width, view, snapshot, enforced_csp
):
    from tests.e2e.conftest import watch

    problems = watch(portal)
    portal.set_viewport_size({"width": width, "height": 1000})
    selectors = [
        ".top",
        ".capacity-detail-page",
        ".ci-head",
        ".ci-filter-card",
        ".ci-field",
        ".ci-kpis",
        ".ci-card",
        ".ci-section-head",
        ".ci-table",
        ".ci-resource",
        ".ci-info",
    ]

    def capture():
        return portal.evaluate(
            """sels => sels.map(s => [...document.querySelectorAll(s)]
              .map(e => {
              const r = e.getBoundingClientRect(), c = getComputedStyle(e);
              return {box: ['x','y','width','height'].map(k =>
                Math.round(r[k] * 10) / 10),
                css: ['fontSize','color','paddingTop','paddingBottom',
                  'marginTop','marginBottom'].map(k => c[k])};
            }))""",
            selectors,
        )

    output = Path(f"tmp/migration/capacity_daily/{width}/{view}")
    output.mkdir(parents=True, exist_ok=True)
    portal.goto(portal.base + PAGE)
    ready(portal)
    if view == "people":
        portal.get_by_role("button", name="Capacidad por recurso").click()
    snapshot(
        f"capacity_daily_layout_{view}_{width}",
        dict(zip(selectors, capture(), strict=True)),
    )
    portal.screenshot(path=str(output / "current.png"), full_page=True)
    assert problems == []
