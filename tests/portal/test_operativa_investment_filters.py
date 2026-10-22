"""Investment cards follow the same population as the filtered portfolio."""

from types import SimpleNamespace

import pytest
from django.core.cache import cache
from django.test import RequestFactory

from apps.portal import views
from apps.portal.services.filters import filter_projects
from apps.portal.services.portfolio_summary import summarize_delivery_managers
from tests.portal.builders import make_project


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def population(service):
    return summarize_delivery_managers(
        filter_projects(
            [
                make_project(project_id="AER.1", service="AER"),
                make_project(project_id="IXB.1", service="IXB"),
            ],
            service,
            "",
        )
    )


def investment():
    return {
        "complete": True,
        "totals": {"operational": 100, "commercial": 12},
        "by_project": {
            "AER.1": {"operational": 30, "commercial": 2},
            "IXB.1": {"operational": 70, "commercial": 10},
        },
    }


@pytest.mark.parametrize(
    "service,expected",
    [
        ("AER", (30, 2)),
        ("IXB", (70, 10)),
        ("", (100, 12)),
        ("Sin proyectos", (0, 0)),
    ],
)
def test_cached_snapshot_scopes_both_investment_cards(service, expected):
    request = RequestFactory().get("/operativa/", {"servicio": service})
    original = investment()
    key = views._operativa_key(request)
    cache.set(key, {"managers": population(service), "investment": original})
    # Independent updates can supply a global investment cut after the base.
    cache.set(key + ":block:inversion", {"investment": original})
    saved = views._operativa_snapshot(request)
    totals = saved["investment"]["totals"]
    assert (totals["operational"], totals["commercial"]) == expected
    assert original["totals"]["operational"] == 100


def test_refresh_keeps_global_cache_and_scopes_filtered_block(monkeypatch):
    request = RequestFactory().get(
        "/operativa/datos/", {"servicio": "AER", "bloque": "inversion"}
    )
    request.user = SimpleNamespace(is_authenticated=True)
    key = views._operativa_key(request)
    cache.set(key, {"managers": population("AER"), "investment": {}})
    monkeypatch.setattr(views, "load_eva1", lambda **kwargs: None)
    monkeypatch.setattr(views, "load_eva2", lambda **kwargs: None)
    monkeypatch.setattr(
        views, "_operativa_investment", lambda *args: investment()
    )
    assert views.operativa_datos(request).status_code == 200
    assert cache.get("portal:ops:investment:v3")["totals"]["operational"] == 100
    assert views._operativa_snapshot(request)["investment"]["totals"] == {
        "operational": 30,
        "commercial": 2,
    }


def test_partial_investment_remains_pending():
    request = RequestFactory().get("/operativa/", {"servicio": "AER"})
    partial = {"complete": False, "error": "Datos pendientes"}
    context = {"managers": population("AER"), "investment": partial}
    views._scope_operativa_investment(request, context)
    assert context["investment"] == partial
