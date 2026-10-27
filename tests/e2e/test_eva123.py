"""EVA 1–3 conservan tablas, filtros, cálculos y carga de históricos."""

from pathlib import Path
from types import SimpleNamespace

import pytest
from playwright.sync_api import expect

from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from tests.ejecutivo.test_aer_tym import build_mpb_row, build_values
from tests.portal.test_eva1 import sample_rows
from tests.portal.test_eva2 import make_row

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("screen", [1, 3])
@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("history", [False, True])
def test_eva13_keeps_approved_reference(
    portal, evas, screen, width, history, snapshot, enforced_csp
):
    from tests.e2e.conftest import watch

    problems = watch(portal)
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + f"/operativa/eva-{screen}/")
    prefix = "eva" if screen == 1 else "eva3"
    if screen == 3:
        expect(
            portal.locator('tr[data-project="AER.004"] [data-field="burn"]')
        ).to_have_text("20.25")
    if history:
        portal.locator(f"#{prefix}-closed-box summary").click()
        table_id = "eva-closed-table" if screen == 1 else "eva3-history-table"
        expect(portal.locator(f"#{table_id}")).to_be_visible()
        if screen == 3:
            expect(
                portal.locator(
                    'tr[data-closed-id="PENDING.AER"] '
                    '[data-closed-field="burn"]'
                )
            ).to_have_text("60.25")
    portal.evaluate("document.fonts.ready")
    portal.mouse.move(0, 0)
    selectors = [".pgh", ".tabs", ".card", "table", ".table-bottom"]
    measured = portal.evaluate(
        """selectors=>selectors.map(s=>[...document.querySelectorAll(s)].map(el=>{
          const b=el.getBoundingClientRect(),c=getComputedStyle(el);
          return {box:['x','y','width','height'].map(k=>Math.round(b[k]*10)/10),
            css:['fontSize','fontWeight','color','backgroundColor','padding',
              'margin'].map(k=>c[k]),text:el.tagName==='TABLE'?el.innerText:null};
        }))""",
        selectors,
    )
    key = f"eva{screen}_layout_{width}_{'history' if history else 'active'}"
    snapshot(key, dict(zip(selectors, measured, strict=True)))
    output = Path(f"tmp/migration/eva13/{key}.png")
    output.parent.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(output), full_page=True)
    assert not problems


@pytest.fixture
def evas(monkeypatch, datos):
    calls = {"ixb": 0, "aer": 0, "active": [], "closed": []}
    ixb = [
        make_row(cliente="Nestlé México"),
        make_row(
            idProyecto="IXB.2",
            servicio="IXB",
            status="Suspendido",
            deliveryManager="Mario",
            nombre="Proyecto suspendido",
        ),
    ]
    monkeypatch.setattr(
        "apps.portal.views.load_eva2",
        lambda: SimpleNamespace(view=build_eva2_view(ixb), error=""),
    )
    monkeypatch.setattr(
        "apps.portal.views.load_eva1",
        lambda *a, **kw: SimpleNamespace(
            view=build_eva1_view(sample_rows()), error=""
        ),
    )

    def closed_ixb():
        calls["ixb"] += 1
        return SimpleNamespace(
            view=build_eva2_view(
                [
                    make_row(
                        idProyecto="CLOSED.1",
                        cliente="Atlas Next Wave",
                        status="Cerrado",
                        budget=1000.5,
                        burn=900.25,
                        etc=100.25,
                        avance=90.025,
                    )
                ]
            ),
            error="",
        )

    monkeypatch.setattr("apps.portal.views.load_eva2_closed", closed_ixb)

    class Reader:
        def read_values(self, _):
            calls["aer"] += 1
            return build_values(
                build_mpb_row(
                    id="CLOSED.AER",
                    cliente="ACME",
                    nombre="Cerrado AER",
                    service="AER",
                    estatus="Completed",
                    inicio="2026-01-01",
                    fin="2026-09-30",
                    dm="Laura",
                    horas=100,
                    burn=120,
                ),
                build_mpb_row(
                    id="PENDING.AER",
                    cliente="ACME",
                    nombre="Sin consumo",
                    service="AER",
                    estatus="Cancelled",
                    inicio="2026-01-01",
                    fin="2026-09-30",
                    dm="Laura",
                    horas=50,
                ),
            )

    monkeypatch.setattr("core.sheets.factory.build_sheet_repository", Reader)

    def consumption(ids):
        calls["active"].append(ids)
        return {
            "ok": True,
            "items": [{"id": pid, "burn": 20.25} for pid in ids],
        }

    monkeypatch.setattr(
        "apps.portal.api.eva.get_aer_tym_consumption", consumption
    )
    monkeypatch.setattr(
        "apps.ejecutivo.rpc.build_sheet_repository", lambda: None
    )
    monkeypatch.setattr(
        "apps.ejecutivo.rpc.load_aer_tym_summary", lambda *_: {"filas": []}
    )
    monkeypatch.setattr(
        "apps.ejecutivo.rpc.build_clockify_loader", lambda *_: None
    )
    monkeypatch.setattr(
        "apps.ejecutivo.rpc.build_consumption_items",
        lambda ids, *args: consumption(ids)["items"],
    )

    def burn(pid):
        calls["closed"].append(pid)
        return {"burn": 60.25}

    monkeypatch.setattr("apps.portal.views.fill_closed_burn", burn)
    monkeypatch.setattr("apps.portal.api.eva.fill_closed_burn", burn)
    return calls


