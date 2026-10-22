"""El precalentamiento incluye el grafico mensual de cada manager."""

from types import SimpleNamespace

import pytest
from django.core.cache import cache

from apps.portal import views
from core.management.commands.warm_cache import warm_delivery_managers

pytestmark = pytest.mark.django_db

DETAIL = SimpleNamespace(
    name="Ana",
    initials="A",
    total=0,
    in_progress=0,
    paused=0,
    health=SimpleNamespace(on_time=0, at_risk=0, critical=0),
    rows=(),
)


@pytest.fixture(autouse=True)
def clean_cache():
    cache.clear()
    yield
    cache.clear()


def payloads(scope):
    return {
        "base": {
            "sources": {},
            "manager_name": "Ana",
            "dm_name": "Ana",
            "detail": DETAIL,
        },
        "inv": {"investment": {"complete": True, "totals": {}}, "risks": {}},
        "horas": {
            "complete": True,
            "monthly": [{"label": "Jun 2026", "total": 1}],
        },
    }


def warm_with(monkeypatch, overrides=None):
    req = SimpleNamespace(GET={})
    manager = SimpleNamespace(name="Ana", slug="ana")
    monkeypatch.setattr(
        views, "_operativa_snapshot", lambda r: {"managers": [manager]}
    )
    calls = []

    def load(slug, stage, scope):
        calls.append((slug, stage))
        data = {**payloads(scope), **(overrides or {})}
        cache.set(views._dm_key(slug, stage, scope), data[stage])

    monkeypatch.setattr(views, "dm_state", load)
    return calls, req


def test_warmer_prepares_monthly_history_in_the_keys_read_by_the_api(
    monkeypatch, client
):
    calls, _ = warm_with(monkeypatch)

    assert warm_delivery_managers() == {"ok": True, "error": ""}
    assert calls == [("ana", "base"), ("ana", "inv"), ("ana", "horas")]
    monkeypatch.undo()  # el detalle debe salir solo de lo guardado
    monkeypatch.setattr(views, "_dm_base", lambda *a: pytest.fail("fuentes"))

    body = client.get(
        "/api/v1/screens/delivery-managers/ana/", {"bloque": "horas"}
    ).json()

    assert body["data"]["hours"]["state"] == "ready"
    assert body["data"]["hours"]["months"][0]["label"] == "Jun 2026"


def test_the_base_is_served_from_cache_without_reading_sources(
    monkeypatch, client
):
    cache.set(views._dm_key("ana", "base"), payloads(None)["base"])
    monkeypatch.setattr(views, "_dm_base", lambda *a: pytest.fail("fuentes"))

    response = client.get("/api/v1/screens/delivery-managers/ana/")

    assert response.status_code == 200
    assert response.json()["data"]["hours"]["state"] == "pending"


def test_incomplete_monthly_history_is_reported_as_partial(monkeypatch):
    warm_with(monkeypatch, {"horas": {"complete": False}})

    assert warm_delivery_managers() == {
        "ok": False,
        "error": "Ana: consumo mensual incompleto",
    }
