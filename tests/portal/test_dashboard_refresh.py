"""Regression checks for truthful source states and snapshot refreshes."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import RequestFactory
from django.utils import timezone

from apps.portal import views
from apps.portal.services import portfolio_loader
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.eva_loader import Eva1Load, Eva2Load
from tests.portal.builders import make_project


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def request(path="/operativa/datos/", **params):
    result = RequestFactory().get(path, {"actualizar": "1", **params})
    result.user = User(username="dashboard-test")
    return result


def stub_eva(monkeypatch, error=""):
    monkeypatch.setattr(
        views, "load_eva2",
        lambda **kwargs: Eva2Load(build_eva2_view([]), error),
    )
    monkeypatch.setattr(
        views, "load_eva1",
        lambda **kwargs: Eva1Load(build_eva1_view([]), error),
    )


def test_failed_refresh_reports_failure_and_keeps_snapshot(monkeypatch):
    stub_eva(monkeypatch)
    refresh = request()
    views.operativa_datos(request(bloque="eva3"))
    key = views._operativa_key(refresh)
    saved = cache.get(key)
    stub_eva(monkeypatch, "Azure y Sheets no responden.")

    html = views.operativa_datos(refresh).content.decode()

    assert 'data-source-errors="2"' in html
    assert "No se pudo renovar el corte guardado." in html
    assert "Azure y Sheets no responden." in html
    assert cache.get(key) == saved


def test_failed_first_refresh_does_not_cache_fake_zero_totals(monkeypatch):
    stub_eva(monkeypatch, "Sin conexión.")
    refresh = request()

    html = views.operativa_datos(refresh).content.decode()

    assert cache.get(views._operativa_key(refresh)) is None
    assert 'data-source-errors="2"' in html
    assert "Información parcial del portafolio." in html
    assert 'data-loaded-at=' in html


def test_failed_eva3_enrichment_keeps_previous_portfolio(monkeypatch):
    stub_eva(monkeypatch)
    refresh = request()
    views.operativa_datos(request(bloque="eva3"))
    saved = cache.get(views._operativa_key(refresh))
    stub_eva(monkeypatch, "Clockify no responde.")

    html = views.operativa_datos(
        request(bloque="eva3"),
    ).content.decode()

    assert 'data-block-error="Clockify no responde."' in html
    assert cache.get(views._operativa_key(refresh)) == saved


def test_eva3_updates_totals_and_health_in_the_same_response(monkeypatch):
    stub_eva(monkeypatch)
    refresh = request()
    views.operativa_datos(refresh)
    projects = [make_project(), make_project(project_id="P-2")]
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.eva_projects",
        lambda *args: projects,
    )

    html = views.operativa_datos(request(bloque="eva3")).content.decode()
    saved = cache.get(views._operativa_key(refresh))

    assert saved["summary"].in_progress == 2
    assert saved["health"].on_time == 2
    assert saved["managers"][0].in_progress == 2
    for section in (
        "ops-metric-progress", "ops-metric-paused", "ops-metric-on-time",
        "ops-health", "ops-managers", "ops-evas",
    ):
        assert html.count(f'id="{section}"') == 1


@pytest.mark.parametrize(
    ("block", "function", "payload", "message"),
    [
        (
            "inversion", "tagged_investment",
            {"complete": False, "error": "Sin Clockify."}, "Sin Clockify.",
        ),
        (
            "capacidad", "legacy_capacity", {"pending": 2},
            "Capacidad con asignaciones pendientes.",
        ),
    ],
)
def test_failed_secondary_block_preserves_saved_cut(
    monkeypatch, block, function, payload, message,
):
    stub_eva(monkeypatch)
    refresh = request()
    views.operativa_datos(request(bloque="eva3"))
    key = views._operativa_key(refresh)
    saved = cache.get(key)
    monkeypatch.setattr(
        f"apps.portal.services.operational_sources.{function}",
        lambda *args: payload,
    )

    html = views.operativa_datos(request(bloque=block)).content.decode()

    assert f'data-block-error="{message}"' in html
    assert cache.get(key) == saved


def test_initial_shell_has_real_filter_context_and_no_example_claim():
    html = views.operativa(
        request("/operativa/", servicio="T&M", cuenta="ACME"),
    ).content.decode()

    assert 'value="T&amp;M" selected' in html
    assert 'value="ACME" selected' in html
    assert "Filtros y alcance de los datos" not in html
    assert "Cargando datos" in html
    assert "Cifras de ejemplo" not in html
    assert 'aria-current="page"' in html
    assert 'href="#main-content"' in html


def test_cache_reuse_preserves_time_of_calculation(monkeypatch):
    stamp = timezone.localtime()
    calls = []
    monkeypatch.setattr(
        portfolio_loader, "build_sheet_repository", lambda: object(),
    )
    monkeypatch.setattr(
        portfolio_loader, "build_time_entry_provider", lambda repo: object(),
    )

    def build(*args):
        calls.append(1)
        return (make_project(),)

    monkeypatch.setattr(portfolio_loader, "build_project_views", build)
    monkeypatch.setattr(portfolio_loader.timezone, "localtime", lambda: stamp)
    first = portfolio_loader.load_portfolio()
    monkeypatch.setattr(
        portfolio_loader.timezone, "localtime",
        lambda: stamp + timedelta(minutes=2),
    )
    second = portfolio_loader.load_portfolio()

    assert first.loaded_at == second.loaded_at == stamp
    assert len(calls) == 1
