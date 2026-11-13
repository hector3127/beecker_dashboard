"""El refresco con caché conserva conteos y motivos de salud juntos."""

from types import SimpleNamespace as N
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory

from apps.portal import views
from apps.portal.schemas import ProjectView
from apps.portal.services.portfolio_summary import health_alerts


def test_cached_refresh_saves_health_detail_with_summary():
    cache.clear()
    request = RequestFactory().get("/operativa/datos/", {"bloque": "eva3"})
    request.user = N(is_authenticated=True)
    project = ProjectView(
        "AER.TEST.001",
        "Prueba",
        "Cliente",
        "DM",
        "AER",
        "Activo",
        "En Riesgo",
        "",
        95,
        10,
        100,
        95,
        5,
        "Solo quedan 5 h.",
    )
    cache.set(views._operativa_key(request), {"loading": False})
    source = N(error="", view=N(total_projects=1, time_cost=None, projects=[]))
    with (
        patch.object(views, "build_eva1_card", return_value=N()),
        patch.object(views, "load_eva1", return_value=source),
        patch.object(views, "load_eva2", return_value=source),
        patch(
            "apps.portal.services.operational_sources.eva_projects",
            return_value=[project],
        ),
        patch.object(views, "_scope_operativa_investment"),
        patch.object(views, "_operativa_block_error", return_value=""),
    ):
        result = views.operativa_block_context(request)
    assert result["summary"].health.at_risk == 1
    assert result["health_alerts"] == health_alerts([project])
    saved = views._operativa_snapshot(request)
    assert saved["health_alerts"][0]["project_id"] == project.project_id
    assert saved["summary"].health.at_risk == len(saved["health_alerts"])
    cache.clear()
