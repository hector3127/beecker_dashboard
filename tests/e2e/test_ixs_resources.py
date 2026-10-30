"""Recursos IXS: diseño anterior, asignaciones, guardado y errores."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_effort import effort as effort
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyectos/AMK.008/"


@pytest.fixture
def resources(portal, effort, monkeypatch):
    from apps.portal.api import project_detail as api

    data, records, _ = effort
    data["filasRecursosCompleto"] = [
        x for x in data["filasRecursosCompleto"] if x["nombre"] != "Externo"
    ]
    result = {
        "ok": True,
        "proyectoId": "AMK.008",
        "filas": [
            {
                "nombre": "Ana Pérez",
                "rol": "Developer",
                "horasEstimadas": 20,
                "activo": False,
            },
            {
                "nombre": "O'Connor",
                "rol": "QA",
                "horasEstimadas": 12.25,
                "activo": True,
            },
        ],
    }
    saves = []
    errors = []

    def save(payload):
        saves.append(copy.deepcopy(payload))
        if errors:
            return {"ok": False, "error": errors.pop(0)}
        row = {
            key: payload[key]
            for key in ("nombre", "rol", "horasEstimadas", "activo")
        }
        row["horasEstimadas"] = float(row["horasEstimadas"])
        result["filas"] = [
            x for x in result["filas"] if x["nombre"] != row["nombre"]
        ] + [row]
        return copy.deepcopy(result)

    monkeypatch.setattr(
        api, "resources_dashboard", lambda project: copy.deepcopy(result)
    )
    monkeypatch.setattr(api, "save_resource_dashboard", save)

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        if name == "ixsRecursosLeer":
            route.fulfill(json={"ok": True, "result": result})
        elif name == "ixsRecursosGuardar":
            route.fulfill(
                json={
                    "ok": True,
                    "result": save(route.request.post_data_json["args"][0]),
                }
            )
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    return data, result, records, saves, errors


def open_resources(portal):
    portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Recursos", exact=True
    ).click()
    expect(portal.locator("#ixs-tab-contenido h3")).to_have_text(
        "Recursos del proyecto AMK.008"
    )
    portal.wait_for_load_state("networkidle")


def edit(portal, name):
    portal.locator("#ixs-tab-contenido tbody tr").filter(
        has_text=name
    ).get_by_role("button", name="Editar", exact=True).click()


def test_add_edit_and_assign_use_api_and_csrf(portal, resources, fixed_day):
    _, _, _, saves, _ = resources
    requests = []
    portal.on("request", lambda r: requests.append(r))
    open_resources(portal)
    edit(portal, "O'Connor")
    form = portal.locator("#ixs-recurso-form")
    expect(form.locator('[name="nombre"]')).to_have_attribute("readonly", "")
    form.locator('[name="rol"]').fill("Lead QA")
    form.locator('[name="horas"]').fill("0")
    form.locator('[name="activo"]').select_option("false")
    form.get_by_role("button", name="Guardar recurso").click()
    expect(portal.locator("#ixs-recurso-modal")).to_have_count(0)
    expect(
        portal.locator("tbody tr").filter(has_text="O'Connor")
    ).to_contain_text("Lead QA")
    portal.get_by_role("button", name="+ Agregar recurso").click()
    form = portal.locator("#ixs-recurso-form")
    form.locator('[name="nombre"]').fill("Nuevo recurso")
    form.locator('[name="rol"]').fill("Consultor")
    form.locator('[name="horas"]').fill("3.25")
    form.get_by_role("button", name="Guardar recurso").click()
    expect(portal.locator("#ixs-recurso-modal")).to_have_count(0)
    portal.get_by_role("button", name="Asignar", exact=True).click()
    form = portal.locator("#ixs-recurso-form")
    expect(form.locator('[name="nombre"]')).to_have_value("Externo")
    form.locator('[name="rol"]').fill("Soporte")
    form.locator('[name="horas"]').fill("5")
    form.get_by_role("button", name="Guardar recurso").click()
    expect(portal.locator("#ixs-recurso-modal")).to_have_count(0)
    expect(portal.locator(".ixs-resource-alert")).to_have_count(1)
    assert len(saves) == 3
    assert saves[0] == {
        "idProyecto": "AMK.008",
        "nombre": "O'Connor",
        "rol": "Lead QA",
        "horasEstimadas": "0",
        "activo": False,
    }
    writes = [r for r in requests if "/recursos/guardar/" in r.url]
    assert len(writes) == 3
    assert all(
        r.method == "POST" and r.headers.get("x-csrftoken") for r in writes
    )
    assert not any("/api/rpc/" in r.url for r in requests)


def test_save_error_retains_form_and_can_retry(portal, resources, fixed_day):
    _, _, _, saves, errors = resources
    errors.append("No se pudo guardar la asignación")
    open_resources(portal)
    edit(portal, "O'Connor")
    form = portal.locator("#ixs-recurso-form")
    form.locator('[name="rol"]').fill("Reintento")
    form.get_by_role("button", name="Guardar recurso").click()
    expect(portal.locator("#ixs-recurso-error")).to_have_text(
        "No se pudo guardar la asignación"
    )
    expect(form.locator('[name="rol"]')).to_have_value("Reintento")
    expect(form.get_by_role("button", name="Guardar recurso")).to_be_enabled()
    form.get_by_role("button", name="Guardar recurso").click()
    expect(portal.locator("#ixs-recurso-modal")).to_have_count(0)
    assert len(saves) == 2


def test_read_error_retries_when_returning(portal, resources, fixed_day):
    _, result, _, _, _ = resources
    result.update({"ok": False, "error": "Sin asignaciones"})
    open_resources(portal)
    expect(portal.locator(".ixs-resources-error")).to_have_text(
        "Sin asignaciones"
    )
    result["ok"] = True
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Recursos", exact=True
    ).click()
    expect(
        portal.locator("#ixs-tab-contenido .ixs-resources-error")
    ).to_have_count(0)
    expect(
        portal.locator("tbody tr").filter(has_text="Ana Pérez")
    ).to_contain_text("160 h")


@pytest.mark.parametrize("failure", ["network", "forbidden"])
def test_write_transport_error_can_retry(portal, resources, fixed_day, failure):
    pattern = "**/screens/proyectos/AMK.008/recursos/guardar/"

    def fail(route):
        if failure == "network":
            route.abort("failed")
        else:
            route.fulfill(status=403, json={"detail": "No tienes acceso"})

    portal.route(pattern, fail)
    open_resources(portal)
    edit(portal, "O'Connor")
    form = portal.locator("#ixs-recurso-form")
    form.get_by_role("button", name="Guardar recurso").click()
    expect(portal.locator("#ixs-recurso-error")).not_to_have_text("")
    expect(form.get_by_role("button", name="Guardar recurso")).to_be_enabled()
    expect(form.locator('[name="rol"]')).to_have_value("QA")
    portal.unroute(pattern, fail)
    form.get_by_role("button", name="Guardar recurso").click()
    expect(portal.locator("#ixs-recurso-modal")).to_have_count(0)


def test_double_submit_is_blocked_and_state_refreshes_in_executive(
    portal, resources, fixed_day
):
    _, result, _, _, _ = resources
    open_resources(portal)
    edit(portal, "Ana Pérez")
    form = portal.locator("#ixs-recurso-form")
    form.locator('[name="activo"]').select_option("true")
    held = []
    portal.route(
        "**/screens/proyectos/AMK.008/recursos/guardar/",
        lambda route: held.append(route),
    )
    with portal.expect_request(
        "**/screens/proyectos/AMK.008/recursos/guardar/"
    ):
        form.get_by_role("button", name="Guardar recurso").click()
    expect(form.get_by_role("button", name="Guardando…")).to_be_disabled()
    form.evaluate("form=>form.requestSubmit()")
    result["filas"][0]["activo"] = True
    assert len(held) == 1
    held[0].fulfill(json={"data": result, "meta": {}})
    expect(portal.locator("#ixs-recurso-modal")).to_have_count(0)
    portal.wait_for_load_state("networkidle")
    assert len(held) == 1
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    expect(
        portal.locator(
            "[data-resource-workload] "
            'td[title="Recurso inactivo en el proyecto"]'
        )
    ).to_have_count(0)


def test_source_text_is_safe_and_editor_can_cancel(
    portal, resources, fixed_day
):
    _, result, _, saves, _ = resources
    text = '<img src=x onerror="window.resourceInjected=true">'
    result["filas"].append(
        {"nombre": text, "rol": text, "horasEstimadas": 0, "activo": True}
    )
    open_resources(portal)
    edit(portal, text)
    expect(portal.locator('#ixs-recurso-form [name="nombre"]')).to_have_value(
        text
    )
    expect(portal.locator('#ixs-recurso-form [name="rol"]')).to_have_value(text)
    assert (
        portal.locator("#ixs-recurso-modal img, #ixs-tab-contenido img").count()
        == 0
    )
    assert portal.evaluate("window.resourceInjected") is None
    portal.get_by_role("button", name="Cancelar", exact=True).click()
    expect(portal.locator("#ixs-recurso-modal")).to_have_count(0)
    assert saves == []


def test_late_records_do_not_replace_new_resource_read(
    portal, resources, fixed_day
):
    portal.goto(portal.base + PAGE)
    portal.wait_for_load_state("networkidle")
    held = []

    def hold_first(route):
        if held:
            route.fallback()
        else:
            held.append(route)

    portal.route("**/screens/proyectos/AMK.008/registros/", hold_first)
    with portal.expect_request("**/screens/proyectos/AMK.008/registros/"):
        portal.locator(".ixs-nav").get_by_role(
            "button", name="Recursos", exact=True
        ).click()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Recursos", exact=True
    ).click()
    row = portal.locator("tbody tr").filter(has_text="Ana Pérez")
    expect(row).to_contain_text("160 h")
    held[0].fulfill(
        json={
            "data": {
                "ok": True,
                "registros": [{"recurso": "Ana Pérez", "duracion": 999}],
            },
            "meta": {},
        }
    )
    portal.wait_for_load_state("networkidle")
    expect(row).to_contain_text("160 h")
