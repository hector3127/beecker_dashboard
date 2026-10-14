"""La precarga prepara los componentes de las tres paginas principales."""

from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import timezone

from apps.portal import views
from apps.portal.services.portfolio_loader import PortfolioLoad
from core.management.commands.warm_cache import warm_portal
from tests.portal.builders import make_project


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def request(path, **params):
    return RequestFactory().get(path, params)


def test_executive_components_are_reused_after_precache(monkeypatch):
    load = Mock(
        return_value=PortfolioLoad(
            projects=(make_project(),),
            error="",
            loaded_at=timezone.localtime(),
        )
    )
    monkeypatch.setattr(views, "load_portfolio", load)
    first = views.ejecutiva(request("/"))
    second = views.ejecutiva(request("/"))
    assert first.content == second.content
    load.assert_called_once_with()
    saved = cache.get(
        "portal:executiva:context:v1:" + timezone.localdate().isoformat()
    )
    assert {"decisions", "hours", "top_accounts"} <= saved.keys()


def test_commercial_components_are_reused_but_filters_are_independent(
    monkeypatch,
):
    build = Mock(
        return_value={
            "active": "comercial",
            "error": "",
            "pipeline": {"sections": []},
            "pipeline_details": {},
            "filter_query": "",
        }
    )
    monkeypatch.setattr(
        "apps.portal.services.commercial_view.build_commercial_context", build
    )
    first = views.comercial(request("/comercial/"))
    assert views.comercial(request("/comercial/")).content == first.content
    assert build.call_count == 1
    views.comercial(request("/comercial/", cliente="ACME"))
    assert build.call_count == 2
    assert build.call_args.args[0]["cliente"] == "ACME"


def test_commercial_source_error_is_not_cached_as_a_ready_page(monkeypatch):
    build = Mock(return_value={"error": "No se pudo leer Backlog_Proyectos"})
    monkeypatch.setattr(
        "apps.portal.services.commercial_view.build_commercial_context", build
    )
    for _ in range(2):
        assert (
            b'data-portal-ready="false"'
            in views.comercial(request("/comercial/")).content
        )
    assert build.call_count == 2


def test_full_warmer_visits_all_components_and_reports_page_errors(monkeypatch):
    visited = []

    def operations(req):
        visited.append(req.GET["bloque"] or "base")
        return HttpResponse('<div data-block-error="" data-source-errors="0">')

    def page(name, ready):
        def load(req):
            visited.append(name)
            return HttpResponse(f'<body data-portal-ready="{ready}">')

        return load

    monkeypatch.setattr(views, "operativa_datos", operations)
    monkeypatch.setattr(
        views, "operations_resumen", page("facturabilidad", "true")
    )
    monkeypatch.setattr(views, "ejecutiva", page("ejecutiva", "true"))
    monkeypatch.setattr(views, "comercial", page("comercial", "false"))
    monkeypatch.setattr(
        "apps.portal.services.financial_cache.warm_financial",
        lambda: {"ok": True},
    )
    assert warm_portal() == {"ok": False, "error": "comercial"}
    assert visited == [
        "base",
        "eva3",
        "inversion",
        "capacidad",
        "facturabilidad",
        "ejecutiva",
        "comercial",
    ]
