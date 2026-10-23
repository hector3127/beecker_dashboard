"""GSE por área: mismo conjunto de datos en la vista anterior y la modular."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/operativa/facturabilidad/area/?anio=2026&periodo=anio"


@pytest.fixture
def area(monkeypatch, datos):
    calls = []
    records = [
        {
            "id": "1",
            "mes": "2026-01",
            "area": "DEV",
            "recurso": "Ana",
            "proyecto": "AER.1",
            "banda": "Senior",
            "categoria": "Facturable",
            "tipo": "Facturable",
            "servicio": "AER",
            "categorias": ["Facturable"],
            "horas": 84,
        },
        {
            "id": "2",
            "mes": "2026-02",
            "area": "DEV",
            "recurso": "Ana",
            "proyecto": "IXB.2",
            "banda": "Senior",
            "categoria": "Vacaciones",
            "tipo": "No Facturables",
            "servicio": "IxB",
            "categorias": ["No Facturables", "Vacaciones"],
            "horas": 20,
        },
        {
            "id": "3",
            "mes": "2026-02",
            "area": "QA",
            "recurso": "Eva",
            "proyecto": "TYM.3",
            "banda": "Baja",
            "categoria": "Inversión Operaciones",
            "tipo": "Facturable",
            "servicio": "TYM",
            "categorias": ["Facturable", "Inversión Operaciones"],
            "horas": 42,
        },
    ]

    def batch(year, selected_area, cursor, expected_rows, force):
        calls.append((year, selected_area, cursor, expected_rows, force))
        return {
            "ok": True,
            "records": [
                r
                for r in records
                if not selected_area or r["area"] == selected_area
            ],
            "cursor": 3,
            "total": 3,
            "done": True,
            "bandas": [
                {"recurso": "Ana", "bandas": ["Senior"] * 12},
                {"recurso": "Eva", "bandas": ["Baja"] * 12},
            ],
        }

    monkeypatch.setattr(
        "apps.gse.rpc.get_gse_areas",
        lambda: {"ok": True, "areas": ["DEV", "QA"]},
    )
    # The RPC registry stores the callable; patch its underlying service too.
    monkeypatch.setattr("apps.gse.rpc.list_areas", lambda *_: ["DEV", "QA"])
    monkeypatch.setattr("apps.gse.rpc.build_sheet_repository", lambda: None)
    monkeypatch.setattr("apps.gse.rpc.build_context", lambda *_: None)
    monkeypatch.setattr(
        "apps.gse.rpc.get_batch", lambda ctx, args: batch(*args, False)
    )
    monkeypatch.setattr("apps.gse.rpc.get_gse_batch", batch)
    monkeypatch.setattr("apps.gse.rpc.refresh_sheet_reads", lambda *_: None)
    monkeypatch.setattr(
        "apps.gse.rpc.read_gse_result_cache",
        lambda *_: {"ok": True, "cached": False},
    )
    monkeypatch.setattr(
        "apps.gse.rpc.save_gse_result_cache", lambda *_: {"ok": True}
    )

    class Cache:
        def read(self, *_):
            return {"ok": True, "cached": False}

        def save(self, *_):
            return {"ok": True}

    monkeypatch.setattr("apps.gse.rpc.build_result_cache", Cache)
    monkeypatch.setattr("apps.portal.pages.anterior_disponible", lambda: True)
    return calls


def ready(page):
    expect(page.locator("#gse-status")).to_contain_text("Selecciona el área")


def load(page):
    page.locator("#gse-load").click()
    expect(page.locator("#gse-status")).to_contain_text("Base leída")


def test_general_sections_filters_and_exports(portal, area):
    errors = []
    portal.on("pageerror", lambda e: errors.append(str(e)))
    portal.goto(portal.base + PAGE)
    ready(portal)
    assert portal.locator("script[src*='gas_shim']").count() == 0
    load(portal)
    expect(portal.locator(".gm-kpis strong").nth(3)).to_have_text("126")
    portal.locator(".gse-sections button").filter(
        has_text="Detalle recurso"
    ).click()
    expect(portal.locator(".gse-resource-table tbody tr")).to_have_count(3)
    portal.locator("#gse-resource-search").fill("Ana")
    expect(portal.locator(".gse-resource-table tbody tr")).to_have_count(2)
    with portal.expect_download() as result:
        portal.locator("#gse-resource-export").click()
    csv = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert "Ana" in csv and "Eva" not in csv
    portal.locator(".gse-sections button").filter(has_text="KPIs").click()
    expect(portal.locator(".gk-kpis")).to_contain_text("Facturabilidad anual")
    portal.locator(".gse-sections button").filter(has_text="% Recurso").click()
    expect(portal.locator(".gpr-table tbody tr")).to_have_count(2)
    portal.locator("#gse-percent-search").fill("Eva")
    expect(portal.locator(".gpr-table tbody tr")).to_have_count(1)
    portal.locator(".gse-sections button").filter(
        has_text="Detalle HRS"
    ).click()
    expect(portal.locator(".ghr-kpis")).to_contain_text("146")
    portal.get_by_role(
        "button", name="Ver todos los servicios", exact=True
    ).click()
    expect(
        portal.get_by_role(
            "button", name="Ocultar TYM, IxB, SaaS y RaaS de Enero", exact=True
        )
    ).to_be_visible()
    assert not errors


@pytest.mark.parametrize("width", [1450, 390])
@pytest.mark.parametrize(
    "section",
    ["General", "Detalle recurso", "KPIs", "% Recurso", "Detalle HRS"],
)
def test_matches_previous(portal, area, width, section):
    portal.set_viewport_size({"width": width, "height": 1000})
    selectors = [
        ".pgh",
        ".tabs",
        ".gm-hero",
        ".gse-tools",
        ".gm-kpi",
        ".gm-card",
        ".gm-table",
        ".gse-resource-dialog",
        ".gse-resource-table",
        ".gpr-table",
        ".ghr-kpi",
        ".ghr-table",
        "#gse-section-content",
    ]

    def measure():
        return portal.evaluate(
            """selectors=>selectors.map(s=>
                  [...document.querySelectorAll(s)].map(el=>{
                    const b=el.getBoundingClientRect(),c=getComputedStyle(el);
                    return {box:['x','y','width','height'].map(k=>
                      Math.round(b[k]*10)/10),
                      text:el.tagName==='TABLE'?el.innerText:null,
                      css:['fontSize','fontWeight','padding','margin',
                        'color','boxShadow'].map(k=>c[k])};
                  }))""",
            selectors,
        )

    output = Path(
        f"tmp/migration/billability_area/{width}/{section.replace(' ', '_')}"
    )
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for mode in ["previous", "current"]:
        # La navegación anterior se oculta por CSS en pantallas pequeñas.
        # Seleccionamos el apartado en escritorio antes de medirlo en móvil.
        portal.set_viewport_size({"width": 1450, "height": 1000})
        portal.goto(
            portal.base
            + PAGE
            + ("&vista=anterior" if mode == "previous" else "")
        )
        ready(portal)
        load(portal)
        portal.locator(".gse-sections button").filter(has_text=section).click()
        portal.set_viewport_size({"width": width, "height": 1000})
        portal.mouse.move(0, 0)
        results.append(measure())
        portal.screenshot(path=str(output / (mode + ".png")), full_page=True)
    for selector, before, after in zip(selectors, *results, strict=True):
        assert before == after, (selector, before, after)


@pytest.mark.parametrize("width", [1450, 390])
def test_selected_area_matches_previous(portal, area, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    output = Path(f"tmp/migration/billability_area/{width}/selected")
    output.mkdir(parents=True, exist_ok=True)
    results = []
    for mode in ["previous", "current"]:
        portal.goto(
            portal.base
            + PAGE
            + ("&vista=anterior" if mode == "previous" else "")
        )
        ready(portal)
        load(portal)
        portal.locator("#gse-area").select_option("DEV")
        expect(portal.locator(".ga-kpis")).to_contain_text("104")
        portal.mouse.move(0, 0)
        results.append(
            portal.evaluate("""()=>{
          const selectors=['.ga-kpi','.ga-charts','.ga-holidays','.ga-report'];
          return selectors.map(s=>[...document.querySelectorAll(s)].map(el=>{
            const b=el.getBoundingClientRect(),c=getComputedStyle(el);
            return {box:[b.x,b.y,b.width,b.height].map(v=>Math.round(v*10)/10),
              css:[c.fontSize,c.color,c.padding]};
          })).concat([document.querySelector('.ga-table').innerText]);
        }""")
        )
        portal.screenshot(path=str(output / (mode + ".png")), full_page=True)
    assert results[0] == results[1]


def test_area_day_holidays_filters_and_force(portal, area):
    portal.goto(portal.base + PAGE)
    ready(portal)
    load(portal)
    portal.locator("#gse-area").select_option("DEV")
    expect(portal.locator(".ga-kpi strong").first).to_have_text("104")
    portal.locator("#gse-day").fill("6")
    portal.locator("#gse-day").press("Tab")
    expect(portal.locator(".ga-kpi strong").nth(1)).to_have_text("240")
    portal.get_by_label("Festivos Enero", exact=True).fill("0")
    portal.get_by_label("Festivos Enero", exact=True).press("Tab")
    expect(portal.locator(".ga-kpi strong").nth(1)).to_have_text("246")
    portal.get_by_role("button", name="Porcentajes", exact=True).click()
    expect(
        portal.locator(".ga-table").get_by_text("Vacaciones", exact=True)
    ).to_have_count(0)
    with portal.expect_download() as result:
        portal.locator("#gse-csv").click()
    content = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert '"Total horas registradas","84","20"' in content
    portal.locator("#gse-refresh").click()
    expect(portal.locator("#gse-status")).to_contain_text("Base leída")
    assert any(call[-1] for call in area)


def test_partial_batches_deduplicate_and_can_retry(portal, area, monkeypatch):
    original = __import__(
        "apps.gse.rpc", fromlist=["get_gse_batch"]
    ).get_gse_batch
    calls = []

    def batches(year, selected_area, cursor, total, force):
        calls.append(cursor)
        if len(calls) == 1:
            return {"ok": False, "error": "Sheets interrumpido"}
        result = original(year, selected_area, cursor, total, force)
        if not cursor:
            result["done"] = False
            result["cursor"] = 1
        return result

    monkeypatch.setattr("apps.gse.rpc.get_gse_batch", batches)
    portal.goto(portal.base + PAGE)
    ready(portal)
    portal.locator("#gse-load").click()
    expect(portal.locator("#gse-status")).to_contain_text("Sheets interrumpido")
    load(portal)
    expect(portal.locator(".gm-kpis strong").nth(3)).to_have_text("126")
    assert calls == [0, 0, 1]


def test_area_failure_retries_without_requesting_hours(
    portal, area, monkeypatch
):
    calls = []

    def areas():
        calls.append(1)
        return (
            {"ok": False, "error": "Bandas no disponible"}
            if len(calls) == 1
            else {"ok": True, "areas": ["DEV"]}
        )

    monkeypatch.setattr("apps.gse.rpc.get_gse_areas", areas)
    portal.goto(portal.base + PAGE)
    expect(portal.locator("#gse-status")).to_contain_text(
        "Bandas no disponible"
    )
    portal.locator("#gse-load").click()
    ready(portal)
    assert not area


def test_ids_continue_the_report_and_return(portal, area, monkeypatch):
    calls = []

    def ids(month, report):
        calls.append((month, report))
        return (
            {"ok": True, "pending": True, "records": 10, "page": 1}
            if not report
            else {
                "ok": True,
                "guardados": 2,
                "pendientes": 0,
                "fuente": "Reporte",
            }
        )

    monkeypatch.setattr("apps.gse.rpc.get_gse_clockify_ids", ids)
    portal.goto(portal.base + PAGE)
    ready(portal)
    portal.locator("#gse-detail").select_option("1")
    portal.locator("#gse-ids").click()
    expect(portal.locator("#gse-status")).to_contain_text("2")
    assert calls == [("2026-02", False), ("2026-02", True)]
    portal.get_by_role("link", name="← Regresar a Operativa").click()
    portal.wait_for_url("**/operativa/")


def test_clockify_source_keeps_pending_and_failed_months(
    portal, area, monkeypatch
):
    calls = []

    def month(value, source, force, selected_area):
        calls.append((value, source, force, selected_area))
        if (
            value.endswith("01")
            and calls.count((value, source, force, selected_area)) == 1
        ):
            return {"ok": True, "pending": True, "records": 1, "page": 1}
        if value.endswith("02"):
            return {"ok": False, "error": "Clockify no disponible"}
        return {"ok": True, "mes": value, "areas": [], "detalle": []}

    monkeypatch.setattr("apps.gse.rpc.get_gse_month", month)
    portal.goto(portal.base + PAGE)
    ready(portal)
    portal.locator("#gse-source").select_option("api")
    portal.locator("#gse-load").click()
    expect(portal.locator("#gse-status")).to_contain_text("Consulta terminada")
    expect(portal.locator("#gse-errors")).to_contain_text(
        "Clockify no disponible"
    )
    assert len([c for c in calls if c[0] == "2026-01"]) == 2
    assert all(c[1] == "api" for c in calls)
    assert not area


def test_names_and_projects_are_text_not_markup(portal, area, monkeypatch):
    from apps.gse import rpc

    original = rpc.get_gse_batch
    hostile = '<img src=x onerror="window.injected=true">'

    def batch(*args):
        result = original(*args)
        result["records"][0] = {
            **result["records"][0],
            "recurso": hostile,
            "proyecto": hostile,
        }
        return result

    monkeypatch.setattr(rpc, "get_gse_batch", batch)
    portal.goto(portal.base + PAGE)
    ready(portal)
    load(portal)
    portal.locator(".gse-sections button").filter(
        has_text="Detalle recurso"
    ).click()
    expect(portal.locator(".gse-resource-table")).to_contain_text(hostile)
    assert portal.locator("#gse-panel img").count() == 0
    assert portal.evaluate("window.injected===undefined")


def test_annual_cache_avoids_loading_batches(portal, area, monkeypatch):
    snapshot = {
        "ok": True,
        "cached": True,
        "savedAt": "2026-10-21T12:00:00Z",
        "scopeArea": "",
        "bandas": [],
        "data": {
            "2026-01": {
                "ok": True,
                "areas": [
                    {
                        "area": "DEV",
                        "horas": 84,
                        "recursos": 1,
                        "categorias": {"Facturable": 84},
                        "personas": [{"nombre": "Ana"}],
                    }
                ],
                "detalle": [],
            }
        },
    }
    monkeypatch.setattr(
        "apps.gse.rpc.read_gse_result_cache", lambda *_: snapshot
    )
    portal.goto(portal.base + PAGE)
    ready(portal)
    portal.locator("#gse-load").click()
    expect(portal.locator("#gse-status")).to_contain_text(
        "Resultado desde caché"
    )
    expect(portal.locator(".gm-kpis strong").nth(3)).to_have_text("84")
    portal.locator("#gse-area").select_option("DEV")
    expect(portal.locator(".ga-kpi strong").first).to_have_text("84")
    assert not area
