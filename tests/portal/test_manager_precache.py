"""El precalentamiento incluye el grafico mensual de cada manager."""

from types import SimpleNamespace

import pytest
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory

from apps.portal import views
from core.management.commands.warm_cache import warm_delivery_managers


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def test_warmer_prepares_monthly_history_in_the_keys_read_by_detail(
    monkeypatch,
):
    manager = SimpleNamespace(name="Ana", slug="ana")
    req = RequestFactory().get("/operativa/")
    cache.set(views._operativa_key(req), {"managers": [manager]})
    calls = []

    def load(request, slug):
        assert request.user.is_authenticated
        stage = request.GET["bloque"]
        calls.append((slug, stage))
        payload = {
            "base": {
                "sources": {},
                "manager_name": "Ana",
                "dm_name": "Ana",
                "detail": SimpleNamespace(rows=()),
            },
            "inv": {"investment": {"complete": True}, "risks": {}},
            "horas": {
                "complete": True,
                "monthly": [{"label": "Jun 2026", "total": 1}],
            },
        }[stage]
        cache.set(views._dm_key(slug, stage), payload)
        return HttpResponse(status=200)

    original = views.delivery_manager
    monkeypatch.setattr(views, "delivery_manager", load)
    assert warm_delivery_managers() == {"ok": True, "error": ""}
    assert calls == [("ana", "base"), ("ana", "inv"), ("ana", "horas")]
    req = RequestFactory().get("/operativa/delivery-manager/ana/")
    html = original(req, "ana").content.decode()
    assert "Cargando consumo desde Clockify" not in html
    assert 'id="hours-monthly-data"' in html
    # El corte de la grafica sigue disponible aunque venza primero la base.
    cache.delete(views._dm_key("ana", "base"))
    html = original(req, "ana").content.decode()
    assert 'id="hours-monthly-data"' in html


def test_incomplete_monthly_history_is_reported_as_partial(monkeypatch):
    req = RequestFactory().get("/operativa/")
    manager = SimpleNamespace(name="Ana", slug="ana")
    cache.set(views._operativa_key(req), {"managers": [manager]})

    def load(request, slug):
        stage = request.GET["bloque"]
        payload = (
            {"complete": False}
            if stage == "horas"
            else {"investment": {"complete": True}}
        )
        cache.set(views._dm_key(slug, stage), payload)
        return HttpResponse(status=200)

    monkeypatch.setattr(views, "delivery_manager", load)
    result = warm_delivery_managers()
    assert result == {
        "ok": False,
        "error": "Ana: consumo mensual incompleto",
    }
