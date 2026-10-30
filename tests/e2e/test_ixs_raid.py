"""Gestión RAID: API v1, mismo diseño y conservación de la última vista."""

import copy

import pytest
from playwright.sync_api import expect

from tests.e2e.test_aer_executive import fixed_day as fixed_day
from tests.e2e.test_ixs_executive import PAGE
from tests.e2e.test_ixs_executive import ixs as ixs
from tests.e2e.test_project_detail_entry import project_detail as project_detail

pytestmark = pytest.mark.django_db(transaction=True)
BASE = {
    "asignadoA": "Ana Pérez",
    "estado": "Active",
    "iterationPath": "AMK\\Development",
    "areaPath": "AMK",
    "ultimaActualizacion": "2026-10-20T10:00:00Z",
    "diasSinActualizar": 3,
    "url": "https://dev.azure.com/o/p/_workitems/edit/1",
    "relacionados": [{"id": 77}],
}
ROWS = [
    {
        **BASE,
        "id": 11,
        "tipo": "Risk",
        "titulo": "Accesos pendientes <b>x</b>",
        "severidad": "1 - Crítico",
        "probabilidad": "2 - Medio",
        "descripcion": (
            "<p>Sin accesos al ambiente</p><br>Se detiene QA &amp; UAT"
        ),
        "prioridad": "1",
        "riskDetalle": {
            "planMitigacion": "Solicitar accesos",
            "triggers": "Retraso &gt; 3 días",
            "categoria": "Técnico",
            "partesInteresadas": "Cliente",
        },
    },
    {
        **BASE,
        "id": 12,
        "tipo": "Risk",
        "titulo": "Riesgo cerrado",
        "estado": "Closed",
        "severidad": "3 - Bajo",
        "diasSinActualizar": 40,
    },
    {
        **BASE,
        "id": 13,
        "tipo": "Issue",
        "titulo": "Servidor caído",
        "asignadoA": "Luis",
        "severidad": "2 - Alto",
        "diasSinActualizar": 12,
        "iterationPath": "AMK\\Deployment",
        "issueDetalle": {
            "plan": "Reiniciar",
            "reporter": "Ana",
            "effortCompleted": 3,
        },
    },
    {
        **BASE,
        "id": 14,
        "tipo": "Opportunity",
        "titulo": "Automatizar reporte",
        "asignadoA": "",
        "severidad": "",
        "impacto": "Alto",
        "probabilidad": "Medio",
        "relacionados": [],
        "opportunityDetalle": {
            "improvementPlan": "Script",
            "followUp": "Mensual",
        },
    },
    {
        **BASE,
        "id": 15,
        "tipo": "Task",
        "titulo": "Otro tipo",
        "relacionados": [],
    },
]


@pytest.fixture
def raid(portal, ixs, monkeypatch):
    from apps.portal.api import project_detail as api

    calls = []
    answer = {
        "result": {"ok": True, "registros": ROWS, "aviso": ""},
        "fail": None,
    }

    def source(project, force=False):
        calls.append((project, force))
        if answer["fail"]:
            raise answer["fail"]
        return copy.deepcopy(answer["result"])

    monkeypatch.setattr(api.ixs_rpc, "list_raid", source)

    def rpc(route):
        name = route.request.url.rstrip("/").rsplit("/", 1)[-1]
        if name == "ixsRaidListarProyecto":
            route.fulfill(
                json={
                    "ok": True,
                    "result": source(*route.request.post_data_json["args"]),
                }
            )
        else:
            route.fallback()

    portal.route("**/api/rpc/**", rpc)
    return calls, answer


def open_raid(portal):
    portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Gestión RAID", exact=True
    ).click()
    expect(portal.locator("#ixs-raid-tabla tbody tr")).to_have_count(5)
    portal.wait_for_load_state("networkidle")


def nothing(portal):
    pass


