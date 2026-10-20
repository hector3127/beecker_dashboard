"""Carga del portafolio: cache corta y errores controlados."""

import pytest
from django.core.cache import cache

from apps.portal.constants import (
    CAPACITY_CACHE_PREFIX,
    EVA2_CACHE_KEY,
    FACTURABILITY_CACHE_PREFIX,
    PORTFOLIO_CACHE_KEY,
    PROJECT_CACHE_PREFIX,
)
from apps.portal.services import (
    capacity_loader,
    eva_loader,
    facturability_loader,
    portfolio_loader,
    project_loader,
)
from core.exceptions import ConfigurationError
from tests.fakes import InMemorySheetRepository
from tests.portal.builders import make_project


@pytest.fixture(autouse=True)
def clean_cache():
    cache.delete(PORTFOLIO_CACHE_KEY)
    yield
    cache.delete(PORTFOLIO_CACHE_KEY)


def stub_sources(monkeypatch, calls):
    monkeypatch.setattr(
        portfolio_loader,
        "build_sheet_repository",
        lambda: object(),
    )
    monkeypatch.setattr(
        portfolio_loader,
        "build_time_entry_provider",
        lambda repository: object(),
    )

    def fake_build(reader, provider, now):
        calls.append(now)
        return (make_project(),)

    monkeypatch.setattr(portfolio_loader, "build_project_views", fake_build)


def test_loads_projects_and_reuses_the_cache(monkeypatch):
    calls = []
    stub_sources(monkeypatch, calls)

    first = portfolio_loader.load_portfolio()
    second = portfolio_loader.load_portfolio()

    assert first.error == ""
    assert [item.project_id for item in first.projects] == ["P-1"]
    assert second.projects == first.projects
    assert len(calls) == 1
    assert calls[0].tzinfo is None


def test_missing_configuration_returns_message_and_is_not_cached(monkeypatch):
    def broken():
        raise ConfigurationError("Define GOOGLE_SPREADSHEET_ID.")

    monkeypatch.setattr(portfolio_loader, "build_sheet_repository", broken)

    result = portfolio_loader.load_portfolio()

    assert result.projects == ()
    assert "Falta configurar el dashboard." in result.error
    assert "GOOGLE_SPREADSHEET_ID" in result.error
    assert cache.get(PORTFOLIO_CACHE_KEY) is None


def test_eva1_loader_builds_the_view(monkeypatch):
    monkeypatch.setattr(
        eva_loader,
        "get_aer_tym_consumption",
        lambda ids: {
            "ok": True,
            "items": [{"id": project_id, "burn": 0} for project_id in ids],
        },
    )
    monkeypatch.setattr(eva_loader, "build_sheet_repository", lambda: object())
    monkeypatch.setattr(
        eva_loader,
        "load_aer_tym_summary",
        lambda reader: {
            "ok": True,
            "filas": [
                {
                    "idProyecto": "AER.001",
                    "servicio": "AER",
                    "deliveryManager": "Laura",
                    "fte": 1,
                    "budget": 100,
                },
            ],
        },
    )

    result = eva_loader.load_eva1()

    assert result.error == ""
    assert result.view.total_projects == 1


def test_eva1_loader_ignores_a_malformed_summary(monkeypatch):
    monkeypatch.setattr(eva_loader, "build_sheet_repository", lambda: object())
    monkeypatch.setattr(
        eva_loader,
        "load_aer_tym_summary",
        lambda reader: {"ok": True},
    )

    assert eva_loader.load_eva1().view.total_projects == 0


def test_eva1_loader_returns_message_when_sheets_fail(monkeypatch):
    def broken():
        raise ConfigurationError("Define GOOGLE_SPREADSHEET_ID.")

    monkeypatch.setattr(eva_loader, "build_sheet_repository", broken)

    result = eva_loader.load_eva1()

    assert "Falta configurar el dashboard." in result.error
    assert result.view.total_projects == 0


