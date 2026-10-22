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
from apps.portal.services.operativa_status import block_error
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
        views,
        "load_eva2",
        lambda **kwargs: Eva2Load(build_eva2_view([]), error),
    )
    monkeypatch.setattr(
        views,
        "load_eva1",
        lambda **kwargs: Eva1Load(build_eva1_view([]), error),
    )


def test_failed_refresh_reports_failure_and_keeps_snapshot(monkeypatch):
    stub_eva(monkeypatch)
    refresh = request()
    views.operativa_block_context(request(bloque="eva3"))
    key = views._operativa_key(refresh)
    saved = cache.get(key)
    stub_eva(monkeypatch, "Azure y Sheets no responden.")

    context = views.operativa_block_context(refresh)

    assert context["source_errors"] == ["Azure y Sheets no responden."] * 2
    assert context["stale"] is True
    assert cache.get(key) == saved


def test_failed_first_refresh_does_not_cache_fake_zero_totals(monkeypatch):
    stub_eva(monkeypatch, "Sin conexión.")
    refresh = request()

    context = views.operativa_block_context(refresh)

    assert cache.get(views._operativa_key(refresh)) is None
    assert context["source_errors"] == ["Sin conexión."] * 2
    assert not context.get("stale")
    assert context["loaded_at"]


def test_failed_eva3_enrichment_keeps_previous_portfolio(monkeypatch):
    stub_eva(monkeypatch)
    refresh = request()
    views.operativa_block_context(request(bloque="eva3"))
    saved = cache.get(views._operativa_key(refresh))
    stub_eva(monkeypatch, "Clockify no responde.")

    context = views.operativa_block_context(request(bloque="eva3"))

    assert block_error(context) == "Clockify no responde."
    assert cache.get(views._operativa_key(refresh)) == saved


def test_eva3_updates_totals_and_health_in_the_same_response(monkeypatch):
    stub_eva(monkeypatch)
    refresh = request()
    views.operativa_block_context(refresh)
    projects = [make_project(), make_project(project_id="P-2")]
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.eva_projects",
        lambda *args: projects,
    )

    context = views.operativa_block_context(request(bloque="eva3"))
    saved = cache.get(views._operativa_key(refresh))

    assert saved["summary"].in_progress == 2
    assert saved["health"].on_time == 2
    assert saved["managers"][0].in_progress == 2
    # Todo lo que la pantalla repinta llega en la misma respuesta.
    for key in (
        "summary",
        "health",
        "donut",
        "managers",
        "eva1_card",
        "eva3_card",
        "consumption_pending",
    ):
        assert key in context
    assert context["consumption_pending"] is False


@pytest.mark.parametrize(
    ("block", "function", "payload", "message"),
    [
        (
            "inversion",
            "tagged_investment",
            {"complete": False, "error": "Sin Clockify."},
            "Sin Clockify.",
        ),
        (
            "capacidad",
            "legacy_capacity",
            {"pending": 2},
            "Capacidad con asignaciones pendientes.",
        ),
    ],
)
def test_failed_secondary_block_preserves_saved_cut(
    monkeypatch,
    block,
    function,
    payload,
    message,
):
    stub_eva(monkeypatch)
    refresh = request()
    views.operativa_block_context(request(bloque="eva3"))
    key = views._operativa_key(refresh)
    saved = cache.get(key)
    monkeypatch.setattr(
        f"apps.portal.services.operational_sources.{function}",
        lambda *args: payload,
    )

    context = views.operativa_block_context(request(bloque=block))

    assert block_error(context) == message
    assert cache.get(key) == saved


def test_initial_cut_has_real_filter_context_and_no_example_claim():
    context = views.operativa_context(
        request("/operativa/", servicio="T&M", cuenta="ACME"),
    )

    assert context["selected_service"] == "T&M"
    assert context["selected_client"] == "ACME"
    assert context["loading"] is True
    assert context["consumption_pending"] is True


def test_cache_reuse_preserves_time_of_calculation(monkeypatch):
    stamp = timezone.localtime()
    calls = []
    monkeypatch.setattr(
        portfolio_loader,
        "build_sheet_repository",
        lambda: object(),
    )
    monkeypatch.setattr(
        portfolio_loader,
        "build_time_entry_provider",
        lambda repo: object(),
    )

    def build(*args):
        calls.append(1)
        return (make_project(),)

    monkeypatch.setattr(portfolio_loader, "build_project_views", build)
    monkeypatch.setattr(portfolio_loader.timezone, "localtime", lambda: stamp)
    first = portfolio_loader.load_portfolio()
    monkeypatch.setattr(
        portfolio_loader.timezone,
        "localtime",
        lambda: stamp + timedelta(minutes=2),
    )
    second = portfolio_loader.load_portfolio()

    assert first.loaded_at == second.loaded_at == stamp
    assert len(calls) == 1