@pytest.mark.parametrize(
    "saved_link", [False, True], ids=["current_url", "obsolete_url"]
)
def test_eva1_filters_export_and_lazy_history(portal, evas, saved_link):
    portal.goto(
        portal.base
        + "/operativa/eva-1/"
        + ("?vista=anterior" if saved_link else "")
    )
    expect(portal.locator("#eva-table tbody tr")).to_have_count(2)
    assert not evas["ixb"]
    portal.locator("#eva-manager").select_option("Mario")
    expect(portal.locator("#eva-count")).to_have_text(
        "Mostrando 1 de 2 proyectos"
    )
    with portal.expect_download() as result:
        portal.locator("#eva-export").click()
    content = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert "IXB.2" in content and "AMK.008" not in content
    portal.locator("#eva-service").select_option("RaaS")
    expect(portal.locator("#eva-count")).to_have_text(
        "Mostrando 0 de 2 proyectos"
    )
    portal.locator("#eva-manager").select_option("")
    expect(portal.locator("#eva-count")).to_have_text(
        "Mostrando 1 de 2 proyectos"
    )
    portal.locator("#eva-from").fill("2027-01-01")
    portal.locator("#eva-from").press("Tab")
    expect(portal.locator("#eva-count")).to_have_text(
        "Mostrando 0 de 2 proyectos"
    )
    portal.locator("#eva-closed-box summary").click()
    expect(portal.locator("#eva-closed-table")).to_contain_text("CLOSED.1")
    assert evas["ixb"] == 1
    portal.locator("#eva-closed-box summary").click()
    portal.locator("#eva-closed-box summary").click()
    assert evas["ixb"] == 1
    expect(portal.locator("#eva-closed-table a").first).to_have_attribute(
        "href", "/proyectos/CLOSED.1/"
    )


def test_eva1_dates_apply_without_blur_and_survive_refresh(
    portal, evas, enforced_csp
):
    portal.goto(portal.base + "/operativa/eva-1/?volver=%2Foperativa%2F")
    expect(portal.locator("#eva-count")).to_have_text(
        "Mostrando 2 de 2 proyectos"
    )
    portal.locator("#eva-from").fill("2026-01-01")
    portal.locator("#eva-to").fill("2026-01-29")
    expect(portal.locator("#eva-count")).to_have_text(
        "Mostrando 0 de 2 proyectos"
    )
    expect(portal.locator("#eva-table tbody tr:visible")).to_have_count(0)
    portal.locator("[data-eva-refresh]").click()
    portal.wait_for_load_state()
    expect(portal.locator("#eva-to")).to_have_value("2026-01-29")
    expect(portal.locator("#eva-count")).to_have_text(
        "Mostrando 0 de 2 proyectos"
    )
    portal.locator("#eva-to").fill("2026-08-28")
    expect(portal.locator("#eva-count")).to_have_text(
        "Mostrando 2 de 2 proyectos"
    )
    portal.locator("#eva-manager").select_option("Mario")
    portal.reload()
    expect(portal.locator("#eva-manager")).to_have_value("Mario")
    expect(portal.locator("#eva-count")).to_have_text(
        "Mostrando 1 de 2 proyectos"
    )
    assert "volver=%2Foperativa%2F" in portal.url


