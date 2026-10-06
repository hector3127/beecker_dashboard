"""Pruebas de integracion con Django (requieren pytest-django)."""

import copy

import pytest

from apps.dashboard.cache import clear_cached_dashboard
from tests.dashboard.sample_data import SHEETS
from tests.fakes import InMemorySheetRepository

pytestmark = pytest.mark.django_db

RPC_URL = "/api/rpc/{name}/"


def call_rpc(client, name, *args):
    return client.post(
        RPC_URL.format(name=name),
        data={"args": list(args)},
        content_type="application/json",
    )


@pytest.fixture
def repository(monkeypatch):
    sheets = copy.deepcopy(SHEETS)
    sheets["Registros_Tiempo"] = [
        [
            "ID_Registro",
            "Proyecto",
            "Recurso",
            "Fecha",
            "Duracion_Hrs",
            "Costing_Rate",
            "Billable",
        ],
        ["T-1", "P-1", "Ana", 46296, 2, 20, "YES"],
    ]
    fake_repository = InMemorySheetRepository(sheets)
    monkeypatch.setattr(
        "apps.dashboard.rpc.build_sheet_repository",
        lambda: fake_repository,
    )
    clear_cached_dashboard()
    yield fake_repository
    clear_cached_dashboard()


def test_portal_serves_legacy_panel_with_shim(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"gas_shim.js" in response.content
    assert b"tpl-dashboard" in response.content


def test_function_not_migrated_returns_controlled_error(client):
    response = call_rpc(client, "obtenerVistaCuentaBeecker", "ACME")

    assert response.status_code == 404
    assert response.json()["code"] == "ERR_RPC_NOT_MIGRATED"


def test_wrong_number_of_arguments_is_rejected(client, repository):
    response = call_rpc(client, "getFiltrosDisponibles", "sobra")

    assert response.status_code == 400
    assert response.json()["code"] == "ERR_INVALID_REQUEST"


def test_available_filters(client, repository):
    response = call_rpc(client, "getFiltrosDisponibles")

    assert response.status_code == 200
    result = response.json()["result"]
    assert result["clientes"][0] == "Todos los clientes"
    assert len(result["proyectos"]) == 5


def test_dashboard_general_view_is_cached(client, repository):
    first_response = call_rpc(client, "getDashboardData", None)
    repository.sheets["Proyectos"] = repository.sheets["Proyectos"][:1]
    second_response = call_rpc(client, "getDashboardData", None)

    assert first_response.status_code == 200
    assert second_response.json()["result"]["kpis"]["totalProyectos"] == 5


def test_clockify_source_requires_workspace(client, repository, settings):
    settings.TIME_ENTRY_SOURCE = "clockify"
    settings.CLOCKIFY_API_KEY = "clave-de-prueba"
    settings.CLOCKIFY_WORKSPACE_ID = ""

    response = call_rpc(client, "getDashboardData", {"proyecto": "P-1"})

    assert response.status_code == 409
    assert response.json()["code"] == "ERR_CLOCKIFY_CONFIG"
    assert "clockify_workspaces" in response.json()["message"]


def test_clockify_config_hides_api_key(client, settings):
    settings.CLOCKIFY_API_KEY = "abcdef123456"

    response = call_rpc(client, "obtenerConfigClockify")

    result = response.json()["result"]
    assert result["sufijo"] == "3456"
    assert "abcdef123456" not in str(result)


def test_top_risks_without_azure_config_returns_error(client, settings):
    settings.AZURE_DEVOPS_ORGANIZATION = ""

    response = call_rpc(client, "obtenerTopRiesgosPortafolioAzure")

    result = response.json()["result"]
    assert response.status_code == 200
    assert result["ok"] is False
    assert "AZURE_DEVOPS_ORGANIZATION" in result["error"]


def test_capacity_rpcs_are_registered(client, monkeypatch, settings):
    from tests.capacidad.sample_data import SHEETS as CAPACITY_SHEETS

    settings.AZURE_DEVOPS_ORGANIZATION = ""
    monkeypatch.setattr(
        "apps.capacidad.rpc.build_sheet_repository",
        lambda: InMemorySheetRepository(copy.deepcopy(CAPACITY_SHEETS)),
    )

    base = call_rpc(client, "capacidadInstaladaBase", "2026-10").json()
    project = call_rpc(
        client,
        "capacidadInstaladaDatosProyecto",
        "RAS.001_S2",
        "",
        "2026-10",
        False,
    ).json()

    assert base["result"]["ok"] is True
    assert base["result"]["bandaColumna"] == "octubre 2026"
    assert project["result"] == {
        "ok": False,
        "inicio": "",
        "fin": "",
        "error": "Conecta Azure DevOps desde Configuración.",
    }


def test_warm_cache_runs_every_view(repository, settings, monkeypatch):
    from io import StringIO

    from django.core.management import call_command

    settings.AZURE_DEVOPS_ORGANIZATION = ""
    monkeypatch.setattr(
        "apps.ejecutivo.rpc.build_sheet_repository",
        lambda: repository,
    )
    output = StringIO()

    call_command("warm_cache", stdout=output)

    text = output.getvalue()
    assert "getDashboardData: listo" in text
    assert "obtenerTopRiesgosPortafolioAzure: " in text
    assert "obtenerResumenIXBRaaS: listo" in text


def test_ixs_rpcs_are_registered(client, settings):
    settings.AZURE_DEVOPS_ORGANIZATION = ""

    panel = call_rpc(client, "obtenerPanelAzureProyectoIXS", "").json()
    raid = call_rpc(client, "ixsRaidListarProyecto", "GPO.007").json()
    create = call_rpc(client, "ixsRaidCrearRegistro", "GPO.007", "Risk", {})

    assert panel["result"] == {"ok": False, "error": "Selecciona un proyecto."}
    assert raid["result"] == {
        "ok": False,
        "error": "Conecta Azure DevOps desde Configuración.",
    }
    assert create.json()["result"]["ok"] is False


def test_ixs_sheet_rpcs_are_registered(client, monkeypatch):
    repository = InMemorySheetRepository({})
    monkeypatch.setattr(
        "apps.daily.ixs_rpc.build_sheet_repository",
        lambda: repository,
    )

    actions = call_rpc(client, "ixsClienteAccionesLeer", "GPO.007").json()
    invalid = call_rpc(client, "ixsPlanGuardar", "otro").json()
    swapped = call_rpc(client, "ixsEliminarContacto", "uid-1", "GPO.007")

    assert actions["result"]["acciones"]["filas"] == []
    assert invalid["result"] == {
        "ok": False,
        "error": "Tipo de registro inválido.",
    }
    assert swapped.json()["result"] == {
        "ok": False,
        "error": "Registro no encontrado.",
    }


def test_account_rpcs_are_registered(client):
    view = call_rpc(client, "obtenerVistaCuentaBeecker", "").json()
    opportunity = call_rpc(client, "beeCuentaGuardarOportunidad", "", {}).json()

    assert view["result"] == {"ok": False, "error": "Selecciona un cliente."}
    assert opportunity["result"] == {
        "ok": False,
        "error": "Selecciona una cuenta.",
    }


def test_claude_rpcs_are_registered(client, settings):
    settings.ANTHROPIC_API_KEY = "sk-ant-secreta-9876"

    config = call_rpc(client, "obtenerConfigClaude").json()["result"]
    saved = call_rpc(client, "guardarApiKeyClaude", "otra").json()["result"]
    short = call_rpc(client, "ixsRaidSugerirClaude", "Issue", "corto").json()

    assert config["configurado"] is True
    assert config["sufijo"] == "9876"
    assert "secreta" not in str(config)
    assert saved["ok"] is False
    assert short["result"]["ok"] is False


def test_aer_rpcs_are_registered(client, monkeypatch):
    repository = InMemorySheetRepository(
        {"Proyectos": [["ID_Proyecto", "Servicio"], ["IXB.001", "IXB"]]},
    )
    monkeypatch.setattr(
        "apps.aer.rpc.build_sheet_repository", lambda: repository
    )

    empty = call_rpc(client, "getDashboardAERTYMProyecto", "").json()
    other = call_rpc(client, "getDashboardAERTYMProyecto", "IXB.001").json()

    assert empty["result"] == {"ok": False, "error": "Falta ID de proyecto."}
    assert other["result"]["error"] == (
        "El proyecto no es AER/T&M. Servicio detectado: IXB"
    )
