"""Precalentamiento y reutilizacion de cortes completos del portal."""

from io import StringIO
from types import SimpleNamespace

from django.core.cache import cache
from django.core.management import call_command
from django.http import HttpResponse

from apps.portal import views
from apps.portal.services.facturability_loader import MonthSources
from core.exceptions import DashboardError
from core.management.commands import warm_cache


def test_portal_only_does_not_clear_cache_or_load_legacy(monkeypatch, db):
    cache.set("keep-this-cut", "saved")
    monkeypatch.setattr(warm_cache, "warm_portal", lambda: {"ok": True})
    monkeypatch.setattr(
        warm_cache,
        "warm_sheets",
        lambda: (_ for _ in ()).throw(AssertionError("Legacy read")),
    )
    output = StringIO()
    call_command("warm_cache", portal_only=True, stdout=output)
    assert "portal: listo" in output.getvalue()
    assert cache.get("keep-this-cut") == "saved"
    cache.clear()


def test_warmer_uses_all_portal_blocks_and_reports_partial_data(monkeypatch):
    calls = []

    def load(request):
        assert request.user.is_authenticated
        calls.append(request.GET["bloque"])
        error = "Sin Clockify" if request.GET["bloque"] == "inversion" else ""
        return {"block_error": error, "source_errors": []}

    monkeypatch.setattr(views, "operativa_block_context", load)
    monkeypatch.setattr(
        views,
        "operations_summary_data",
        lambda refresh=False: SimpleNamespace(errors=("Sin conexion",)),
    )
    monkeypatch.setattr(
        views,
        "comercial",
        lambda request: HttpResponse('<body data-portal-ready="true">'),
    )
    monkeypatch.setattr(
        views,
        "ejecutiva",
        lambda request: HttpResponse('<body data-portal-ready="true">'),
    )
    monkeypatch.setattr(
        "apps.portal.services.financial_cache.warm_financial",
        lambda: {"ok": True},
    )
    monkeypatch.setattr(
        "apps.portal.services.executive_operations.warm_operations",
        lambda: {"ok": True},
    )
    monkeypatch.setattr(
        "apps.portal.services.executive_commercial.warm_commercial_summary",
        lambda: {"ok": True},
    )
    result = warm_cache.warm_portal()
    assert calls == ["", "eva4", "eva3", "inversion", "capacidad"]
    assert result == {"ok": False, "error": "inversion, facturabilidad"}


def test_secondary_pages_are_warmed_and_one_failure_does_not_stop_the_other(
    monkeypatch,
):
    visited = []

    def kpis(request):
        visited.append("kpis")
        assert request.user.is_authenticated
        raise DashboardError("Sin Azure")

    def closed(request):
        visited.append("eva1_cerrados")
        return HttpResponse(status=200)

    monkeypatch.setattr(views, "kpi_context", kpis)
    monkeypatch.setattr(views, "eva1_cerrados", closed)

    result = warm_cache.warm_secondary_pages()

    assert visited == ["kpis", "eva1_cerrados"]
    assert result["ok"] is False
    assert result["error"].startswith("kpis: ")


def test_secondary_pages_report_a_non_200_response(monkeypatch):
    monkeypatch.setattr(views, "kpi_context", lambda request: {})
    monkeypatch.setattr(
        views, "eva1_cerrados", lambda request: HttpResponse(status=401)
    )

    assert warm_cache.warm_secondary_pages() == {
        "ok": False,
        "error": "eva1_cerrados",
    }


def test_summary_cache_skips_calculation_and_manual_refresh_rebuilds(
    monkeypatch,
):
    cache.clear()
    calls = []

    def sources(month):
        calls.append(month)
        return [MonthSources(month=month)]

    monkeypatch.setattr(views, "load_year_sources", sources)
    first = views.operations_summary_data()
    assert views.operations_summary_data() == first
    assert len(calls) == 1
    views.operations_summary_data(refresh=True)
    assert len(calls) == 2
    cache.clear()


def test_partial_summary_preserves_previous_valid_cut(monkeypatch):
    cache.clear()
    key = views._operations_summary_key()
    cache.set(key, "previous-cut")
    monkeypatch.setattr(
        views,
        "load_year_sources",
        lambda month: [MonthSources(month=month, error="Sin conexion")],
    )
    assert views.operations_summary_data(refresh=True).errors
    assert cache.get(key) == "previous-cut"
    assert cache.get(key + ":fresh") is None
    cache.clear()