@pytest.mark.parametrize(
    "saved_link", [False, True], ids=["current_url", "obsolete_url"]
)
def test_eva3_fills_hours_and_closed_projects(portal, evas, saved_link):
    portal.goto(
        portal.base
        + "/operativa/eva-3/"
        + ("?vista=anterior" if saved_link else "")
    )
    pending = portal.locator('tr[data-project="AER.004"]')
    expect(pending.locator('[data-field="burn"]')).to_have_text("20.25")
    assert evas["active"] == [["AER.004"]]
    assert not evas["aer"]
    portal.locator("#eva3-closed-box summary").click()
    row = portal.locator('tr[data-closed-id="PENDING.AER"]')
    expect(row.locator('[data-closed-field="burn"]')).to_have_text("60.25")
    expect(row.locator('[data-closed-field="etc"]')).to_have_text("-10.25")
    expect(row.locator('[data-closed-field="progress"]')).to_have_text("120.5%")
    assert evas["closed"] == ["PENDING.AER"]
    portal.get_by_role("link", name="← Regresar a Operativa").click()
    portal.wait_for_url("**/operativa/")


@pytest.mark.parametrize("screen", [1, 2, 3])
def test_empty_source_error_remains_visible(portal, evas, monkeypatch, screen):
    view = build_eva2_view([]) if screen < 3 else build_eva1_view([])
    monkeypatch.setattr(
        f"apps.portal.views.eva{2 if screen < 3 else 3}_data",
        lambda: {"eva": view, "error": "Fuente no disponible"},
    )
    portal.goto(portal.base + f"/operativa/eva-{screen}/")
    expect(portal.locator(".err")).to_contain_text("Fuente no disponible")
    expect(portal.locator(".fresh")).to_contain_text("Fuente no disponible")
    expect(portal.locator(".vacio").first).to_contain_text("No hay proyectos")


@pytest.mark.parametrize("screen", [1, 3])
def test_history_network_error_can_retry(portal, evas, screen):
    path = f"**/api/v1/screens/eva-{screen}/cerrados/"
    count = []

    def first_fails(route):
        count.append(1)
        if len(count) == 1:
            route.fulfill(status=503, body="No disponible")
        else:
            route.continue_()

    portal.route(path, first_fails)
    portal.goto(portal.base + f"/operativa/eva-{screen}/")
    prefix = "eva" if screen == 1 else "eva3"
    portal.locator(f"#{prefix}-closed-box summary").click()
    body = portal.locator(f"#{prefix}-closed-body")
    body.get_by_role("button", name="Reintentar", exact=True).click()
    expect(body.locator("table")).to_be_visible()
    assert len(count) == 2


def test_closed_burn_retries_one_failed_project(portal, evas, monkeypatch):
    calls = []

    def burn(project):
        calls.append(project)
        if len(calls) == 1:
            raise ValueError("MPB temporalmente no disponible")
        return {"burn": 60.25}

    monkeypatch.setattr("apps.portal.api.eva.fill_closed_burn", burn)
    portal.goto(portal.base + "/operativa/eva-3/")
    portal.locator("#eva3-closed-box summary").click()
    cell = portal.locator(
        'tr[data-closed-id="PENDING.AER"] [data-closed-field="burn"]'
    )
    expect(cell).to_contain_text("No disponible")
    cell.get_by_role("button", name="Reintentar").click()
    expect(cell).to_have_text("60.25")
    assert calls == ["PENDING.AER", "PENDING.AER"]


def test_deferred_consumption_keeps_a_partial_failure(
    portal, evas, monkeypatch
):
    monkeypatch.setattr(
        "apps.portal.api.eva.get_aer_tym_consumption",
        lambda _: {"ok": False, "error": "Clockify no disponible"},
    )
    portal.goto(portal.base + "/operativa/eva-3/")
    cell = portal.locator('tr[data-project="AER.004"] [data-field="burn"]')
    expect(cell).to_have_text("No disponible")
    expect(cell).to_have_attribute("title", "Clockify no disponible")
    expect(
        portal.locator('tr[data-project="AER.003"] [data-field="burn"]')
    ).to_have_text("120")


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_eva2_keeps_approved_reference(
    portal, evas, width, snapshot, enforced_csp
):
    portal.set_viewport_size({"width": width, "height": 1000})
    selectors = [
        ".pgh",
        ".kp4",
        ".kc",
        ".kv",
        ".two2",
        ".card",
        ".card h2",
        ".hs",
        "table",
        "th",
        "td",
        ".note",
        ".portal-page-toolbar",
    ]

    def measure():
        return portal.evaluate(
            """selectors=>selectors.map(s=>
          [...document.querySelectorAll(s)].map(el=>{
            const b=el.getBoundingClientRect(),c=getComputedStyle(el);
            return {box:['x','y','width','height'].map(k=>
                Math.round(b[k]*10)/10),
              css:['fontSize','fontWeight','color','backgroundColor',
                'padding','margin'].map(k=>c[k]),
              text:el.tagName==='TABLE'?el.innerText:null};
          }))""",
            selectors,
        )

    output = Path(f"tmp/migration/eva2/{width}")
    output.mkdir(parents=True, exist_ok=True)
    portal.goto(portal.base + "/operativa/eva-2/")
    portal.mouse.move(0, 0)
    snapshot(
        f"eva2_layout_{width}", dict(zip(selectors, measure(), strict=True))
    )
    portal.screenshot(path=str(output / "current.png"), full_page=True)


