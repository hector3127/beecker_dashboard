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
        "Mostrando 1 de 1 acciones"
    )
    portal.get_by_role("button", name="Filtros", exact=True).click()
    expect(portal.locator("#aa-a")).to_have_value("")
    portal.locator("#aer-modal-back").get_by_role(
        "button", name="✕", exact=True
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
