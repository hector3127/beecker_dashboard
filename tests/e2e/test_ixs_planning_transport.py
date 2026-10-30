"""Planeación parcial: API sin cambiar su presentación ni controladores."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
PAGE = "/proyectos/AMK.008/"


@pytest.fixture
def planning(portal, ixs, monkeypatch):
    from apps.portal.api import project_detail as api

    plan = {
        "ok": True,
        "vacaciones": [
            {
                "uid": "vac/'1",
                "recurso": "Ana Pérez",
                "inicio": "2026-10-26",
                "fin": "2026-10-30",
                "estado": "Aprobada",
                "comentarios": "Descanso",
                "registradoPor": "DM",
            }
        ],
        "compromisos": [
            {
                "uid": "hito/'1",
                "actividad": "Entrega adicional",
                "fecha": "2026-10-29",
                "estado": "Pendiente",
                "responsable": "Ana Pérez",
                "tipo": "Hito",
            }
        ],
    }
    items = [
        {
            "id": 101,
            "titulo": "REQ-01 Desarrollo",
            "tipo": "To Be",
            "estado": "Active",
            "asignadoA": "Ana Pérez",
            "avanceTotal": 40,
            "fechaLimiteDev": "2026-10-22",
            "iterationPath": "AMK\\Development",
            "url": "https://example.invalid/workitems/101",
        },
        {
            "id": 102,
            "titulo": "CR-02 Validación",
            "tipo": "Change Request",
            "estado": "Closed",
            "asignadoA": "Luis",
            "avanceTotal": 100,
            "fechaLimiteDev": "2026-10-29",
            "iterationPath": "AMK\\Deployment",
            "url": "https://example.invalid/workitems/102",
        },
    ]
    azure = {"ok": True, "items": items, "allItems": items}
    calls, errors = [], []

    def save(kind, payload):
        calls.append(("save", kind, copy.deepcopy(payload)))
        if errors:
            return {"ok": False, "error": errors.pop(0)}
        key = "vacaciones" if kind == "vacacion" else "compromisos"
        row = {**payload, "uid": payload.get("uid") or "created"}
        plan[key] = [x for x in plan[key] if x["uid"] != row["uid"]] + [row]
        return copy.deepcopy(plan)

    def delete(kind, project, uid):
        calls.append(("delete", kind, project, uid))
        key = "vacaciones" if kind == "vacacion" else "compromisos"
        plan[key] = [x for x in plan[key] if x["uid"] != uid]
        return copy.deepcopy(plan)

    monkeypatch.setattr(
        api, "planning_dashboard", lambda project: copy.deepcopy(plan)
    )
    monkeypatch.setattr(
        api, "get_ixs_panel", lambda *args: copy.deepcopy(azure)
    )
    monkeypatch.setattr(api, "save_plan_dashboard", save)
    monkeypatch.setattr(api, "delete_plan_dashboard", delete)

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        if name in {"ixsPlanLeer", "obtenerPanelAzureProyectoIXS"}:
            route.fulfill(
                json={
                    "ok": True,
                    "result": (plan if name == "ixsPlanLeer" else azure),
                }
            )
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    return plan, azure, calls, errors


def open_planning(portal):
    portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(portal.locator("#ixs-plan-vacaciones")).to_contain_text("Ana Pérez")
    portal.wait_for_load_state("networkidle")


def test_reads_and_vacation_save_edit_delete_use_api(
    portal, planning, fixed_day
):
    _, _, calls, _ = planning
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    open_planning(portal)
    portal.get_by_role(
        "button", name="+ Registrar vacaciones", exact=True
    ).click()
    form = portal.locator("#ixs-plan-form")
    form.locator('[name="recurso"]').fill("O'Connor")
    form.locator('[name="inicio"]').fill("2026-11-02")
    form.locator('[name="fin"]').fill("2026-11-03")
    form.get_by_role("button", name="Guardar", exact=True).click()
    expect(portal.locator("#ixs-plan-modal")).to_have_count(0)
    row = portal.locator("#ixs-plan-vacaciones tbody tr").filter(
        has_text="O'Connor"
    )
    expect(row).to_have_count(1)
    row.get_by_role("button").click()
    form.locator('[name="comentarios"]').fill("Cambio")
    form.get_by_role("button", name="Guardar", exact=True).click()
    expect(row).to_contain_text("Cambio")
    row.get_by_role("button").click()
    portal.once("dialog", lambda dialog: dialog.accept())
    form.get_by_role("button", name="Eliminar", exact=True).click()
    expect(row).to_have_count(0)
    assert [x[0] for x in calls] == ["save", "save", "delete"]
    assert calls[0][2]["idProyecto"] == "AMK.008"
    assert calls[1][2]["uid"] == "created"
    assert calls[2][2:] == ("AMK.008", "created")
    assert any(url.endswith("/planeacion/azure/") for url in requests)
    assert any(url.endswith("/planeacion/") for url in requests)
    assert not any("/api/rpc/" in url for url in requests)


def test_hito_error_preserves_form_and_retry_uses_api(
    portal, planning, fixed_day
):
    _, _, calls, errors = planning
    errors.append("Indica actividad y fecha válida.")
    open_planning(portal)
    portal.get_by_role("button", name="+ Agregar hito", exact=True).click()
    form = portal.locator("#ixs-plan-form")
    form.locator('[name="actividad"]').fill("Entrega QA")
    form.locator('[name="fecha"]').fill("2026-11-02")
    form.get_by_role("button", name="Guardar", exact=True).click()
    expect(portal.locator("#ixs-plan-error")).to_have_text(
        "Indica actividad y fecha válida."
    )
    expect(form.locator('[name="actividad"]')).to_have_value("Entrega QA")
    form.get_by_role("button", name="Guardar", exact=True).click()
    expect(portal.locator("#ixs-plan-modal")).to_have_count(0)
    assert len(calls) == 2
    assert calls[1][1] == "compromiso"
    assert calls[1][2]["tipo"] == "Hito"


def test_failed_reads_can_be_retried_by_reopening_tab(
    portal, planning, fixed_day
):
    plan, azure, _, _ = planning
    plan.update(ok=False, error="No se pudo leer planeación.")
    azure.update(ok=False, error="Azure no disponible.")
    portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(portal.locator("#ixs-tab-contenido")).to_contain_text(plan["error"])
    expect(portal.locator("#ixs-plan-attention")).to_contain_text(
        azure["error"]
    )
    plan["ok"] = azure["ok"] = True
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Ejecutivo", exact=True
    ).click()
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Planeación", exact=True
    ).click()
    expect(portal.locator("#ixs-plan-vacaciones")).to_contain_text("Ana Pérez")
    expect(portal.locator("#ixs-tab-contenido")).not_to_contain_text(
        plan["error"]
    )


def test_azure_data_keeps_summary_and_local_filters(
    portal, planning, fixed_day
):
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    open_planning(portal)
    expect(portal.locator("#ixs-plan-attention")).to_contain_text(
        "1 trabajos vencidos"
    )
    expect(portal.locator("#ixs-azure-table tbody tr")).to_have_count(2)
    before = len(requests)
    portal.locator("#ixs-azure-filter-estado").select_option("Active")
    expect(portal.locator("#ixs-azure-table tbody tr")).to_have_count(1)
    expect(portal.locator("#ixs-azure-table")).to_contain_text("Desarrollo")
    portal.locator("#ixs-azure-filter-search").fill("Sin coincidencia")
    expect(portal.locator("#ixs-azure-table")).to_contain_text(
        "No hay work items"
    )
    assert len(requests) == before