def test_eva2_loader_builds_the_view_and_caches(monkeypatch):
    cache.delete(EVA2_CACHE_KEY)
    calls = []

    def fake_summary():
        calls.append(1)
        return {
            "ok": True,
            "filas": [
                {
                    "idProyecto": "AMK.015",
                    "servicio": "IXB",
                    "deliveryManager": "Laura",
                    "status": "Discovery",
                },
            ],
        }

    monkeypatch.setattr(eva_loader, "get_ixb_raas_summary", fake_summary)

    first = eva_loader.load_eva2()
    second = eva_loader.load_eva2()

    assert first.error == ""
    assert first.view.total_projects == 1
    assert second.view.total_projects == 1
    assert len(calls) == 1
    cache.delete(EVA2_CACHE_KEY)


def test_eva2_loader_reports_errors_and_does_not_cache_them(monkeypatch):
    cache.delete(EVA2_CACHE_KEY)
    monkeypatch.setattr(
        eva_loader,
        "get_ixb_raas_summary",
        lambda: {"ok": False, "error": "Azure no responde."},
    )

    result = eva_loader.load_eva2()

    assert result.error == "Azure no responde."
    assert result.view.total_projects == 0
    assert cache.get(EVA2_CACHE_KEY) is None


def test_eva2_loader_with_malformed_summary(monkeypatch):
    cache.delete(EVA2_CACHE_KEY)
    monkeypatch.setattr(
        eva_loader,
        "get_ixb_raas_summary",
        lambda: {"ok": True},
    )

    assert eva_loader.load_eva2().view.total_projects == 0
    cache.delete(EVA2_CACHE_KEY)


def test_eva2_loader_uses_default_message_when_error_is_empty(monkeypatch):
    cache.delete(EVA2_CACHE_KEY)
    monkeypatch.setattr(
        eva_loader,
        "get_ixb_raas_summary",
        lambda: {"ok": False},
    )

    assert "No se pudo leer IXB y RaaS" in eva_loader.load_eva2().error


def test_capacity_loader_caches_per_month_and_can_refresh(monkeypatch):
    cache.delete(f"{CAPACITY_CACHE_PREFIX}2026-10")
    calls = []

    def fake_base(month):
        calls.append(month)
        return {"ok": True, "mes": month, "filas": []}

    monkeypatch.setattr(capacity_loader, "get_capacity_base", fake_base)

    first = capacity_loader.load_capacity("2026-10")
    capacity_loader.load_capacity("2026-10")
    capacity_loader.load_capacity("2026-10", refresh=True)

    assert first.error == ""
    assert first.data["mes"] == "2026-10"
    assert calls == ["2026-10", "2026-10"]
    cache.delete(f"{CAPACITY_CACHE_PREFIX}2026-10")


def test_capacity_loader_reports_errors_and_does_not_cache_them(monkeypatch):
    cache.delete(f"{CAPACITY_CACHE_PREFIX}2026-09")
    monkeypatch.setattr(
        capacity_loader,
        "get_capacity_base",
        lambda month: {"ok": False, "error": "Falta la hoja Recursos."},
    )

    result = capacity_loader.load_capacity("2026-09")

    assert result.error == "Falta la hoja Recursos."
    assert result.data == {}
    assert cache.get(f"{CAPACITY_CACHE_PREFIX}2026-09") is None

    monkeypatch.setattr(
        capacity_loader,
        "get_capacity_base",
        lambda month: {"ok": False},
    )

    assert "No se pudo leer Capacidad instalada" in (
        capacity_loader.load_capacity("2026-09").error
    )


def test_project_loader_caches_and_reports_errors(monkeypatch):
    key = f"{PROJECT_CACHE_PREFIX}HIS-1"
    cache.delete(key)
    calls = []

    def fake_dashboard(project_id):
        calls.append(project_id)
        return {"proyecto": {"id": project_id}}

    monkeypatch.setattr(
        project_loader, "get_executive_dashboard", fake_dashboard
    )

    first = project_loader.load_project_dashboard("HIS-1")
    project_loader.load_project_dashboard("HIS-1")

    assert first.error == ""
    assert first.data["proyecto"]["id"] == "HIS-1"
    assert calls == ["HIS-1"]
    cache.delete(key)

    monkeypatch.setattr(
        project_loader,
        "get_executive_dashboard",
        lambda project_id: {"errorServidor": "Sin Clockify.", "proyecto": None},
    )
    failed = project_loader.load_project_dashboard("HIS-1")

    assert failed.error == "Sin Clockify."
    assert failed.data == {}
    assert cache.get(key) is None

    monkeypatch.setattr(
        project_loader,
        "get_executive_dashboard",
        lambda project_id: {},
    )

    assert "No se pudo leer el detalle" in (
        project_loader.load_project_dashboard("HIS-1").error
    )


