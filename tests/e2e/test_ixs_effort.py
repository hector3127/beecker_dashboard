"""Esfuerzo IXS: paridad del contenido, modales, filtros y exportación."""

import copy
import json
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyectos/AMK.008/"


@pytest.fixture
def effort(portal, ixs, monkeypatch):
    from apps.portal.api import project_detail as api

    records = [
        {
            "id": str(i),
            "fecha": f"2026-10-{i + 1:02}",
            "recurso": "Ana Pérez",
            "actividad": "Desarrollo",
            "descripcion": f"Trabajo {i}",
            "duracion": 8,
            "inicio": "09:00",
            "fin": "17:00",
            "billable": True,
            "fueraHorario": i == 19,
        }
        for i in range(20)
    ]
    records += [
        {
            "id": "month" + str(i),
            "fecha": f"2026-{i:02}-01",
            "recurso": "Luis Gómez",
            "actividad": "Pruebas",
            "descripcion": "Validación",
            "duracion": 2.5,
            "inicio": "10:00",
            "fin": "12:30",
            "billable": False,
        }
        for i in range(5, 10)
    ]
    records += [
        {
            "id": "external",
            "fecha": "2026-10-22",
            "recurso": "Externo",
            "actividad": "",
            "descripcion": "=Descripción",
            "duracion": 1,
            "billable": True,
        }
    ]
    result = {"ok": True, "registros": records}
    calls = []

    def load(project):
        calls.append(project)
        return copy.deepcopy(result)

    monkeypatch.setattr(api, "records_dashboard", load)

    def rpc(route):
        if route.request.url.rstrip("/").endswith(
            "/getRegistrosClockifyProyecto"
        ):
            route.fulfill(json={"ok": True, "result": result})
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    return ixs[0], result, calls


def open_effort(portal, previous=False):
    portal.goto(portal.base + PAGE + ("?vista=anterior" if previous else ""))
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Esfuerzo", exact=True
    ).click()
    expect(portal.locator(".ixs-effort-kpis6")).to_be_visible()
    portal.wait_for_load_state("networkidle")


def open_modal(portal, kind):
    if kind == "activity":
        portal.locator(".ixs-effort-activity summary").first.click()
        portal.locator(".ixs-effort-member").first.click()
    elif kind == "records":
        portal.get_by_role("button", name="Ver más (").click()
    elif kind == "excess":
        portal.get_by_role(
            "button", name="Ver horas fuera de las estimadas"
        ).click()
    portal.wait_for_load_state("networkidle")


def state(portal, selector):
    return portal.evaluate(
        """selector => [...document.querySelectorAll(selector)]
      .map(el=>{const r=el.getBoundingClientRect(),c=getComputedStyle(el);
        return {tag:el.tagName.toLowerCase(),
          box:['x','y','width','height'].map(k=>Math.round(r[k]*10)/10),
          css:['fontSize','fontWeight','lineHeight','color','backgroundColor',
            'backgroundImage','paddingTop','paddingBottom','marginTop',
            'marginBottom','display','gap'].map(k=>c[k]),
          text:el.textContent.replace(/\\s+/g,'')};})""",
        selector,
    )