def detail(row_id):
    def step(portal):
        portal.locator(
            "#ixs-raid-tabla tbody tr", has_text=f"#{row_id}"
        ).get_by_role("button").click()
        expect(portal.locator("#ixs-raid-detail-overlay")).to_be_visible()

    return step


def filtered(portal):
    portal.locator("#ixs-raid-filter-tipo").select_option("Risk")
    portal.locator("#ixs-raid-filter-search").fill("acce")
    expect(portal.locator("#ixs-raid-tabla tbody tr")).to_have_count(1)


def test_reads_by_api_and_sync_forces_the_source(portal, raid, fixed_day):
    calls, _ = raid
    requests = []
    portal.on("request", lambda request: requests.append(request.url))
    open_raid(portal)
    assert calls == [("AMK.008", False)]
    portal.get_by_role("button", name="Sincronizar").click()
    expect(portal.locator("#ixs-raid-notice")).to_contain_text(
        "Origen: Azure DevOps"
    )
    assert calls[-1] == ("AMK.008", True)
    assert not any("ixsRaidListarProyecto" in url for url in requests)
    assert any("/raid-registro/" in url for url in requests)


def test_text_is_never_html_and_details_close(portal, raid, fixed_day):
    open_raid(portal)
    expect(portal.locator("#ixs-raid-tabla")).to_contain_text(
        "Accesos pendientes <b>x</b>"
    )
    expect(portal.locator("#ixs-raid-tabla b")).to_have_count(0)
    detail(11)(portal)
    expect(portal.locator(".ixs-raid-risk-card")).to_contain_text(
        ["Descripción"]
    )
    expect(portal.locator("#ixs-raid-detail-overlay")).to_contain_text(
        "Se detiene QA & UAT"
    )
    portal.locator("#ixs-raid-detail-overlay header button").click()
    expect(portal.locator("#ixs-raid-detail-overlay")).to_have_count(0)
    detail(13)(portal)
    portal.locator("#ixs-raid-detail-overlay").click(position={"x": 3, "y": 3})
    expect(portal.locator("#ixs-raid-detail-overlay")).to_have_count(0)


def test_attention_list_shows_more_on_demand(portal, raid, fixed_day):
    calls, answer = raid
    extra = [
        {**BASE, "id": 100 + i, "tipo": "Issue", "titulo": f"Extra {i}"}
        for i in range(5)
    ]
    answer["result"] = {"ok": True, "registros": [*ROWS, *extra], "aviso": ""}
    portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Gestión RAID", exact=True
    ).click()
    expect(portal.locator(".ixs-raid-att-row:visible")).to_have_count(4)
    button = portal.locator("#ixs-raid-att-btn")
    expect(button).to_have_text("Ver más (5)")
    button.click()
    expect(portal.locator(".ixs-raid-att-row:visible")).to_have_count(9)
    expect(button).to_have_text("Ver menos")


def test_failed_refresh_keeps_the_last_view_and_first_error_is_shown(
    portal, raid, fixed_day
):
    calls, answer = raid
    answer["fail"] = RuntimeError("Azure fuera de servicio")
    portal.goto(portal.base + PAGE)
    portal.locator(".ixs-nav").get_by_role(
        "button", name="Gestión RAID", exact=True
    ).click()
    failure = portal.locator("#ixs-raid-tabla .ixs-azure-empty")
    expect(failure).not_to_have_text("Consultando Azure DevOps…")
    expect(failure).to_have_text(
        "El servidor no pudo completar la consulta. Intenta de nuevo."
    )
    answer["fail"] = None
    portal.get_by_role("button", name="Sincronizar").click()
    expect(portal.locator("#ixs-raid-tabla tbody tr")).to_have_count(5)
    answer["result"] = {"ok": False, "error": "Sin permiso Azure"}
    portal.get_by_role("button", name="Sincronizar").click()
    expect(portal.locator("#ixs-raid-sync-warning")).to_contain_text(
        "Se conservan los datos de la consulta anterior"
    )
    expect(portal.locator("#ixs-raid-tabla tbody tr")).to_have_count(5)
