"""Opening Operativa must not wait for external data sources."""

from types import SimpleNamespace
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory

from apps.portal import views
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.eva_loader import Eva1Load, Eva2Load


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
        response = views.operativa(request)
        assert response.status_code == 200 and b"Calculando" in response.content
    refresh = RequestFactory().get("/operativa/datos/")
    refresh.user = request.user
    with (
        patch.object(
            views, "load_eva2", return_value=Eva2Load(build_eva2_view([]), "")
        ),
        patch.object(
            views, "load_eva1", return_value=Eva1Load(build_eva1_view([]), "")
        ),
    ):
        assert views.operativa_datos(refresh).status_code == 200
    assert cache.get(views._operativa_key(request))
    with patch.object(
        views,
        "load_eva2",
        side_effect=AssertionError("Cached navigation contacted Azure"),
    ):
        assert views.operativa(request).status_code == 200
