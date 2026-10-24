"""Acciones modular: paridad de vista, formularios y eventos seguros."""

from pathlib import Path

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
from tests.e2e.test_ixs_effort import state

pytestmark = pytest.mark.django_db(transaction=True)


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("variant", ["empty", "attention", "progress"])
def test_actions_variants_match(
    portal, board, family, fixed_day, width, variant
):
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    for previous in [True, False]:
        enter(portal, family, previous)
        portal.evaluate(
            """variant => {
              const a = aerDashboardData.acciones;
              if(variant === 'empty') {
                aerDashboardData.acciones = {};
                aerIAState.accionesPartes = [];
              } else if(variant === 'progress') {
                a.filas = [
                  {...a.filas[0], uid:'b', estado:'En progreso'},
                  {...a.filas[0], uid:'c', estado:'Completado'}
                ];
              } else {
                a.filas[0].estado = 'Detenido';
                a.filas[0].dependencia = 'Otra área';
                a.filas[0].responsable = '';
                a.filas[0].fechaReal = '2026-10-02';
                a.vencidas = [...a.filas]; a.detenidas = [...a.filas];
                a.abiertas = [];
              }
              _aerRenderTab();
            }""",
            variant,
        )
        portal.mouse.move(0, 0)
        states.append(state(portal, ".aer-action-shell, .aer-action-shell *"))
    assert states[0] == states[1]
    assert (
        portal.locator(
            ".aer-action-shell [onclick], .aer-action-shell [onchange], "
            ".aer-action-shell [oninput]"
        ).count()
        == 0
    )


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("kind", ["new", "edit", "part"])
def test_forms_match(portal, board, family, fixed_day, width, kind):
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = (
        Path("tmp/migration/project_detail/actions_forms")
        / family
        / kind
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        enter(portal, family, previous)
        portal.evaluate(
            "aerIAAbrirNuevaAccionParte()"
            if kind == "part"
            else "aerAbrirAccion('a1')"
            if kind == "edit"
            else "aerAbrirAccion()"
        )
        portal.mouse.move(0, 0)
        states.append(state(portal, "#aer-modal-back, #aer-modal-back *"))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    assert states[0] == states[1]
    assert portal.locator("#aer-modal-back [onclick]").count() == 0


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
