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


@pytest.fixture
def evas(monkeypatch, datos):
    calls = {"ixb": 0, "aer": 0, "active": [], "closed": []}
    ixb = [
        make_row(),
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
    monkeypatch.setattr("apps.portal.pages.anterior_disponible", lambda: True)
    return calls


def test_eva1_filters_export_and_lazy_history(portal, evas):
    portal.goto(portal.base + "/operativa/eva-1/")
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


def test_eva3_fills_hours_and_closed_projects(portal, evas):
    portal.goto(portal.base + "/operativa/eva-3/")
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


@pytest.mark.parametrize("screen", [1, 2, 3])
@pytest.mark.parametrize("width", [1450, 390])
def test_matches_previous(portal, evas, screen, width):
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

    output = Path(f"tmp/migration/eva{screen}/{width}")
    output.mkdir(parents=True, exist_ok=True)
    captures = []
    for mode in ["previous", "current"]:
        legacy_path = (
            "**/operativa/eva-1/cerrados/"
            if screen == 1
            else "**/operativa/eva3/cerrados/"
        )

        def previous_fragment(route):
            route.continue_(url=route.request.url + "?vista=anterior")

        if mode == "previous" and screen != 2:
            portal.route(legacy_path, previous_fragment)
        portal.goto(
            portal.base
            + f"/operativa/eva-{screen}/"
            + ("?vista=anterior" if mode == "previous" else "")
        )
        if screen == 3:
            expect(
                portal.locator('tr[data-project="AER.004"] [data-field="burn"]')
            ).to_have_text("20.25")
        portal.mouse.move(0, 0)
        active = measure()
        portal.screenshot(path=str(output / (mode + ".png")), full_page=True)
        if screen != 2:
            prefix = "eva" if screen == 1 else "eva3"
            portal.locator(f"#{prefix}-closed-box summary").click()
            if screen == 1:
                expect(portal.locator("#eva-closed-table")).to_be_visible()
            else:
                expect(
                    portal.locator(
                        'tr[data-closed-id="PENDING.AER"] '
                        '[data-closed-field="burn"]'
                    )
                ).to_have_text("60.25")
            portal.mouse.move(0, 0)
            closed = measure()
            portal.screenshot(
                path=str(output / (mode + "-closed.png")), full_page=True
            )
        else:
            closed = []
        captures.append((active, closed))
        if mode == "previous" and screen != 2:
            portal.unroute(legacy_path, previous_fragment)
    for state in [0, 1]:
        if not captures[0][state]:
            continue
        for selector, before, after in zip(
            selectors, captures[0][state], captures[1][state], strict=True
        ):
            assert before == after, (state, selector, before, after)
