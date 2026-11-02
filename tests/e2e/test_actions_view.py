"""Acciones modular: paridad de vista, formularios y eventos seguros."""

import pytest
from playwright.sync_api import expect

from tests.e2e.test_actions_transport import (
    board as board,
)
from tests.e2e.test_actions_transport import (
    client_actions as client_actions,
)
from tests.e2e.test_actions_transport import (
    enter,
)
from tests.e2e.test_actions_transport import (
    family as family,
)
from tests.e2e.test_actions_transport import (
    fixed_day as fixed_day,
)
from tests.e2e.test_actions_transport import (
    ixs as ixs,
)
from tests.e2e.test_actions_transport import (
    project_detail as project_detail,
)

pytestmark = pytest.mark.django_db(transaction=True)


def test_search_and_forms_do_not_use_old_renderers(
    portal, board, family, fixed_day
):
    enter(portal, family)
    portal.evaluate("""() => {
      aerDashboardData.acciones.filas[0].accion = 'Revisión técnica';
      const fail = () => { throw Error('Old renderer called'); };
      _aerVistaAcciones = aerIAAccionesPartesVista = _aerModal = fail;
      aerAbrirAccion = aerIAAbrirNuevaAccionParte = fail;
      _aerRenderTab();
    }""")
    search = portal.locator(".aer-action-search")
    search.fill("revision tecnica")
    expect(portal.locator("#aer-actions-table-body tr")).to_be_visible()
    search.fill("no coincide")
    expect(portal.locator("#aer-actions-table-body tr")).to_be_hidden()
    expect(portal.locator(".aer-action-shell")).to_contain_text(
        "Mostrando 0 de 1 acciones"
    )
    portal.get_by_role("button", name="Filtros", exact=True).click()
    expect(
        portal.get_by_role("group", name="Filtros de acciones")
    ).to_be_visible()
    assert portal.locator("#aer-modal-back").count() == 0
    portal.get_by_role("button", name="+ Agregar acción", exact=True).click()
    expect(portal.locator("#aa-a")).to_have_value("")
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="Cerrar", exact=True
    ).click()
    portal.get_by_role(
        "button", name="＋ Agregar pendiente", exact=True
    ).click()
    expect(portal.locator("#aerp-new-accion")).to_be_visible()


def test_data_stays_text_in_view_and_editor(portal, board, family, fixed_day):
    enter(portal, family)
    unsafe = '<img src=x onerror="window.injected=true">'
    portal.evaluate(
        """unsafe => {
      const row = aerDashboardData.acciones.filas[0];
      row.accion = row.responsable = row.dependencia = row.notas = unsafe;
      row.uid = "a'1";
      aerIAState.accionesPartes[0].accion = unsafe;
      _aerRenderTab();
    }""",
        unsafe,
    )
    expect(portal.locator("#aer-actions-table-body textarea")).to_have_value(
        unsafe
    )
    portal.evaluate('aerAbrirAccion("a\'1")')
    expect(portal.locator("#aa-a")).to_have_value(unsafe)
    expect(portal.locator("#aa-d")).to_have_value(unsafe)
    assert (
        portal.locator(".aer-action-shell img, #aer-modal-back img").count()
        == 0
    )
    assert portal.evaluate("window.injected || false") is False


def test_keyboard_opens_and_saves_form(portal, board, family, fixed_day):
    _, calls = board
    enter(portal, family)
    add = portal.get_by_role("button", name="+ Agregar acción", exact=True)
    add.focus()
    add.press("Enter")
    field = portal.get_by_label("Acción / Entregable", exact=True).last
    field.focus()
    field.fill("Revisión con teclado")
    field.press("Tab")
    expect(portal.locator("#aa-r")).to_be_focused()
    save = portal.locator("#aer-modal-back").get_by_role(
        "button", name="Guardar", exact=True
    )
    save.focus()
    save.press("Enter")
    expect(portal.locator("#aer-modal-back")).to_have_count(0)
    assert calls[-1][1]["Accion"] == "Revisión con teclado"


def test_reference_filters_charts_and_view_all_do_not_clean_data(
    portal, board, family, fixed_day
):
    _, calls = board
    enter(portal, family)
    expect(
        portal.get_by_role("img", name="Acciones previstas por semana")
    ).to_be_visible()
    assert portal.locator(".aer-action-mid h4 svg").evaluate_all(
        "nodes => nodes.every(n => n.getBoundingClientRect().width <= 24 && "
        "n.getBoundingClientRect().height <= 24)"
    )
    portal.get_by_role("button", name="Filtros", exact=True).click()
    portal.get_by_role("group", name="Filtros de acciones").get_by_role(
        "combobox", name="Estado", exact=True
    ).select_option("Pendiente")
    expect(portal.locator("#aer-actions-table-body tr")).to_be_visible()
    portal.locator(".aer-action-search").fill("no coincide")
    expect(portal.locator("#aer-actions-filter-count")).to_have_text(
        "Mostrando 0 de 1 acciones"
    )
    before = len(calls)
    portal.get_by_role(
        "button", name="Ver todas las acciones →", exact=True
    ).click()
    expect(portal.locator("#aer-actions-table-body tr")).to_be_visible()
    expect(portal.locator(".aer-action-search")).to_have_value("")
    assert len(calls) == before
    portal.set_viewport_size({"width": 390, "height": 844})
    assert portal.evaluate("document.documentElement.scrollWidth <= innerWidth")


def test_editor_reference_layout_and_cancel(portal, board, family, fixed_day):
    _, calls = board
    enter(portal, family)
    before = len(calls)
    for trigger, title, field in [
        ("+ Agregar acción", "Agregar acción", "aa-a"),
        (
            "＋ Agregar pendiente",
            "Agregar pendiente Beecker / Cliente",
            "aerp-new-accion",
        ),
    ]:
        button = portal.get_by_role("button", name=trigger, exact=True)
        button.click()
        dialog = portal.get_by_role("dialog", name=title, exact=True)
        expect(dialog).to_be_visible()
        dialog.locator("#" + field).fill("Revisión")
        expect(dialog.locator("#" + field + "-counter")).to_have_text(
            "8 caracteres"
        )
        for width in [1450, 390, 320]:
            portal.set_viewport_size({"width": width, "height": 1000})
            assert dialog.evaluate("n => n.scrollWidth <= n.clientWidth")
            assert dialog.locator(".ixs-svg").evaluate_all(
                "nodes => nodes.every(n => "
                "n.getBoundingClientRect().width <= 32)"
            )
        portal.keyboard.press("Escape")
        expect(dialog).to_have_count(0)
        expect(button).to_be_focused()
        portal.set_viewport_size({"width": 1450, "height": 1000})
    assert len(calls) == before