@pytest.mark.parametrize("variant", ["full", "empty", "attention"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_all_elements_match_previous(portal, effort, fixed_day, variant, width):
    data, result, _ = effort
    if variant == "empty":
        data.clear()
        data.update({"proyecto": {"id": "AMK.008"}})
        result["registros"] = []
    elif variant == "attention":
        data["totalesRecursos"].update(
            {"horasEstimadas": 10, "horasReales": 30, "horasNoFact": 50}
        )
        data["kpisExtra"]["horasFueraHorario"] = 2.25
    portal.set_viewport_size({"width": width, "height": 1000})
    compare(portal, f"{variant}/{width}", "#ixs-tab-contenido *")
    expect(portal.locator("#ixs-tab-contenido")).to_have_attribute(
        "data-renderer", "modular-effort"
    )
    assert portal.locator("#ixs-tab-contenido [onclick]").count() == 0


@pytest.mark.parametrize("kind", ["activity", "records", "excess"])
@pytest.mark.parametrize("width", [1450, 900, 390])
def test_modals_match_previous(portal, effort, fixed_day, kind, width):
    portal.set_viewport_size({"width": width, "height": 1000})
    selector = {
        "activity": "#ixs-actividad-modal",
        "records": "#ixs-clockify-modal",
        "excess": "#ixs-excess-modal",
    }[kind]
    compare(portal, f"{kind}/{width}", selector + ", " + selector + " *", kind)
    assert portal.locator(selector + " [onclick]").count() == 0


def compare(portal, name, selector, modal=None):
    out = Path("tmp/migration/project_detail/ixs_effort") / name
    out.mkdir(parents=True, exist_ok=True)
    open_effort(portal, True)
    if modal:
        open_modal(portal, modal)
    before = state(portal, selector)
    portal.screenshot(path=str(out / "previous.png"), full_page=True)
    open_effort(portal)
    if modal:
        open_modal(portal, modal)
    after = state(portal, selector)
    portal.screenshot(path=str(out / "current.png"), full_page=True)
    (out / "differences.json").write_text(
        json.dumps(
            {
                "previous_count": len(before),
                "current_count": len(after),
                "differences": [
                    {"index": i, "previous": a, "current": b}
                    for i, (a, b) in enumerate(zip(before, after, strict=False))
                    if a != b
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    assert after == before


def test_dates_cache_and_navigation(portal, effort, fixed_day):
    _, _, calls = effort
    requests = []
    portal.on("request", lambda r: requests.append(r.url))
    open_effort(portal)
    portal.locator("#ixs-clock-desde").fill("2026-05-01")
    portal.locator("#ixs-clock-hasta").fill("2026-10-23")
    portal.get_by_role("button", name="Aplicar", exact=True).click()
    expect(portal.locator(".ixs-effort-records tbody tr")).to_have_count(5)
    expect(portal.get_by_role("button", name="Ver más (26)")).to_be_visible()
    open_modal(portal, "records")
    expect(portal.locator("#ixs-clockify-modal tbody tr")).to_have_count(26)
    portal.locator("#ixs-clockify-modal").get_by_role(
        "button", name="✕ Cerrar"
    ).click()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Esfuerzo", exact=True
    ).click()
    expect(portal.locator("#ixs-clock-desde")).to_have_value("2026-05-01")
    assert calls == ["AMK.008"]
    assert not any("/api/rpc/" in url for url in requests)


def test_excess_filters_sort_pages_and_csv(portal, effort, fixed_day, tmp_path):
    csvs = []
    for previous in (True, False):
        open_effort(portal, previous)
        open_modal(portal, "excess")
        first = portal.locator("#ixs-excess-records details").first
        expect(first.locator("tbody tr")).to_have_count(8)
        first.get_by_role("button", name="Página siguiente").click()
        expect(first.locator("footer")).to_contain_text("Mostrando 9–14 de 14")
        first.get_by_role("button", name="Inicio").click()
        expect(first.locator("th").nth(1)).to_have_attribute(
            "aria-sort", "ascending"
        )
        portal.locator("#ixs-excess-from").fill("2026-10-19")
        portal.locator("#ixs-excess-to").fill("2026-10-22")
        portal.get_by_role("button", name="Aplicar fechas").click()
        expect(first.locator("tbody tr")).to_have_count(2)
        with portal.expect_download() as download:
            portal.get_by_role("button", name="↓ Exportar CSV").click()
        path = tmp_path / ("old.csv" if previous else "new.csv")
        download.value.save_as(path)
        csvs.append(path.read_bytes())
        assert (
            download.value.suggested_filename
            == "AMK.008_horas_excedidas_2026-10-19_2026-10-22.csv"
        )
    assert csvs[0] == csvs[1]
    assert b"'=Descripci" in csvs[1]


@pytest.mark.parametrize("transport", [False, True])
def test_records_errors_keep_other_sections(
    portal, effort, fixed_day, transport
):
    _, result, _ = effort
    if transport:
        portal.route(
            "**/screens/proyectos/AMK.008/registros/",
            lambda route: route.abort("failed"),
        )
    else:
        result.update({"ok": False, "error": "Clockify no disponible"})
    open_effort(portal)
    expect(portal.locator("#ixs-actividad-card .ixs-empty")).not_to_have_text(
        "Consultando Clockify…"
    )
    expect(portal.locator("#ixs-registros-card .ixs-empty")).to_be_visible()
    expect(portal.locator(".ixs-effort-kpis6")).to_contain_text("49.86 h")
    expect(portal.locator("#ixs-tasks-effort")).to_contain_text("Desarrollo")


def test_invalid_dates_preserve_applied_range(portal, effort, fixed_day):
    messages = []

    def dismiss(dialog):
        messages.append(dialog.message)
        dialog.dismiss()

    portal.on("dialog", dismiss)
    open_effort(portal)
    portal.locator("#ixs-clock-desde").fill("2026-10-23")
    portal.locator("#ixs-clock-hasta").fill("2026-10-01")
    portal.get_by_role("button", name="Aplicar", exact=True).click()
    assert (
        messages[-1]
        == "Selecciona fechas válidas; Desde debe ser anterior o igual a Hasta."
    )
    expect(portal.get_by_role("button", name="Ver más (3)")).to_be_visible()
    open_modal(portal, "excess")
    portal.locator("#ixs-excess-from").fill("2026-10-23")
    portal.locator("#ixs-excess-to").fill("2026-10-01")
    portal.get_by_role("button", name="Aplicar fechas").click()
    assert (
        messages[-1]
        == "La fecha de inicio debe ser anterior o igual a la fecha de fin."
    )
    expect(portal.locator("#ixs-excess-records details")).to_have_count(2)


def test_safe_text_in_activities_and_dialogs(portal, effort, fixed_day):
    data, result, _ = effort
    text = '<img src=x onerror="window.effortInjected=true">'
    result["registros"][0].update(
        {"recurso": text, "actividad": text, "descripcion": text}
    )
    data["filasRecursosCompleto"][0]["nombre"] = text
    data["filasRecursosCompleto"][0]["horasEstimadas"] = 0
    open_effort(portal)
    activity = portal.locator(".ixs-effort-activity").filter(has_text=text)
    activity.locator("summary").click()
    activity.locator(".ixs-effort-member").click()
    expect(portal.locator("#ixs-actividad-modal")).to_contain_text(text)
    assert portal.locator("#ixs-actividad-modal img").count() == 0
    portal.locator("#ixs-actividad-modal button").press("Escape")
    expect(portal.locator("#ixs-actividad-modal")).to_have_count(0)
    open_modal(portal, "excess")
    expect(portal.locator("#ixs-excess-modal")).to_contain_text(text)
    assert (
        portal.locator("#ixs-excess-modal img, #ixs-tab-contenido img").count()
        == 0
    )
    assert portal.evaluate("window.effortInjected") is None


def test_late_records_are_cached_without_overwriting_other_tab(
    portal, effort, fixed_day
):
    _, result, _ = effort
    held = []
    portal.route(
        "**/screens/proyectos/AMK.008/registros/",
        lambda route: held.append(route),
    )
    portal.goto(portal.base + PAGE)
    with portal.expect_request("**/screens/proyectos/AMK.008/registros/"):
        portal.locator(".ixs-nav").get_by_role(
            "button", name="Esfuerzo", exact=True
        ).click()
    expect(portal.locator("#ixs-actividad-card")).to_contain_text(
        "Consultando Clockify…"
    )
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    assert len(held) == 1
    held[0].fulfill(json={"data": result, "meta": {}})
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#ixs-tab-contenido")).to_have_attribute(
        "data-renderer", "modular"
    )
    assert portal.locator("#ixs-actividad-card").count() == 0
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Esfuerzo", exact=True
    ).click()
    expect(portal.locator(".ixs-effort-activity")).to_have_count(3)
    assert len(held) == 1
