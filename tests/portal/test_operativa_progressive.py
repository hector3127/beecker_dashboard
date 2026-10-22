"""Operativa entrega conteos antes de consultar consumos o Azure."""

from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.core.management import call_command
from django.test import RequestFactory

from apps.portal import views
from apps.portal.services import eva_loader
from apps.portal.services.eva1 import build_eva1_view
from core.management.commands import warm_cache
from tests.fakes import InMemorySheetRepository


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def base_repository():
    return InMemorySheetRepository(
        {
            "Proyectos": [
                ["ID_Proyecto", "Nombre", "Servicio", "Cliente", "Budget_Hrs"],
                ["IXB.001", "Robot", "IXB", "ACME", 100],
            ],
            "Historico_Proyectos": [
                ["Project ID", "Status", "Start", "Finish", "Delivery Manager"],
                ["IXB.001", "Discovery", "01/01/2026", "", "Ana"],
                ["IXB.001", "Deployment", "", "31/12/2026", "Ana"],
            ],
        }
    )


def request(**params):
    result = RequestFactory().get("/operativa/datos/", params)
    result.user = SimpleNamespace(is_authenticated=True)
    return result


def test_base_reads_only_sheets_and_saves_visible_counts(monkeypatch):
    heavy = Mock(side_effect=AssertionError("Heavy summary on first paint"))
    monkeypatch.setattr(eva_loader, "get_ixb_raas_summary", heavy)
    monkeypatch.setattr(eva_loader, "build_sheet_repository", base_repository)
    monkeypatch.setattr(
        views,
        "load_eva1",
        lambda **kwargs: eva_loader.Eva1Load(build_eva1_view([]), ""),
    )
    context = views.operativa_block_context(request())
    saved = views._operativa_snapshot(request())
    assert saved["summary"].in_progress == 1
    assert saved["loading"] is False
    assert saved["consumption_pending"] is True
    assert len(saved["managers"]) == 1
    assert saved["eva1_card"].time_cost.cost_percent is None
    assert context["consumption_pending"] is True
    heavy.assert_not_called()


def test_fresh_base_navigation_skips_sources_and_keeps_pending_blocks(
    monkeypatch,
):
    monkeypatch.setattr(eva_loader, "build_sheet_repository", base_repository)
    monkeypatch.setattr(
        views,
        "load_eva1",
        lambda **kwargs: eva_loader.Eva1Load(build_eva1_view([]), ""),
    )
    views.operativa_block_context(request())
    monkeypatch.setattr(
        views, "load_eva2", Mock(side_effect=AssertionError("Repeated read"))
    )
    assert views.operativa_block_context(request())["loading"] is False
    context = views.operativa_context(request())
    assert context["pending_blocks"] == "eva3,inversion,capacidad,eva4"


def test_independent_blocks_survive_stale_base_snapshot_writes():
    req = request()
    key = views._operativa_key(req)
    cache.set(key, {"consumption_pending": True, "investment": {}})
    cache.set(key + ":block:eva3", {"consumption_pending": False})
    cache.set(key + ":block:inversion", {"investment": {"complete": True}})
    # Una respuesta vieja no puede deshacer los bloques ya completados.
    cache.set(key, {"consumption_pending": True, "investment": {}})
    saved = views._operativa_snapshot(req)
    assert saved["consumption_pending"] is False
    assert saved["investment"]["complete"] is True


def test_default_warmer_does_not_run_legacy_steps(monkeypatch):
    portal = Mock(return_value={"ok": True})
    legacy = Mock(side_effect=AssertionError("Unused legacy cache"))
    monkeypatch.setattr(warm_cache, "warm_portal", portal)
    monkeypatch.setattr(warm_cache, "warm_sheets", legacy)
    call_command("warm_cache", stdout=StringIO())
    portal.assert_called_once_with()
    legacy.assert_not_called()


def test_base_only_warmer_does_not_start_full_portal(monkeypatch):
    portal = Mock(return_value={"ok": True})
    monkeypatch.setattr(warm_cache, "warm_portal", portal)
    call_command("warm_cache", base_only=True, stdout=StringIO())
    portal.assert_called_once_with(base_only=True)


def test_missing_consumption_reports_failure_without_caching_empty_success(
    monkeypatch,
):
    monkeypatch.setattr(eva_loader, "build_sheet_repository", lambda: object())
    monkeypatch.setattr(
        eva_loader,
        "load_aer_tym_summary",
        lambda reader: {
            "ok": True,
            "filas": [{"idProyecto": "AER.001", "budget": 100}],
        },
    )
    monkeypatch.setattr(
        eva_loader,
        "get_aer_tym_consumption",
        lambda ids: {"ok": False, "items": [], "error": "Sin conexion"},
    )
    result = eva_loader.load_eva1()
    assert "AER.001" in result.error
    assert cache.get("portal:eva3:consumption:AER.001") is None
    assert result.view.projects[0].burn is None