def test_eva2_saved_previous_link_keeps_tables_and_return(portal, evas):
    portal.goto(portal.base + "/operativa/eva-2/?vista=anterior")
    expect(portal.locator('script[src*="pages/eva2/main.js"]')).to_have_count(1)
    expect(portal.locator("table").last).to_contain_text("AMK.008")
    expect(portal.locator("table").last).to_contain_text("IXB.2")
    expect(
        portal.get_by_role("link", name="← Regresar a Operativa")
    ).to_have_attribute("href", "/operativa/")


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_eva3_reference_filters_export_and_layout(portal, evas, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + "/operativa/eva-3/")
    expect(
        portal.locator(
            '#eva3-projects tr[data-project="AER.004"] [data-field="burn"]'
        )
    ).to_have_text("20.25")
    expect(portal.locator("#eva3-projects tbody tr:visible")).to_have_count(3)
    portal.get_by_role("button", name="T&M (1)", exact=True).click()
    expect(portal.locator("#eva3-projects tbody tr:visible")).to_have_count(1)
    expect(portal.locator("#eva3-projects tbody")).to_contain_text(
        "TYM.AMK.010"
    )
    with portal.expect_download() as result:
        portal.locator("#eva3-export").click()
    text = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert "TYM.AMK.010" in text and "AER.003" not in text
    portal.get_by_role("button", name="Todos (3)", exact=True).click()
    expect(portal.locator(".eva3-filters")).to_have_count(0)
    expect(portal.locator("#eva3-search")).to_have_count(0)
    table = portal.locator("#eva3-projects")

    def menu_for(label):
        table.get_by_role(
            "button", name=f"Opciones de {label}", exact=False
        ).click()
        return portal.get_by_role(
            "dialog", name=f"Opciones de {label}", exact=True
        )

    def clear_columns():
        portal.locator(".eva3-project-card .eva-column-clear").click()

    menu = menu_for("Cuenta")
    menu.get_by_role("button", name="Borrar", exact=True).click()
    menu.get_by_role("checkbox", name="Globex", exact=True).check()
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator('tr[data-project="AER.003"]')).to_be_visible()
    expect(table.locator('tr[data-project="TYM.AMK.010"]')).to_be_hidden()
    clear_columns()
    menu = menu_for("Nombre del proyecto")
    menu.locator("summary").filter(has_text="Filtrar por condición").click()
    menu.get_by_label("Condición", exact=True).select_option("contains")
    menu.get_by_label("Valor de la condición", exact=True).fill("no existe")
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(portal.locator(".eva3-filter-empty")).to_contain_text(
        "No hay proyectos"
    )
    clear_columns()
    menu = menu_for("Fin")
    menu.locator("summary").filter(has_text="Filtrar por condición").click()
    menu.get_by_label("Condición", exact=True).select_option("gte")
    menu.get_by_label("Valor de la condición", exact=True).fill("2027-01-01")
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator('tr[data-project="TYM.AMK.010"]')).to_be_hidden()
    expect(table.locator('tr[data-project="AER.003"]')).to_be_visible()
    clear_columns()
    expect(table.locator("tbody tr:visible")).to_have_count(3)
    with portal.expect_download() as result:
        portal.locator("#eva3-summary-export").click()
    assert "Total FTE" in Path(result.value.path()).read_text(
        encoding="utf-8-sig"
    )
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    target = Path("tmp/design/eva3-reference")
    target.mkdir(parents=True, exist_ok=True)
    portal.mouse.move(0, 0)
    portal.screenshot(path=str(target / f"eva3-{width}.png"), full_page=True)


