"""Pantallas Ejecutiva, Operativa y Comercial."""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.portal.schemas import CapacityFilters
from apps.portal.services.account import build_account_detail, find_account
from apps.portal.services.account_ranking import rank_accounts
from apps.portal.services.capacity import (
    build_capacity_csv,
    build_capacity_view,
    normalize_month,
    parse_workday_hours,
)
from apps.portal.services.capacity_loader import load_capacity
from apps.portal.services.decisions import build_decisions
from apps.portal.services.eva_loader import (
    build_eva1_card,
    load_eva1,
    load_eva2,
    peek_eva2_card,
)
from apps.portal.services.filters import (
    filter_projects,
    list_clients,
    list_services,
)
from apps.portal.services.kpis_dm import build_kpi_view
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
    select_in_progress,
    summarize_delivery_managers,
    summarize_hours,
    summarize_portfolio,
)
from apps.portal.services.project_groups import (
    build_project_groups,
    select_on_time,
)
from apps.portal.services.project_loader import load_project_dashboard
from apps.portal.services.project_page import build_project_page

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
            "top_accounts": rank_accounts(load.projects),
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
            "eva1_card": build_eva1_card(load_eva1()),
            "eva2_card": peek_eva2_card(),
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
def cuenta(request: HttpRequest, slug: str) -> HttpResponse:
    """
    Muestra una cuenta (cliente) con todos sus proyectos.

    Args:
        request: Peticion HTTP.
        slug: Nombre de la cuenta escrito para la URL.

    Returns:
        La pagina de la cuenta.

    Raises:
        Http404: Cuando ningun proyecto es de esa cuenta.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_portfolio()
    found = find_account(load.projects, slug)

    if found is None:
        if load.error:
            return redirect("portal:operativa")

        raise Http404("No existe esa cuenta.")

    context = _base_context(load)
    context.update(
        {
            "active": "operativa",
            "account": build_account_detail(*found),
        },
    )

    return render(request, "portal/cuenta.html", context)


@require_GET
def proyecto(request: HttpRequest, project_id: str) -> HttpResponse:
    """
    Muestra el detalle de un proyecto.

    Args:
        request: Peticion HTTP.
        project_id: ID del proyecto en la hoja Proyectos.

    Returns:
        La pagina del proyecto.

    Raises:
        Http404: Cuando el portafolio no tiene ese proyecto.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_portfolio()
    project = next(
        (item for item in load.projects if item.project_id == project_id),
        None,
    )

    if project is None:
        if load.error:
            return redirect("portal:operativa")

        raise Http404("No existe ese proyecto.")

    detail = load_project_dashboard(project_id)
    context = _base_context(load)
    context.update(
        {
            "active": "operativa",
            "page": build_project_page(
                project,
                detail.data,
                timezone.localdate(),
            ),
            "detail_error": detail.error,
        },
    )

    return render(request, "portal/proyecto.html", context)


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


def _read_capacity_filters(request: HttpRequest) -> CapacityFilters:
    """Lee mes, jornada y filtros de la direccion web."""
    return CapacityFilters(
        month=normalize_month(
            request.GET.get("mes", ""),
            timezone.localdate(),
        ),
        workday_hours=parse_workday_hours(request.GET.get("jornada", "")),
        search=request.GET.get("buscar", "").strip(),
        technology=request.GET.get("tecnologia", ""),
        concept=request.GET.get("concepto", ""),
    )


@require_GET
def capacidad_instalada(request: HttpRequest) -> HttpResponse:
    """
    Muestra las asignaciones y la capacidad base de un mes.

    Args:
        request: Peticion HTTP con mes, jornada y filtros opcionales.

    Returns:
        La pagina de Capacidad instalada.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    filters = _read_capacity_filters(request)
    load = load_capacity(
        filters.month, refresh=bool(request.GET.get("actualizar"))
    )

    return render(
        request,
        "portal/capacidad_instalada.html",
        {
            "active": "operativa",
            "loaded_at": timezone.localtime(),
            "error": load.error,
            "capacity": build_capacity_view(load.data, filters),
            "filters": filters,
        },
    )


@require_GET
def capacidad_instalada_csv(request: HttpRequest) -> HttpResponse:
    """
    Descarga en CSV las asignaciones que muestra la pantalla.

    Args:
        request: Peticion HTTP con los mismos filtros de la pantalla.

    Returns:
        El archivo CSV (con BOM para abrirlo bien en Excel).
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    filters = _read_capacity_filters(request)
    load = load_capacity(filters.month)
    view = build_capacity_view(load.data, filters)
    response = HttpResponse(
        "\ufeff" + build_capacity_csv(view.rows),
        content_type="text/csv; charset=utf-8",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="capacidad-instalada-{filters.month}.csv"'
    )

    return response


def _render_groups(request: HttpRequest, only_on_time: bool) -> HttpResponse:
    """Pantalla de proyectos agrupados por Delivery Manager."""
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_portfolio()
    context = _base_context(load)
    context.update(
        {
            "active": "operativa",
            "only_on_time": only_on_time,
            "managers": summarize_delivery_managers(load.projects),
            "groups": build_project_groups(load.projects, only_on_time),
            "listed": len(
                select_on_time(load.projects)
                if only_on_time
                else select_in_progress(load.projects),
            ),
        },
    )

    return render(request, "portal/en_ejecucion.html", context)


@require_GET
def en_ejecucion(request: HttpRequest) -> HttpResponse:
    """
    Muestra los proyectos en ejecucion agrupados por Delivery Manager.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina de proyectos en ejecucion.
    """
    return _render_groups(request, only_on_time=False)


@require_GET
def en_tiempo(request: HttpRequest) -> HttpResponse:
    """
    Muestra los proyectos que van en tiempo agrupados por Delivery Manager.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina de proyectos en tiempo.
    """
    return _render_groups(request, only_on_time=True)


@require_GET
def kpis_delivery_managers(request: HttpRequest) -> HttpResponse:
    """
    Muestra TP, T y C de cada Delivery Manager con el corte actual.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina de KPIs de Delivery Managers.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_portfolio()
    context = _base_context(load)
    context.update(
        {
            "active": "operativa",
            "kpis": build_kpi_view(load.projects),
        },
    )

    return render(request, "portal/kpis_dm.html", context)
