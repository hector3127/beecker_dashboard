"""Precalentamiento y reutilizacion de cortes completos del portal."""

from io import StringIO
from types import SimpleNamespace

from django.core.cache import cache
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory

from apps.portal import views
from apps.portal.services.facturability_loader import MonthSources
from core.management.commands import warm_cache


def test_portal_only_does_not_clear_cache_or_load_legacy(monkeypatch):
    cache.set("keep-this-cut", "saved")
    monkeypatch.setattr(warm_cache, "warm_portal", lambda: {"ok": True})
    monkeypatch.setattr(
        warm_cache, "warm_sheets",
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
        return HttpResponse(
            f'<div data-block-error="{error}" data-source-errors="0"></div>'
        )

    monkeypatch.setattr(views, "operativa_datos", load)
    monkeypatch.setattr(
        views, "operations_resumen",
        lambda request: HttpResponse('<div data-partial="true"></div>'),
    )
    monkeypatch.setattr(
        views, "comercial",
        lambda request: HttpResponse('<body data-portal-ready="true">'),
    )
    monkeypatch.setattr(
        views, "ejecutiva",
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
    result = warm_cache.warm_portal()
    assert calls == ["", "eva4", "eva3", "inversion", "capacidad"]
    assert result == {"ok": False, "error": "inversion, facturabilidad"}


def test_summary_cache_skips_calculation_and_manual_refresh_rebuilds(
    monkeypatch,
):
    cache.clear()
    calls = []

    def sources(month):
        calls.append(month)
        return [MonthSources(month=month)]

    monkeypatch.setattr(views, "load_year_sources", sources)
    factory = RequestFactory()
    request = factory.get("/operations/resumen/")
    request.user = SimpleNamespace(is_authenticated=True)
    first = views.operations_resumen(request)
    assert views.operations_resumen(request).content == first.content
    assert len(calls) == 1
    request.GET = request.GET.copy()
    request.GET["actualizar"] = "1"
    views.operations_resumen(request)
    assert len(calls) == 2
    cache.clear()


def test_partial_summary_preserves_previous_valid_cut(monkeypatch):
    cache.clear()
    key = views._operations_summary_key()
    cache.set(key, "previous-cut")
    monkeypatch.setattr(
        views, "load_year_sources",
        lambda month: [MonthSources(month=month, error="Sin conexion")],
    )
    request = RequestFactory().get("/operations/resumen/")
    request.user = SimpleNamespace(is_authenticated=True)
    assert b'data-partial="true"' in views.operations_resumen(request).content
    assert cache.get(key) == "previous-cut"
    assert cache.get(key + ":fresh") is None
    cache.clear()