def test_eva3_reference_paginates_without_losing_projects(
    portal, evas, monkeypatch
):
    rows = [
        dict(row, idProyecto=f"{row['idProyecto']}.{index}")
        for index in range(10)
        for row in sample_rows()
    ]
    monkeypatch.setattr(
        "apps.portal.views.load_eva1",
        lambda *a, **kw: SimpleNamespace(view=build_eva1_view(rows), error=""),
    )
    portal.goto(portal.base + "/operativa/eva-3/")
    expect(portal.locator("#eva3-projects tbody tr:visible")).to_have_count(25)
    portal.get_by_role("button", name="Página siguiente", exact=True).click()
    expect(portal.locator("#eva3-projects tbody tr:visible")).to_have_count(5)
    portal.select_option("#eva3-page-size", "50")
    expect(portal.locator("#eva3-projects tbody tr:visible")).to_have_count(30)


def test_eva3_export_sanitizes_sheet_formulas(portal, evas, monkeypatch):
    rows = [dict(row, nombre="=1+1") for row in sample_rows()]
    monkeypatch.setattr(
        "apps.portal.views.load_eva1",
        lambda *a, **kw: SimpleNamespace(view=build_eva1_view(rows), error=""),
    )
    portal.goto(portal.base + "/operativa/eva-3/")
    with portal.expect_download() as result:
        portal.locator("#eva3-export").click()
    text = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert '"\'=1+1"' in text