def test_facturability_loader_reads_gse_and_caches(monkeypatch):
    key = f"{FACTURABILITY_CACHE_PREFIX}2026-10"
    cache.delete(key)
    calls = []

    def fake_gse(month):
        calls.append(month)
        return {"ok": True, "areas": [], "detalle": []}

    monkeypatch.setattr(facturability_loader, "read_gse_month", fake_gse)

    first = facturability_loader.load_month_sources("2026-10")
    facturability_loader.load_month_sources("2026-10")

    assert first.error == ""
    assert first.gse["ok"] is True
    assert first.gse["areas"] == []
    assert calls == ["2026-10"]
    assert cache.get(key) == first
    cache.delete(key)


def test_facturability_loader_reports_errors_without_cache(monkeypatch):
    key = f"{FACTURABILITY_CACHE_PREFIX}2026-09"
    cache.delete(key)
    monkeypatch.setattr(
        facturability_loader,
        "read_gse_month",
        lambda month: {"ok": False, "error": "Clockify no está configurado."},
    )

    result = facturability_loader.load_month_sources("2026-09")

    assert result.error == "GSE: Clockify no está configurado."
    assert result.gse == {}
    assert cache.get(key) is None


def test_facturability_keeps_gse_data_without_capacity_roster(monkeypatch):
    key = f"{FACTURABILITY_CACHE_PREFIX}2026-01"
    cache.delete(key)
    gse = {
        "ok": True,
        "areas": [{"area": "DEV", "recursos": 1}],
        "detalle": [{"recurso": "Ana", "area": "DEV", "horas": 84}],
    }
    monkeypatch.setattr(
        facturability_loader,
        "read_gse_month",
        lambda month: gse,
    )

    def unavailable_capacity(*args, **kwargs):
        raise AssertionError("Facturabilidad no depende de Capacidad.")

    monkeypatch.setattr(
        capacity_loader,
        "get_capacity_base",
        unavailable_capacity,
    )

    try:
        result = facturability_loader.load_month_sources("2026-01")
        assert result.error == ""
        assert result.gse == gse
    finally:
        cache.delete(key)


def test_facturability_applies_bands_roster_without_capacity_loader(
    monkeypatch,
):
    key = f"{FACTURABILITY_CACHE_PREFIX}2026-09"
    cache.delete(key)
    monkeypatch.setattr(
        facturability_loader,
        "read_gse_month",
        lambda month: {
            "ok": True,
            "areas": [],
            "detalle": [],
            "plantilla": [{"nombre": "Ana", "rol": "DEV"}],
        },
    )
    try:
        result = facturability_loader.load_month_sources("2026-09")
        assert result.error == ""
        assert result.gse["areas"] == []
    finally:
        cache.delete(key)


def test_read_gse_month_never_saves_to_sheets(monkeypatch):
    captured = {}

    class FakeLoader:
        def __init__(self, settings_tuple, sources, persist="unset"):
            captured["persist"] = persist

    reader = InMemorySheetRepository(
        {
            "Bandas/rol": [["Nombre", "ROL", "Octubre"], ["Ana", "DEV", "B1"]],
        }
    )
    monkeypatch.setattr(
        facturability_loader,
        "build_sheet_repository",
        lambda: reader,
    )
    monkeypatch.setattr(facturability_loader, "BaseStore", lambda *args: None)
    monkeypatch.setattr(facturability_loader, "MonthReportLoader", FakeLoader)
    monkeypatch.setattr(
        facturability_loader,
        "get_month",
        lambda context, request: {"ok": True, "request": request},
    )

    result = facturability_loader.read_gse_month("2026-10")

    assert captured["persist"] is None
    assert result["request"] == ("2026-10", "api", False, "")
    assert result["plantilla"] == [{"nombre": "Ana", "rol": "DEV"}]
    assert reader.appended_rows == []
    assert reader.replaced_rows == []


def test_year_months():
    assert facturability_loader.year_months("2026-03") == [
        "2026-01",
        "2026-02",
        "2026-03",
    ]
