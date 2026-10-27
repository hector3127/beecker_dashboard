"""Detalle de proyecto anterior, solo para comparar en las pruebas.

La aplicacion ya no lo sirve: este modulo lo expone con `?vista=anterior`
cuando las pruebas activan la referencia (tests/e2e/conftest.py).
"""

from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from apps.access.checks import require_capability
from apps.portal import pages, views
from apps.portal.services.return_navigation import return_context


@require_GET
@ensure_csrf_cookie
@require_capability("view_operations")
def previous_detail(request: HttpRequest, project_id: str) -> HttpResponse:
    """Todas las secciones del proyecto con la plantilla y el JS anteriores."""
    if views._needs_login(request):
        return redirect_to_login(request.get_full_path())
    views.ensure_project_visible(request, project_id)
    return render(
        request,
        "portal/proyecto_detalle.html",
        {
            **return_context(request, reverse("portal:operativa"), "Operativa"),
            "active": "operativa",
            "project_id": project_id,
            "project_context": {"id": project_id},
        },
    )


def detail(request: HttpRequest, project_id: str) -> HttpResponse:
    """La ruta real; con ?vista=anterior entrega la referencia."""
    if request.GET.get("vista") == "anterior":
        return previous_detail(request, project_id)
    return pages.project_detail(request, project_id)