@pytest.fixture
def history_reference(portal):
    import json

    projects = []
    for index in range(13):
        projects.append(
            {
                "project_id": f"HIS.{index:03}",
                "url": f"/proyectos/HIS.{index:03}/",
                "manager": "Laura" if index % 2 else "Mario",
                "client": "Cuenta prueba",
                "service": "AER" if index % 2 else "T&M",
                "name": "=1+1" if index == 0 else f"Proyecto {index}",
                "closed_status": "Cancelled" if index % 3 == 0 else "Completed",
                "start": "01/01/26",
                "end": "20/02/26" if index == 12 else "20/01/26",
                "budget": 100,
                "burn": 50 + index,
                "etc": 50 - index,
                "progress": 50 + index,
                "display": {
                    "budget": "100",
                    "burn": str(50 + index),
                    "etc": str(50 - index),
                    "progress": str(50 + index),
                },
            }
        )
    portal.route(
        "**/api/v1/screens/eva-3/cerrados/",
        lambda route: route.fulfill(
            content_type="application/json",
            body=json.dumps({"data": {"projects": projects, "error": ""}}),
        ),
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_eva3_history_reference_controls(
    portal, evas, history_reference, width
):
    portal.set_viewport_size({"width": width, "height": 1100})
    portal.goto(portal.base + "/operativa/eva-3/")
    portal.locator("#eva3-closed-box summary").click()
    table = portal.locator("#eva3-history-table")
    expect(table.locator("tbody tr:visible")).to_have_count(12)
    expect(portal.locator("#eva3-history-count")).to_have_text(
        "Mostrando 12 de 13 proyectos"
    )
    with portal.expect_download() as result:
        portal.locator("#eva3-history-export").click()
    text = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert "HIS.012" in text and '"\'=1+1"' in text
    expect(portal.locator("#eva3-closed-box")).to_have_attribute("open", "")
    portal.get_by_role(
        "button", name="Histórico página siguiente", exact=True
    ).click()
    expect(table.locator("tbody tr:visible")).to_have_count(1)

    def open_column(label):
        table.get_by_role(
            "button", name=f"Opciones de {label}", exact=False
        ).click()
        return portal.get_by_role(
            "dialog", name=f"Opciones de {label}", exact=True
        )

    menu = open_column("Service")
    target = Path("tmp/design/eva3-column-menus")
    target.mkdir(parents=True, exist_ok=True)
    box = menu.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= width
    assert box["y"] >= 0 and box["y"] + box["height"] <= 1100
    portal.screenshot(path=str(target / f"menu-{width}.png"))
    menu.get_by_role("button", name="Borrar", exact=True).click()
    menu.get_by_role("checkbox", name="AER", exact=True).check()
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(6)
    menu = open_column("Estatus")
    menu.get_by_role("button", name="Borrar", exact=True).click()
    menu.get_by_role("checkbox", name="Cancelado", exact=True).check()
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(2)
    portal.locator("#eva3-history-clear").click()
    menu = open_column("Delivery Manager")
    menu.get_by_role("button", name="Borrar", exact=True).click()
    menu.get_by_role("checkbox", name="Laura", exact=True).check()
    menu.get_by_role("button", name="Cancelar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(12)
    menu = open_column("Finish")
    menu.locator("summary").filter(has_text="Filtrar por condición").click()
    menu.get_by_label("Condición", exact=True).select_option("gte")
    menu.get_by_label("Valor de la condición", exact=True).fill("2026-02-01")
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(1)
    expect(table.locator("tbody tr:visible")).to_contain_text("HIS.012")
    portal.locator("#eva3-history-clear").click()
    menu = open_column("Burn")
    menu.get_by_role(
        "button", name="Ordenar de mayor a menor", exact=True
    ).click()
    expect(table.locator("tbody tr:visible").first).to_contain_text("HIS.012")
    portal.select_option("#eva3-history-size", "25")
    expect(table.locator("tbody tr:visible")).to_have_count(13)
    portal.locator("#eva3-history-clear").click()
    portal.select_option("#eva3-history-size", "12")
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")
    target = Path("tmp/design/eva3-history-reference")
    target.mkdir(parents=True, exist_ok=True)
    portal.locator("#eva3-closed-body .sc").evaluate(
        "node => node.scrollLeft = 0"
    )
    portal.locator("#eva3-closed-box").screenshot(
        path=str(target / f"history-{width}.png")
    )


def test_history_column_search_condition_color_and_csv(
    portal, evas, history_reference
):
    portal.goto(portal.base + "/operativa/eva-3/")
    portal.locator("#eva3-closed-box summary").click()
    table = portal.locator("#eva3-history-table")
    expect(portal.locator("#eva3-history-filters")).to_have_count(0)
    expect(table.locator("thead button")).to_have_count(12)
    table.get_by_role(
        "button", name="Opciones de Project ID", exact=False
    ).click()
    menu = portal.get_by_role(
        "dialog", name="Opciones de Project ID", exact=True
    )
    menu.get_by_role("button", name="Borrar", exact=True).click()
    menu.get_by_label("Buscar valores de la columna").fill("HIS.012")
    expect(menu.get_by_role("checkbox")).to_have_count(1)
    menu.get_by_role("checkbox", name="HIS.012").check()
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(1)
    with portal.expect_download() as result:
        portal.locator("#eva3-history-export").click()
    text = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert "HIS.012" in text and "HIS.011" not in text
    portal.locator("#eva3-history-clear").click()
    table.get_by_role("button", name="Opciones de Estatus", exact=False).click()
    menu = portal.get_by_role("dialog", name="Opciones de Estatus", exact=True)
    menu.locator("summary").filter(has_text="Filtrar por color").click()
    menu.get_by_label("Filtrar por color", exact=True).select_option("red")
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(5)
    portal.locator("#eva3-history-clear").click()
    table.get_by_role("button", name="Opciones de Burn", exact=False).click()
    menu = portal.get_by_role("dialog", name="Opciones de Burn", exact=True)
    menu.locator("summary").filter(has_text="Filtrar por condición").click()
    menu.get_by_label("Condición", exact=True).select_option("gt")
    menu.get_by_label("Valor de la condición", exact=True).fill("60")
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(2)
    table.get_by_role("button", name="Opciones de Nombre", exact=False).click()
    portal.keyboard.press("Escape")
    expect(
        portal.get_by_role("dialog", name="Opciones de Nombre", exact=True)
    ).to_be_hidden()


@pytest.mark.parametrize("width", [1450, 390])
def test_other_eva_project_tables_have_column_menus(portal, evas, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + "/operativa/eva-1/")
    table = portal.locator("#eva-table")
    expect(table.locator("thead button.eva-column-trigger")).to_have_count(27)
    table.get_by_role("button", name="Opciones de Service", exact=True).click()
    menu = portal.get_by_role("dialog", name="Opciones de Service", exact=True)
    menu.get_by_role("button", name="Borrar", exact=True).click()
    menu.get_by_role("checkbox", name="RaaS", exact=True).check()
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(1)
    with portal.expect_download() as result:
        portal.locator("#eva-export").click()
    text = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert "AMK.008" in text and "IXB.2" not in text
    portal.locator("#eva-projects .eva-column-clear").click()
    expect(table.locator("tbody tr:visible")).to_have_count(2)
    table.get_by_role(
        "button", name="Opciones de Discovery · Total de Work Items", exact=True
    ).click()
    menu = portal.get_by_role(
        "dialog", name="Opciones de Discovery · Total de Work Items", exact=True
    )
    target = Path("tmp/design/eva-column-menus")
    target.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(target / f"eva1-{width}.png"))
    portal.keyboard.press("Escape")
    portal.locator("#eva-closed-box summary").click()
    history = portal.locator("#eva-closed-table")
    expect(history.locator("thead button.eva-column-trigger")).to_have_count(26)
    history.get_by_role("button", name="Opciones de Nombre", exact=True).click()
    menu = portal.get_by_role("dialog", name="Opciones de Nombre", exact=True)
    menu.get_by_role("button", name="Borrar", exact=True).click()
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(history.locator("tbody tr[data-manager]:visible")).to_have_count(0)
    expect(history.locator(".eva-history-empty")).to_be_visible()
    portal.locator("#eva-closed-body .eva-column-clear").click()
    expect(history.locator("tbody tr:visible")).to_have_count(1)
    assert evas["ixb"] == 1
    portal.goto(portal.base + "/operativa/eva-3/")
    table = portal.locator("#eva3-projects")
    expect(table.locator("thead button.eva-column-trigger")).to_have_count(13)
    table.get_by_role(
        "button", name="Opciones de Presupuesto", exact=True
    ).click()
    menu = portal.get_by_role(
        "dialog", name="Opciones de Presupuesto", exact=True
    )
    menu.locator("summary").filter(has_text="Filtrar por condición").click()
    menu.get_by_label("Condición", exact=True).select_option("gt")
    menu.get_by_label("Valor de la condición", exact=True).fill("100")
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(1)
    with portal.expect_download() as result:
        portal.locator("#eva3-export").click()
    text = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert "TYM.AMK.010" in text and "AER.003" not in text
    table.get_by_role("button", name="Opciones de Cuenta", exact=True).click()
    portal.screenshot(path=str(target / f"eva3-{width}.png"))
    portal.keyboard.press("Escape")
    portal.locator(".eva3-project-card .eva-column-clear").click()
    expect(table.locator("tbody tr:visible")).to_have_count(3)


@pytest.mark.parametrize("width", [1450, 390])
def test_ixb_history_ten_per_page_and_filtered_export(
    portal, evas, monkeypatch, width
):
    import csv
    import io

    closed = [
        make_row(
            idProyecto=f"CLOSED.{index:02}",
            status="Cerrado",
            nombre="=1+1" if index == 0 else f"Proyecto {index}",
            budget=100 + index,
            burn=50,
            etc=50 + index,
        )
        for index in range(17)
    ]
    monkeypatch.setattr(
        "apps.portal.views.load_eva2_closed",
        lambda: SimpleNamespace(view=build_eva2_view(closed), error=""),
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + "/operativa/eva-1/")
    portal.locator("#eva-closed-box summary").click()
    table = portal.locator("#eva-closed-table")
    expect(table.locator("tbody tr:visible")).to_have_count(10)
    expect(portal.locator("#eva-history-count")).to_have_text(
        "Mostrando 1–10 de 17 proyectos"
    )
    with portal.expect_download() as result:
        portal.locator("#eva-history-export").click()
    text = Path(result.value.path()).read_text(encoding="utf-8-sig")
    exported = list(csv.reader(io.StringIO(text)))
    assert len(exported) == 18 and len(exported[0]) == 26
    assert "CLOSED.16" in text and '"\'=1+1"' in text
    expect(portal.locator("#eva-closed-box")).to_have_attribute("open", "")
    portal.get_by_role(
        "button", name="Histórico IXB página siguiente", exact=True
    ).click()
    expect(table.locator("tbody tr:visible")).to_have_count(7)
    expect(portal.locator("#eva-history-count")).to_have_text(
        "Mostrando 11–17 de 17 proyectos"
    )
    table.get_by_role(
        "button", name="Opciones de Project ID", exact=True
    ).click()
    menu = portal.get_by_role(
        "dialog", name="Opciones de Project ID", exact=True
    )
    menu.get_by_role("button", name="Borrar", exact=True).click()
    menu.get_by_role("checkbox", name="CLOSED.16", exact=True).check()
    menu.get_by_role("button", name="Aceptar", exact=True).click()
    expect(table.locator("tbody tr:visible")).to_have_count(1)
    expect(table.locator("tbody tr:visible")).to_contain_text("CLOSED.16")
    with portal.expect_download() as result:
        portal.locator("#eva-history-export").click()
    text = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert "CLOSED.16" in text and "CLOSED.00" not in text
    portal.locator("#eva-closed-body .eva-column-clear").click()
    expect(table.locator("tbody tr:visible")).to_have_count(10)
    expect(
        portal.get_by_role(
            "button", name="Histórico IXB página anterior", exact=True
        )
    ).to_be_disabled()
    target = Path("tmp/design/eva1-history-pagination")
    target.mkdir(parents=True, exist_ok=True)
    portal.locator("#eva-closed-box").screenshot(
        path=str(target / f"history-{width}.png")
    )


def test_aer_history_account_column_logo_and_csv(
    portal, evas, history_reference
):
    import json

    portal.route(
        "**/api/v1/account-logos/",
        lambda route: route.fulfill(
            content_type="application/json",
            body=json.dumps(
                {
                    "data": {
                        "items": [
                            {
                                "key": "cuenta prueba",
                                "url": "/static/account-test.svg",
                            }
                        ]
                    }
                }
            ),
        ),
    )
    portal.route(
        "**/static/account-test.svg",
        lambda route: route.fulfill(
            content_type="image/svg+xml",
            body=(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'width="20" height="20"><rect width="20" '
                'height="20" fill="green"/></svg>'
            ),
        ),
    )
    portal.goto(portal.base + "/operativa/eva-3/")
    portal.locator("#eva3-closed-box summary").click()
    table = portal.locator("#eva3-history-table")
    expect(table.locator("thead th").nth(1)).to_contain_text("Cuenta")
    expect(
        table.locator("tbody tr:visible").first.locator("td").nth(1)
    ).to_contain_text("Cuenta prueba")
    expect(
        table.locator("tbody tr:visible")
        .first.locator("td")
        .nth(1)
        .locator("img")
    ).to_have_attribute("src", "/static/account-test.svg")
    table.get_by_role("button", name="Opciones de Cuenta", exact=True).click()
    menu = portal.get_by_role("dialog", name="Opciones de Cuenta", exact=True)
    expect(
        menu.get_by_role("checkbox", name="Cuenta prueba", exact=True)
    ).to_be_checked()
    menu.get_by_role("button", name="Cancelar", exact=True).click()
    with portal.expect_download() as result:
        portal.locator("#eva3-history-export").click()
    text = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert text.splitlines()[0].startswith(
        '"Delivery Manager","Cuenta","Project ID"'
    )
    assert '"Cuenta prueba"' in text
    assert '"CP Cuenta prueba"' not in text


@pytest.mark.parametrize("width", [1450, 390])
def test_ixb_both_account_logos_and_compact_pager(portal, evas, width):
    import json

    portal.route(
        "**/api/v1/account-logos/",
        lambda route: route.fulfill(
            content_type="application/json",
            body=json.dumps(
                {
                    "data": {
                        "items": [
                            {
                                "key": "nestle mexico",
                                "url": "/static/ixb-test-logo.svg",
                            },
                            {
                                "key": "atlas nextwave",
                                "url": "/static/ixb-test-logo.svg",
                            },
                        ]
                    }
                }
            ),
        ),
    )
    portal.route(
        "**/static/ixb-test-logo.svg",
        lambda route: route.fulfill(
            content_type="image/svg+xml",
            body=(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'width="1600" height="600">'
                '<rect width="1600" height="600" fill="green"/></svg>'
            ),
        ),
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + "/operativa/eva-1/")
    table = portal.locator("#eva-table")
    expect(
        table.locator("thead tr").first.locator("th").nth(1)
    ).to_contain_text("Cuenta")
    expect(table.locator("tbody td:nth-child(2) img")).to_have_count(1)
    image = table.locator("tbody td:nth-child(2) img")
    expect(image).to_have_css("width", "26px")
    expect(image).to_have_css("height", "26px")
    with portal.expect_download() as result:
        portal.locator("#eva-export").click()
    text = Path(result.value.path()).read_text(encoding="utf-8-sig")
    assert text.splitlines()[0].startswith(
        '"Delivery Manager","Cuenta","Project ID"'
    )
    assert "Nestlé México" in text
    portal.locator("#eva-closed-box summary").click()
    history = portal.locator("#eva-closed-table")
    expect(history.locator("tbody td:nth-child(2)")).to_contain_text(
        "Atlas Next Wave"
    )
    expect(history.locator("tbody td:nth-child(2) img")).to_have_count(1)
    image = history.locator("tbody td:nth-child(2) img")
    expect(image).to_have_css("width", "26px")
    expect(image).to_have_css("height", "26px")
    target = Path("tmp/design/eva1-compact-logos")
    target.mkdir(parents=True, exist_ok=True)
    portal.locator("#eva-closed-box").screenshot(
        path=str(target / f"history-{width}.png")
    )
    expect(portal.locator(".eva-history-current")).to_have_text("1 / 1")
    expect(portal.locator("#eva-history-size")).to_have_value("10")
    portal.select_option("#eva-history-size", "25")
    expect(history.locator("tbody tr:visible")).to_have_count(1)
