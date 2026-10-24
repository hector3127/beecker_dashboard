"""Pestaña Cliente (AER e IXS): API v1, mismo diseño y guardado."""

import copy
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import PAGE as AER_PAGE
from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_client_actions_transport import (  # noqa: F401
    client_actions as client_actions,
)
from tests.e2e.test_ixs_effort import state as capture_state
from tests.e2e.test_ixs_executive import PAGE as IXS_PAGE
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
CONTACTS = [
    {
        "uid": "c1",
        "nombre": "Ana Pérez",
        "cargo": "Dirección <b>TI</b>",
        "rol": "Sponsor",
        "area": "TI",
        "correo": "ana@example.com",
        "telefono": "5551234",
        "nivelDecision": "Alto",
        "estado": "Activo",
        "canal": "Teams",
        "alcance": "Proyecto, Presupuesto; Riesgos",
        "requerimientos": True,
        "aprueba": True,
        "valida": False,
        "decide": True,
        "informado": False,
        "esDecisor": True,
        "notas": "Notas & más",
    },
    {
        "uid": "c2",
        "nombre": "Luis Soto",
        "cargo": "",
        "rol": "Usuario clave",
        "area": "Operaciones",
        "correo": "",
        "telefono": "",
        "nivelDecision": "Medio",
        "estado": "Activo",
        "canal": "Correo",
        "alcance": "",
        "informado": True,
    },
    {
        "uid": "c3",
        "nombre": "Eva Gil",
        "cargo": "Analista",
        "rol": "Usuario clave",
        "area": "Finanzas",
        "correo": "eva@example.com",
        "telefono": "5559999",
        "nivelDecision": "Bajo",
        "estado": "Inactivo",
        "canal": "",
        "alcance": "Reportes",
    },
]
CLIENT = {
    "contactos": CONTACTS,
    "info": {
        "uid": "i1",
        "areaPrincipal": "TI",
        "sponsor": "Ana Pérez",
        "productOwner": "Luis Soto",
        "correoDistribucion": "equipo@example.com",
        "rutaEscalamiento": "PO > Sponsor",
        "canales": "Teams, Correo, Comité operativo",
    },
    "gobierno": [
        {
            "reunion": "Seguimiento",
            "frecuencia": "Semanal",
            "participantes": "PO + Cliente",
            "canal": "Teams",
        }
    ],
    "documentos": [
        {
            "uid": "d1",
            "nombre": "Repositorio",
            "tipo": "Repositorio",
            "url": "https://drive.google.com/r",
            "accion": "Abrir",
            "notas": "",
        },
        {
            "uid": "d2",
            "nombre": "Plantilla MCO",
            "tipo": "Plantilla",
            "url": "drive.google.com/mco",
            "accion": "Ver",
            "notas": "x",
        },
    ],
    "resumen": {},
}


@pytest.fixture(params=["ixs", "aer"])
def family(request):
    return request.param


@pytest.fixture
def board(request, family, portal, monkeypatch, fixed_day):
    """Datos de Cliente listos para la familia pedida."""
    calls = []
    if family == "ixs":
        data, _ = request.getfixturevalue("client_actions")
        data["cliente"] = copy.deepcopy(CLIENT)
    else:
        _, aer = request.getfixturevalue("project_detail")
        aer["cliente"] = copy.deepcopy(CLIENT)
    return family, calls


def open_tab(portal, family, previous=False):
    suffix = "?vista=anterior" if previous else ""
    if family == "ixs":
        portal.goto(portal.base + IXS_PAGE + suffix)
        portal.locator(".ixs-nav").get_by_role(
            "button", name="Cliente", exact=True
        ).click()
        content = "#ixs-tab-contenido"
    else:
        portal.goto(portal.base + AER_PAGE + suffix)
        portal.locator(".aer-tabs").get_by_role(
            "button", name="Cliente", exact=True
        ).click()
        content = "#aer-tab-content"
    expect(portal.locator(".aer-client-shell")).to_be_visible()
    portal.wait_for_load_state("networkidle")
    return content


def snapshot(portal, content):
    selector = (
        f"{content}, {content} *, #aer-modal-back, #aer-modal-back *, "
        ".aer-toast"
    )
    classes = portal.evaluate(
        "s=>[...document.querySelectorAll(s)]"
        ".map(e=>String(e.getAttribute('class')||'').trim())",
        selector,
    )
    return [
        {**s, "cls": c}
        for s, c in zip(capture_state(portal, selector), classes, strict=True)
    ]


def nothing(portal):
    pass


def filters(portal):
    portal.get_by_role("button", name="⌄ Filtros").click()
    portal.locator(".aer-client-filterbar select").first.select_option(
        "Usuario clave"
    )


def search(portal):
    portal.locator("#aer-client-search").fill("eva")


def new_contact(portal):
    portal.get_by_role("button", name="＋ Agregar contacto").click()
    expect(portal.locator("#aer-modal-back")).to_be_visible()


def edit_contact(portal):
    portal.locator(".aer-client-directory tbody tr").first.get_by_role(
        "button"
    ).click()
    expect(portal.locator("#aer-modal-back")).to_be_visible()


def info(portal):
    portal.get_by_role("button", name="✎ Editar información").click()
    expect(portal.locator("#aer-modal-back")).to_be_visible()


def governance(portal):
    portal.get_by_role("button", name="✎ Editar", exact=True).click()
    expect(portal.locator("#aer-gov-editor")).to_be_visible()


def new_document(portal):
    portal.get_by_role("button", name="＋ Agregar link").click()
    expect(portal.locator("#aer-modal-back")).to_be_visible()


def edit_document(portal):
    portal.locator(".aer-client-docs-table tbody tr").first.get_by_role(
        "button", name="⋮"
    ).click()
    expect(portal.locator("#aer-modal-back")).to_be_visible()


STEPS = [
    nothing,
    filters,
    search,
    new_contact,
    edit_contact,
    info,
    governance,
    new_document,
    edit_document,
]


@pytest.mark.parametrize("width", [1450, 900, 390])
@pytest.mark.parametrize("step", STEPS)
def test_matches_previous(portal, board, width, step):
    family, _ = board
    portal.set_viewport_size({"width": width, "height": 1000})
    states = []
    directory = (
        Path("tmp/migration/project_detail/client_tab")
        / family
        / step.__name__
        / str(width)
    )
    directory.mkdir(parents=True, exist_ok=True)
    for previous in [True, False]:
        content = open_tab(portal, family, previous)
        step(portal)
        portal.mouse.move(0, 0)
        portal.wait_for_timeout(250)
        states.append(snapshot(portal, content))
        portal.screenshot(
            path=str(directory / ("old.png" if previous else "new.png")),
            full_page=True,
        )
    diffs = [
        (
            i,
            a["tag"],
            a["cls"],
            {k: (a[k], b[k]) for k in a if k != "cls" and a[k] != b[k]},
        )
        for i, (a, b) in enumerate(zip(*states, strict=False))
        if a != b
    ]
    assert len(states[0]) == len(states[1]) and not diffs, diffs[:5]
