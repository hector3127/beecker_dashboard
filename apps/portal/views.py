"""Pantallas Ejecutiva, Operativa y Comercial."""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.portal.services.decisions import build_decisions
from apps.portal.services.eva_loader import load_eva1, load_eva2
from apps.portal.services.filters import (
    filter_projects,
    list_clients,
    list_services,
)
from apps.portal.services.manager_detail import (
    build_manager_detail,
    find_manager,
    summarize_suspended,
)
from apps.portal.services.periods import current_quarter
from apps.portal.services.portfolio_loader import (
    PortfolioLoad,
    load_portfolio,
)
from apps.portal.services.portfolio_summary import (
    build_donut_segments,
    summarize_delivery_managers,
    summarize_hours,
    summarize_portfolio,
)

"""BKD.120.010 - Vistas del portal
Reemplazan la portada anterior. Leen datos reales cuando existen y
marcan como "Ejemplo" lo que todavia no tiene fuente conectada.
"""


def _needs_login(request: HttpRequest) -> bool:
    """Indica si hay que mandar al usuario a iniciar sesion."""
    return bool(
        settings.PORTAL_LOGIN_REQUIRED and not request.user.is_authenticated,
    )


def _base_context(load: PortfolioLoad) -> dict[str, object]:
    """Datos que comparten las tres pantallas."""
    return {
        "loaded_at": load.loaded_at,
        "error": load.error,
        "period": current_quarter(load.loaded_at.date()),
    }


@require_GET
def ejecutiva(request: HttpRequest) -> HttpResponse:
    """
    Muestra la pantalla Ejecutiva.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina con Financiera, Operations, Comercial y las decisiones.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_portfolio()
    context = _base_context(load)
    context.update(
        {
            "active": "ejecutiva",
            "decisions": build_decisions(load.projects),
            "hours": summarize_hours(load.projects),
            "has_projects": bool(load.projects),
        },
    )

    return render(request, "portal/ejecutiva.html", context)


@require_GET
def operativa(request: HttpRequest) -> HttpResponse:
    """
    Muestra la pantalla Operativa con filtros de Servicio y Cuenta.

    Args:
        request: Peticion HTTP; acepta ?servicio= y ?cuenta=.

    Returns:
        La pagina con los indicadores y los Delivery Managers.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_portfolio()
    selected_service = request.GET.get("servicio", "").strip()
    selected_client = request.GET.get("cuenta", "").strip()
    projects = filter_projects(
        load.projects,
        selected_service,
        selected_client,
    )
    summary = summarize_portfolio(projects)
    context = _base_context(load)
    context.update(
        {
            "active": "operativa",
            "summary": summary,
            "health": summary.health,
            "donut": build_donut_segments(summary.health),
            "managers": summarize_delivery_managers(projects),
            "services": list_services(load.projects),
            "clients": list_clients(load.projects),
            "selected_service": selected_service,
            "selected_client": selected_client,
            "has_projects": bool(projects),
        },
    )

    return render(request, "portal/operativa.html", context)


@require_GET
def comercial(request: HttpRequest) -> HttpResponse:
    """
    Muestra la pantalla Comercial (cifras de ejemplo por ahora).

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina Comercial del diseno aprobado.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    context: dict[str, object] = {
        "active": "comercial",
        "loaded_at": None,
    }

    return render(request, "portal/comercial.html", context)


@require_GET
def delivery_manager(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Muestra el detalle de un Delivery Manager con todos sus proyectos.

    Args:
        request: Peticion HTTP.
        slug: Nombre del Delivery Manager escrito para la URL.

    Returns:
        La pagina del Delivery Manager.

    Raises:
        Http404: Cuando ningun proyecto tiene a ese Delivery Manager.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_portfolio()
    found = find_manager(load.projects, slug)

    if found is None:
        if load.error:
            return redirect("portal:operativa")

        raise Http404("No existe ese Delivery Manager.")

    context = _base_context(load)
    context.update(
        {
            "active": "operativa",
            "detail": build_manager_detail(*found),
        },
    )

    return render(request, "portal/delivery_manager.html", context)


@require_GET
def suspendidos(request: HttpRequest) -> HttpResponse:
    """
    Muestra los proyectos suspendidos de todo el portafolio.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina de suspendidos.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_portfolio()
    context = _base_context(load)
    context.update(
        {
            "active": "operativa",
            "suspended": summarize_suspended(load.projects),
        },
    )

    return render(request, "portal/suspendidos.html", context)


@require_GET
def eva1(request: HttpRequest) -> HttpResponse:
    """
    Muestra EVA 1: proyectos AER y T&M por Delivery Manager.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina EVA 1 con los datos de la hoja MPB.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_eva1()

    return render(
        request,
        "portal/eva1.html",
        {
            "active": "operativa",
            "loaded_at": timezone.localtime(),
            "error": load.error,
            "eva": load.view,
        },
    )


@require_GET
def eva2(request: HttpRequest) -> HttpResponse:
    """
    Muestra EVA 2: proyectos IXB y RaaS con su avance en Azure DevOps.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina EVA 2 con el resumen IXB/RaaS.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_eva2()

    return render(
        request,
        "portal/eva2.html",
        {
            "active": "operativa",
            "loaded_at": timezone.localtime(),
            "error": load.error,
            "eva": load.view,
        },
    )
