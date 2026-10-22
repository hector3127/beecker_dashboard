"""Opening Operativa must not wait for external data sources."""

from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory
from django.utils import timezone

from apps.portal import views
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.eva_loader import Eva1Load, Eva2Load
from apps.portal.services.operations_summary import (
    build_operations_summary,
)


def test_open_is_cache_first_and_refresh_saves_snapshot():
    cache.clear()
    request = RequestFactory().get("/operativa/")
    request.user = SimpleNamespace(is_authenticated=True)
    with (
        patch.object(
            views,
            "load_portfolio",
            side_effect=AssertionError("Blocking portfolio call"),
        ),
        patch.object(
            views,
            "load_eva2",
            side_effect=AssertionError("Blocking Azure call"),
        ),
    ):
        assert views.operativa_context(request)["loading"] is True
    refresh = RequestFactory().get("/operativa/datos/", {"bloque": "eva3"})
    refresh.user = request.user
    with (
        patch.object(
            views, "load_eva2", return_value=Eva2Load(build_eva2_view([]), "")
        ),
        patch.object(
            views, "load_eva1", return_value=Eva1Load(build_eva1_view([]), "")
        ),
    ):
        views.operativa_block_context(refresh)
    assert cache.get(views._operativa_key(request))
    with patch.object(
        views,
        "load_eva2",
        side_effect=AssertionError("Cached navigation contacted Azure"),
    ):
        assert views.operativa_context(request)["loading"] is False


def test_only_complete_fresh_blocks_skip_automatic_refresh():
    cache.clear()
    request = RequestFactory().get("/operativa/", {"cuenta": "ACME"})
    request.user = SimpleNamespace(is_authenticated=True)
    cache.set(
        views._operativa_key(request), {"loaded_at": timezone.localtime()}
    )
    for block in views._OPS_BLOCKS:
        cache.set(views._operativa_fresh_key(request, block), True)
    assert views.operativa_context(request)["async_operativa"] is False

    cache.delete(views._operativa_fresh_key(request, "capacidad"))
    assert views.operativa_context(request)["async_operativa"] is True
    other = RequestFactory().get("/operativa/", {"cuenta": "OTRA"})
    other.user = request.user
    assert views.operativa_context(other)["async_operativa"] is True
    cache.clear()


def test_summary_cut_is_embedded_and_its_freshness_is_independent():
    cache.clear()
    request = RequestFactory().get("/operativa/")
    request.user = SimpleNamespace(is_authenticated=True)
    key = views._operations_summary_key()
    saved = build_operations_summary([])
    cache.set(key, saved)
    cache.set(key + ":fresh", True)
    context = views.operativa_context(request)
    assert context["operations_summary"] == saved
    assert context["summary_fresh"] is True
    cache.delete(key + ":fresh")
    context = views.operativa_context(request)
    assert context["operations_summary"] == saved
    assert context["summary_fresh"] is False
    cache.clear()


def test_manager_base_prefetch_reuses_cached_computation(monkeypatch):
    cache.clear()
    request = RequestFactory().get("/operativa/dm/ana/", {"bloque": "base"})
    request.user = SimpleNamespace(is_authenticated=True)
    cache.set(
        views._dm_key("ana", "base"),
        {
            "manager_name": "Ana",
            "sources": {},
            "detail": SimpleNamespace(rows=()),
            "dm_name": "Ana",
        },
    )

    def unexpected_read(slug):
        raise AssertionError("Cached manager contacted integrations")

    monkeypatch.setattr(views, "_dm_base", unexpected_read)
    assert views.delivery_manager(request, "ana").status_code == 200
    cache.clear()
