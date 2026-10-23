"""Tabla Azure modular: paridad, filtros, guardado y ciclo de vida."""

from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_azure_transport import enter, tab
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_ixs_planning_transport import planning as planning
from tests.e2e.test_ixs_work_items import update
from tests.e2e.test_ixs_work_items import writes as writes
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)


def open_table(portal, previous=False):
    enter(portal, previous)
    portal.locator("#ixs-azure-wi-collapse > summary").click()
    expect(portal.locator("#wi-row-101")).to_be_attached()
    portal.wait_for_load_state("networkidle")


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["full", "filtered", "no-match"])
def test_table_matches_previous(portal, writes, fixed_day, width, variant):
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = (
        Path("tmp/migration/project_detail/ixs_azure_table")
        / variant
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        open_table(portal, previous)
        if variant == "filtered":
            portal.locator("#ixs-azure-filter-estado").select_option("Closed")
        elif variant == "no-match":
            portal.locator("#ixs-azure-filter-search").fill("inexistente")
        portal.mouse.move(0, 0)
        states.append(
            capture_state(portal, "#ixs-tab-contenido, #ixs-tab-contenido *")
        )
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    expect(portal.locator("#ixs-tab-contenido")).to_have_attribute(
        "data-renderer", "modular-azure"
    )
    assert (
        portal.locator(
            "#ixs-tab-contenido [onclick], #ixs-tab-contenido [onchange], "
            "#ixs-tab-contenido [oninput]"
        ).count()
        == 0
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("kind", ["dev", "qa", "date", "demo", "comment"])
def test_saved_row_matches_previous(portal, writes, fixed_day, width, kind):
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = (
        Path("tmp/migration/project_detail/ixs_azure_table") / kind / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        open_table(portal, previous)
        if kind == "comment":
            portal.locator("#wi-comentario-101").fill(" Validación á ")
            portal.locator("#wi-row-101 button").click()
            expect(portal.locator("#wi-comentario-status-101")).to_have_text(
                "✓ Publicado en Azure DevOps"
            )
        else:
            column, value = {
                "dev": (5, "62.5"),
                "qa": (6, True),
                "date": (7, "2026-11-01"),
                "demo": (8, "Demo á ' final"),
            }[kind]
            update(portal, column, value)
            expect(portal.locator("#wi-avance-101")).to_contain_text(
                "50%" if kind == "dev" else "20%" if kind == "qa" else "0%"
            )
        portal.mouse.move(0, 0)
        states.append(capture_state(portal, "#wi-row-101, #wi-row-101 *"))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]


def test_filters_refresh_and_date_keep_existing_behavior(
    portal, writes, planning, fixed_day
):
    calls, _ = writes
    open_table(portal)
    original = portal.locator("#ixs-azure-dates").text_content()
    update(portal, 7, "2026-11-01")
    expect(portal.locator("#wi-avance-101")).to_contain_text("0%")
    expect(portal.locator("#ixs-azure-dates")).to_have_text(original)
    portal.locator("#ixs-azure-filter-tipo").select_option("To Be")
    expect(portal.locator("#ixs-azure-table tbody tr")).to_have_count(1)
    # Filtering repaints from the source, as before.
    expect(portal.locator("#wi-row-101 input[type=date]")).to_have_value(
        "2026-10-22"
    )
    portal.locator("#ixs-azure-filter-search").fill("Ana")
    portal.get_by_text("↻ Actualizar Azure", exact=True).click()
    expect(portal.locator("#ixs-azure-filter-tipo")).to_have_value("To Be")
    expect(portal.locator("#ixs-azure-filter-search")).to_have_value("Ana")
    expect(portal.locator("#wi-row-101")).to_be_attached()
    assert calls[-1] == ("progress", 101, "fechaLimiteDev", "2026-11-01")


@pytest.mark.parametrize("kind", ["progress", "comment"])
@pytest.mark.parametrize("mode", ["source", "transport"])
def test_error_and_retry(portal, writes, fixed_day, kind, mode):
    _, answers = writes
    open_table(portal)
    url = "**/screens/work-items/101/" + (
        "avance/" if kind == "progress" else "comentarios/"
    )
    if mode == "source":
        answers[kind] = {"ok": False, "error": "Falla simulada"}
    else:
        portal.route(
            url,
            lambda route: route.fulfill(
                status=502,
                json={"error": {"code": "source", "message": "Falla simulada"}},
            ),
        )

    def submit():
        if kind == "progress":
            update(portal, 5, "60")
        else:
            portal.locator("#wi-comentario-101").fill("Borrador")
            portal.locator("#wi-row-101 button").click()

    portal.once("dialog", lambda dialog: dialog.accept())
    with portal.expect_event("dialog") as event:
        submit()
    assert "Falla simulada" in event.value.message
    if kind == "comment":
        expect(portal.locator("#wi-comentario-101")).to_have_value("Borrador")
    answers[kind] = {"ok": True}
    if mode == "transport":
        portal.unroute(url)
    submit()
    expect(
        portal.locator("#wi-avance-101")
        if kind == "progress"
        else portal.locator("#wi-comentario-status-101")
    ).to_contain_text("48%" if kind == "progress" else "✓ Publicado")


@pytest.mark.parametrize("kind", ["progress", "comment"])
@pytest.mark.parametrize("ok", [True, False])
def test_late_result_cannot_change_reentered_tab(
    portal, writes, fixed_day, kind, ok
):
    open_table(portal)
    held = []
    url = "**/screens/work-items/101/" + (
        "avance/" if kind == "progress" else "comentarios/"
    )
    portal.route(url, lambda route: held.append(route))
    alerts = []
    portal.on(
        "dialog",
        lambda dialog: (alerts.append(dialog.message), dialog.accept()),
    )
    with portal.expect_request(url):
        if kind == "progress":
            update(portal, 5, "75")
        else:
            portal.locator("#wi-comentario-101").fill("Anterior")
            portal.locator("#wi-row-101 button").click()
    if kind == "comment":
        portal.locator("#wi-row-101 button").dispatch_event("click")
        assert len(held) == 1
    tab(portal, "Ejecutivo")
    tab(portal, "Azure DevOps")
    portal.locator("#ixs-azure-wi-collapse > summary").click()
    portal.locator("#wi-comentario-101").fill("Nuevo borrador")
    held[0].fulfill(json={"data": {"ok": ok, "error": "Vieja"}, "meta": {}})
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#wi-avance-101")).to_contain_text("40%")
    expect(portal.locator("#wi-comentario-101")).to_have_value("Nuevo borrador")
    expect(portal.locator("#wi-comentario-status-101")).to_be_empty()
    assert alerts == []


def test_empty_comment_and_source_text(portal, writes, planning, fixed_day):
    _, azure, _, _ = planning
    text = '<img src=x onerror="window.injected=1">'
    azure["items"][0].update(titulo=text, demo=text)
    open_table(portal)
    expect(portal.locator("#ixs-azure-table")).to_contain_text(text)
    expect(portal.locator("#wi-row-101 td:nth-child(8) input")).to_have_value(
        text
    )
    assert portal.locator("#ixs-azure-table img").count() == 0
    assert portal.evaluate("window.injected") is None
    portal.once("dialog", lambda dialog: dialog.accept())
    with portal.expect_event("dialog") as event:
        portal.locator("#wi-row-101 button").click()
    assert event.value.message == "Escribe un comentario antes de enviar."


def test_cached_items_remain_searchable_while_reentering_loads(
    portal, writes, planning, fixed_day
):
    _, azure, _, _ = planning
    open_table(portal)
    tab(portal, "Ejecutivo")
    held = []
    path = "**/screens/proyectos/AMK.008/azure/*"
    portal.route(path, lambda route: held.append(route))
    tab(portal, "Azure DevOps")
    expect(portal.locator("#ixs-azure-stale")).to_have_text(
        "Cargando Azure DevOps…"
    )
    portal.locator("#ixs-azure-wi-collapse > summary").click()
    expect(portal.locator("#ixs-azure-filter-estado option")).to_have_count(1)
    portal.locator("#ixs-azure-filter-search").fill("Ana")
    expect(portal.locator("#ixs-azure-table tbody tr")).to_have_count(1)
    held[0].fulfill(json={"data": azure, "meta": {}})
    portal.wait_for_load_state("networkidle")
    expect(portal.locator("#ixs-azure-filter-estado option")).to_have_count(3)
    expect(portal.locator("#ixs-azure-filter-search")).to_have_value("Ana")
    expect(portal.locator("#ixs-azure-table tbody tr")).to_have_count(1)
