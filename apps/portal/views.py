"""Pantallas Ejecutiva, Operativa y Comercial."""

import hashlib
from typing import Any

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from apps.portal.constants import KPI_HISTORY_CHART_MANAGERS
from apps.portal.schemas import (
    CapacityFilters,
    InvestmentView,
    KpiHistory,
    Period,
    RoleOption,
)
from apps.portal.services.account import find_account
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
)
from apps.portal.services.facturability import (
    build_month_facturability as build_month_facturability,
)
from apps.portal.services.facturability import (
    build_resources as build_resources,
)
from apps.portal.services.facturability import (
    build_specialties as build_specialties,
)
from apps.portal.services.facturability import (
    combine_months,
    default_role_keys,
    display_role,
    list_roles,
    merge_specialties,
    role_key,
    team_averages,
)
from apps.portal.services.facturability_loader import (
    MonthSources,
    load_month_sources,
    peek_month_sources,
)
from apps.portal.services.facturability_loader import (
    load_year_sources as load_year_sources,
)
from apps.portal.services.filters import (
    filter_projects,
    list_clients,
    list_services,
)
from apps.portal.services.holidays import count_business_days
from apps.portal.services.investment import build_investment_view
from apps.portal.services.kpi_history import (
    build_matrix,
    chart_series,
)
from apps.portal.services.kpi_history_loader import load_kpi_history
from apps.portal.services.kpis_dm import build_kpi_view
from apps.portal.services.manager_detail import (
    build_manager_detail,
    find_manager,
)
from apps.portal.services.operations_summary import (
    build_operations_summary,
    last_closed_month,
)
from apps.portal.services.period_filter import (
    build_picker,
    parse_period,
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
from apps.portal.services.project_loader import load_project_dashboard
from apps.portal.services.project_page import build_project_page
from apps.portal.services.slugs import build_slug
from apps.portal.services.time_cost import average

"""BKD.120.010 - Vistas del portal
Reemplazan la portada anterior. Leen datos reales cuando existen y
marcan como "Ejemplo" lo que todavia no tiene fuente conectada.
"""


def _needs_login(request: HttpRequest) -> bool:
    """Indica si hay que mandar al usuario a iniciar sesion."""
    return bool(
        settings.PORTAL_LOGIN_REQUIRED and not request.user.is_authenticated,
    )


def _base_context(load: PortfolioLoad) -> dict[str, Any]:
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


def _operativa_key(request: Any) -> Any:
    filters = "|".join(request.GET.get(k, "") for k in ("servicio", "cuenta"))
    return (
        "portal:operativa:snapshot:v4:"
        + timezone.localdate().isoformat()
        + ":"
        + hashlib.sha256(filters.encode()).hexdigest()
    )


@require_GET
def operativa(request: Any) -> Any:
    """Muestra el corte guardado y carga los datos aparte."""
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())
    context = cache.get(_operativa_key(request))
    if context is None:
        from apps.portal.schemas import EvaCard

        summary = summarize_portfolio([])
        context = {
            "active": "operativa",
            "period": current_quarter(timezone.localdate()),
            "summary": summary,
            "health": summary.health,
            "donut": build_donut_segments(summary.health),
            "loading": True,
            "eva1_card": EvaCard(available=False),
            "eva2_card": EvaCard(available=False),
            "eva3_card": EvaCard(available=False),
            "investment": {"complete": False, "loading": True},
            "capacity_live": {"loading": True},
            "selected_service": request.GET.get("servicio", ""),
            "selected_client": request.GET.get("cuenta", ""),
        }
    context = dict(context)
    context["async_operativa"] = True
    return render(request, "portal/operativa.html", context)


def _operativa_block_error(context: dict[str, Any], block: str) -> str:
    """Describe una carga incompleta sin reemplazar el corte disponible."""
    if block == "inversion":
        investment = context["investment"]
        if not investment.get("complete"):
            return str(investment.get("error") or "Inversión no disponible.")
    elif block == "capacidad":
        capacity = context["capacity_live"]
        if capacity.get("error") or capacity.get("pending"):
            return str(
                capacity.get("error")
                or "Capacidad con asignaciones pendientes."
            )
    return ""


@require_GET
def operativa_datos(request: HttpRequest) -> HttpResponse:
    """
    Muestra la pantalla Operativa con filtros de Servicio y Cuenta.

    Args:
        request: Peticion HTTP; acepta ?servicio= y ?cuenta=.

    Returns:
        La pagina con los indicadores y los Delivery Managers.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    block = request.GET.get("bloque", "")
    saved = cache.get(_operativa_key(request))
    if saved and block in {"inversion", "capacidad", "eva3"}:
        from apps.portal.services.operational_sources import (
            legacy_capacity,
            tagged_investment,
        )

        context = dict(saved)
        if block == "inversion":
            context["investment"] = tagged_investment(load_eva2().view.projects)
        elif block == "capacidad":
            context["capacity_live"] = legacy_capacity(
                timezone.localdate().strftime("%Y-%m")
            )
        else:
            aer = load_eva1()
            ixb = load_eva2()
            if aer.error or ixb.error:
                return render(
                    request,
                    "portal/operativa.html",
                    {
                        **saved,
                        "refresh_block": block,
                        "block_error": aer.error or ixb.error,
                    },
                )
            context["eva3_card"] = build_eva1_card(aer)
            from apps.portal.services.operational_sources import eva_projects

            population = filter_projects(
                eva_projects(ixb, aer),
                request.GET.get("servicio", ""),
                request.GET.get("cuenta", ""),
            )
            context["managers"] = summarize_delivery_managers(population)
            context["summary"] = summarize_portfolio(population)
            context["health"] = context["summary"].health
            context["donut"] = build_donut_segments(context["health"])
        block_error = _operativa_block_error(context, block)
        if block_error:
            return render(
                request,
                "portal/operativa.html",
                {**saved, "refresh_block": block, "block_error": block_error},
            )
        if block == "inversion":
            cache.set("portal:ops:investment", context["investment"], 86400)
        elif block == "capacidad":
            cache.set("portal:ops:capacity", context["capacity_live"], 86400)
        # Preserve changes completed by other asynchronous blocks.
        latest = cache.get(_operativa_key(request)) or saved
        latest.update(
            {
                k: context[k]
                for k in {
                    "inversion": "investment",
                    "capacidad": "capacity_live",
                    "eva3": "eva3_card",
                }.values()
                if k
                == {
                    "inversion": "investment",
                    "capacidad": "capacity_live",
                    "eva3": "eva3_card",
                }[block]
            }
        )
        if block == "eva3":
            latest.update(
                {
                    k: context[k]
                    for k in ("managers", "summary", "health", "donut")
                }
            )
        cache.set(_operativa_key(request), latest, 86400)
        return render(
            request,
            "portal/operativa.html",
            {**latest, "refresh_block": block},
        )
    load = PortfolioLoad(projects=(), loaded_at=timezone.localtime(), error="")
    selected_service = request.GET.get("servicio", "").strip()
    selected_client = request.GET.get("cuenta", "").strip()
    from apps.portal.schemas import EvaCard
    from apps.portal.services.operational_sources import (
        eva_projects,
        legacy_capacity,
        tagged_investment,
    )

    ixb = load_eva2()
    aer = load_eva1(enrich=False)
    eva_population = eva_projects(ixb, aer)
    projects = filter_projects(
        eva_population,
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
            "services": list_services(eva_population),
            "clients": list_clients(eva_population),
            "selected_service": selected_service,
            "selected_client": selected_client,
            "has_projects": bool(projects),
            "eva1_card": EvaCard(
                available=not ixb.error,
                total_projects=ixb.view.total_projects,
                time_cost=ixb.view.time_cost,
            ),
            "eva3_card": build_eva1_card(aer),
            "eva2_card": EvaCard(
                available=not ixb.error,
                total_projects=ixb.view.total_projects,
                time_cost=ixb.view.time_cost,
            ),
            "investment": cache.get("portal:ops:investment")
            or {"complete": False, "loading": True},
            "capacity_live": cache.get("portal:ops:capacity")
            or {"loading": True},
            "source_errors": [e for e in (ixb.error, aer.error) if e],
            "portfolio_unavailable": bool(ixb.error and aer.error),
        },
    )

    block = request.GET.get("bloque", "")
    if block == "inversion":
        context["investment"] = tagged_investment(ixb.view.projects)
        cache.set("portal:ops:investment", context["investment"], 86400)
    elif block == "capacidad":
        context["capacity_live"] = legacy_capacity(
            timezone.localdate().strftime("%Y-%m")
        )
        cache.set("portal:ops:capacity", context["capacity_live"], 86400)
    elif block == "eva3":
        aer = load_eva1()
        context["eva3_card"] = build_eva1_card(aer)
    context["loading"] = False
    if saved and (ixb.error or aer.error) and not block:
        return render(
            request,
            "portal/operativa.html",
            {
                **saved,
                "source_errors": context["source_errors"],
                "stale": True,
            },
        )
    if ixb.error or aer.error:
        return render(
            request,
            "portal/operativa.html",
            {**context, "refresh_block": block},
        )
    cache.set(_operativa_key(request), context, 86400)
    return render(
        request,
        "portal/operativa.html",
        {**context, "refresh_block": block},
    )


@require_GET
def comercial(request: HttpRequest) -> HttpResponse:
    """
    Muestra los registros comerciales de Backlog_Proyectos en USD.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina Comercial del diseno aprobado.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    from apps.portal.services.commercial_view import build_commercial_context

    context = build_commercial_context(request.GET)
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

    from apps.portal.services.operational_sources import (
        aer_open_risks,
        eva_projects,
        manager_monthly_history,
        remaining_days,
        tagged_investment,
    )

    ixb, aer = load_eva2(), load_eva1()
    load = PortfolioLoad(
        projects=eva_projects(ixb, aer),
        loaded_at=timezone.localtime(),
        error=" · ".join(e for e in (ixb.error, aer.error) if e),
    )
    found = find_manager(load.projects, slug)

    if found is None:
        if load.error:
            return redirect("portal:operativa")

        raise Http404("No existe ese Delivery Manager.")

    from dataclasses import asdict

    detail = build_manager_detail(*found)
    all_sources: list[Any] = list(ixb.view.projects)
    all_sources.extend(aer.view.projects)
    sources = {p.project_id: p for p in all_sources if p.manager == found[0]}
    risks = aer_open_risks(
        [
            pid
            for pid, source in sources.items()
            if not hasattr(source, "risk_titles")
        ]
    )
    investment = tagged_investment(
        list(sources.values()), include_suspended=True
    )
    project_rows = []
    for row in detail.rows:
        source = sources.get(row.project_id)
        if source is None:
            continue
        data = asdict(row)
        data["account_slug"] = build_slug(row.client)
        data.update(
            {
                "service": source.service,
                "fte": getattr(source, "fte", None),
                "start": source.start,
                "end": source.end,
                "budget": source.budget,
                "burn": source.burn,
                "etc_hours": source.etc,
                "progress_percent": source.progress,
                "renewal_days": remaining_days(source),
                "risk_label": len(source.risk_titles)
                if hasattr(source, "risk_titles")
                else risks.get(row.project_id, "No disponible"),
            }
        )
        days = data["renewal_days"]
        if data["status_code"] in ("r", "a") and not (
            source.budget > 0
            and source.burn is not None
            and source.burn > source.budget
        ):
            data["detail"] = (
                f"{-days} d\u00edas de vencido"
                if days is not None and days < 0
                else "Pocos d\u00edas y horas restantes"
            )
        hours = investment.get("by_project", {}).get(row.project_id, {})
        data["investment_operational"] = (
            hours.get("operational") if investment["complete"] else None
        )
        data["investment_commercial"] = (
            hours.get("commercial") if investment["complete"] else None
        )
        project_rows.append(data)
    context = _base_context(load)
    context.update(
        {
            "active": "operativa",
            "detail": detail,
            "project_rows": project_rows,
            "monthly_history": manager_monthly_history(
                found[0], list(sources.values())
            ),
            "investment": investment,
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

    from django.http import JsonResponse

    from apps.ejecutivo.account_rpc import (
        get_account_consumption,
        get_account_view,
    )

    client = request.GET.get("nombre", "").strip()
    if not client:
        portfolio = load_portfolio()
        found = find_account(portfolio.projects, slug)
        if found is None:
            if portfolio.error:
                return redirect("portal:operativa")
            raise Http404("No existe esa cuenta.")
        client = found[0]
    if request.GET.get("bloque") == "consumos":
        return JsonResponse(
            get_account_consumption(client, request.GET.get("offset", 0), 3)
        )
    data = get_account_view(client)
    projects = data.get("proyectos", [])
    groups: dict[str, dict[str, Any]] = {}
    for project in projects:
        group = groups.setdefault(
            project.get("servicio") or "Sin servicio",
            {
                "name": project.get("servicio") or "Sin servicio",
                "budget": 0,
                "burn": 0,
            },
        )
        group["budget"] += project.get("budget") or 0
        group["burn"] += project.get("burn") or 0
    budget = sum(p.get("budget") or 0 for p in projects)
    burn = sum(p.get("burn") or 0 for p in projects)
    maximum = max([1, *[max(g["budget"], g["burn"]) for g in groups.values()]])
    for group in groups.values():
        group["budget_width"] = group["budget"] / maximum * 100
        group["burn_width"] = group["burn"] / maximum * 100
    states: dict[str, int] = {}
    for project in projects:
        state = project.get("estado") or "Sin estado"
        states[state] = states.get(state, 0) + 1
    known = [
        p
        for p in projects
        if p.get("budget")
        and p.get("burn") is not None
        and not p.get("clockifyPending")
    ]
    progress = (
        sum(p["burn"] / p["budget"] * 100 for p in known) / len(known)
        if known
        else None
    )
    risky = sum(1 for p in projects if p.get("excedido") or p.get("atrasado"))
    for group in groups.values():
        subset = [
            p
            for p in projects
            if (p.get("servicio") or "Sin servicio") == group["name"]
        ]
        group["count"] = len(subset)
        group["completed"] = (
            round(
                sum(
                    1
                    for p in subset
                    if str(p.get("etapa", "")).lower()
                    in ("completed", "completado")
                    and not p.get("excedido")
                    and not p.get("atrasado")
                )
                / len(subset)
                * 100
            )
            if subset
            else 0
        )
        group["risk"] = (
            round(
                sum(1 for p in subset if p.get("excedido") or p.get("atrasado"))
                / len(subset)
                * 100
            )
            if subset
            else 0
        )
        group["other"] = max(0, 100 - group["completed"] - group["risk"])
    palette = ["#24bc86", "#6540ed", "#f5b326", "#ec4d79", "#b1abc4"]
    state_rows = []
    running = 0.0
    for index, (name, count) in enumerate(states.items()):
        percent = count / len(projects) * 100 if projects else 0
        state_rows.append(
            {
                "name": name,
                "count": count,
                "percent": round(percent),
                "dash": percent,
                "offset": -running,
                "color": palette[index % len(palette)],
            }
        )
        running += percent
    context = {
        "active": "operativa",
        "loaded_at": timezone.localtime(),
        "data": data,
        "client": client,
        "projects": projects,
        "total": len(projects),
        "budget": budget,
        "burn": burn,
        "groups": list(groups.values()),
        "states": [
            {
                "name": key,
                "count": value,
                "percent": round(value / len(projects) * 100)
                if projects
                else 0,
            }
            for key, value in states.items()
        ],
        "alerts": [
            p for p in projects if p.get("excedido") or p.get("atrasado")
        ],
        "progress": progress,
        "risk_percent": round(risky / len(projects) * 100) if projects else 0,
        "risk_count": risky,
        "cost_variance": round((burn - budget) / budget * 100, 1)
        if budget
        else None,
        "state_chart": state_rows,
        "development": sum(
            1 for p in projects if p.get("estado") == "En desarrollo"
        ),
    }
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
def eva1(request: HttpRequest) -> HttpResponse:
    """
    Muestra EVA 1: proyectos IXB y RaaS por Delivery Manager.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina EVA 1 con los datos de la historico, Clockify y Azure DevOps.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_eva2()

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


@require_GET
@ensure_csrf_cookie
def eva3(request: HttpRequest) -> HttpResponse:
    """
    Muestra EVA 3: proyectos AER y T&M por Delivery Manager.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina EVA 3 con los datos de la hoja MPB.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    load = load_eva1()

    return render(
        request,
        "portal/eva3.html",
        {
            "active": "operativa",
            "loaded_at": timezone.localtime(),
            "error": load.error,
            "eva": load.view,
            "renewal_average": average(
                p.renewal_days for p in load.view.projects
            ),
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


@require_GET
def kpis_delivery_managers(request: HttpRequest) -> HttpResponse:
    """
    Muestra TP, T y C de cada Delivery Manager en el periodo elegido.

    Args:
        request: Peticion HTTP; acepta ?periodo=anio|trimestre|mes.

    Returns:
        La pagina de KPIs de Delivery Managers.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    period = _period(request)
    load = load_portfolio()
    history = load_kpi_history(period.year)
    context = _base_context(load)
    context.update(_period_context(request, period))
    context.update(
        {
            "active": "operativa",
            "kpis": build_kpi_view(load.projects),
            "cut_label": timezone.localdate().strftime("%d/%m/%Y"),
            "cut_is_current": True,
            "history_error": history.error,
        },
    )

    if history.history is not None:
        quarters = {f"T{(int(m[5:7]) - 1) // 3 + 1}" for m in period.months}
        months = build_matrix(
            [cut for cut in history.history.months if cut.key in period.months],
            history.history.managers,
        )
        end_cut = next(
            cut for cut in history.history.months if cut.key == period.end_month
        )

        if not end_cut.partial:
            context.update(
                {
                    "kpis": end_cut.view,
                    "cut_label": end_cut.cut_label,
                    "cut_is_current": False,
                },
            )

        context.update(
            {
                "month_matrix": months,
                "quarter_matrix": build_matrix(
                    [
                        cut
                        for cut in history.history.quarters
                        if cut.label in quarters
                    ],
                    history.history.managers,
                ),
                "chart": _kpi_chart(history.history, period),
            },
        )

    return render(request, "portal/kpis_dm.html", context)


def _kpi_chart(history: KpiHistory, period: Period) -> dict[str, object]:
    """Grafica de C: enero hasta el fin del periodo, con el periodo marcado."""
    cuts = [cut for cut in history.months if cut.key <= period.end_month]
    chart = chart_series(
        build_matrix(cuts, history.managers),
        KPI_HISTORY_CHART_MANAGERS,
    )
    chart["highlight"] = [cut.label for cut in cuts if cut.key in period.months]

    return chart


def _period(request: HttpRequest) -> Period:
    """Periodo elegido (?periodo=anio|trimestre|mes), sin pasar de hoy."""
    return parse_period(
        {key: request.GET.get(key, "") for key in request.GET},
        timezone.localdate(),
    )


def _period_context(request: HttpRequest, period: Period) -> dict[str, object]:
    """Selector de periodo y datos para conservarlo al cambiar de pestana."""
    picker = build_picker(
        period,
        timezone.localdate(),
        {key: request.GET.getlist(key) for key in request.GET},
    )

    return {"period": period, "picker": picker}


def _facturability_month(request: HttpRequest) -> str:
    """Ultimo mes del periodo elegido (o el actual)."""
    return _period(request).end_month


def _facturability_context(month: str, tab: str) -> dict[str, object]:
    """Datos comunes de las pestanas de Facturabilidad."""
    return {
        "active": "operativa",
        "loaded_at": timezone.localtime(),
        "month": month,
        "tab": tab,
    }


@require_GET
def facturabilidad(request: HttpRequest) -> HttpResponse:
    """
    Muestra la facturabilidad de enero al mes elegido.

    Args:
        request: Peticion HTTP; acepta ?periodo=anio|trimestre|mes y el
            filtro de roles.

    Returns:
        La pagina de Facturabilidad.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    period = _period(request)
    month = period.end_month
    sources = load_year_sources(month)
    scope, role_options = _role_scope(request, sources)
    months = [
        build_month_facturability(item.month, item.gse, item.error, scope)
        for item in sources
    ]
    selected = combine_months(
        [item for item in months if item.month in period.months],
        period.label,
        period.label,
    )
    context = _facturability_context(month, "general")
    context.update(_period_context(request, period))
    context.update(
        {
            "months": months,
            "selected": selected,
            "first": months[0],
            "in_period": period.months,
            "errors": [item for item in months if item.error],
            "no_roster": ", ".join(
                item.short_label for item in months if item.notice
            ),
            "role_options": role_options,
        },
    )

    return render(request, "portal/facturabilidad.html", context)


@require_GET
def facturabilidad_especialidad(request: HttpRequest) -> HttpResponse:
    """
    Muestra la facturabilidad del mes por especialidad.

    Args:
        request: Peticion HTTP; acepta ?periodo=anio|trimestre|mes y el
            filtro de roles.

    Returns:
        La pagina por especialidad.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    period = _period(request)
    month = period.end_month
    loaded = [load_month_sources(item) for item in period.months]
    scope, role_options = _role_scope(request, loaded)
    specialties = merge_specialties(
        [build_specialties(item.gse, item.month, scope) for item in loaded],
    )
    selected = combine_months(
        [
            build_month_facturability(
                item.month,
                item.gse,
                item.error,
                scope,
            )
            for item in loaded
        ],
        period.label,
        period.label,
    )
    errors = " · ".join(item.error for item in loaded if item.error)
    context = _facturability_context(month, "especialidad")
    context.update(_period_context(request, period))
    context.update(
        {
            "selected": selected,
            "specialties": specialties,
            "headcount": sum(row.headcount for row in specialties),
            "dev_free": next(
                (
                    row.free_fte
                    for row in specialties
                    if "dev" in row.name.lower()
                ),
                None,
            ),
            "error": errors,
            "role_options": role_options,
        },
    )

    return render(request, "portal/facturabilidad_especialidad.html", context)


@require_GET
def facturabilidad_recurso(request: HttpRequest) -> HttpResponse:
    """
    Muestra la facturabilidad de cada persona, de enero al mes elegido.

    Args:
        request: Peticion HTTP; acepta ?periodo=anio|trimestre|mes y el
            filtro de roles.

    Returns:
        La pagina por recurso.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    period = _period(request)
    month = period.end_month
    sources = load_year_sources(month)
    scope, role_options = _role_scope(request, sources)
    rows = build_resources(
        [(item.month, item.gse) for item in sources],
        scope,
    )
    by_month, overall = team_averages(rows, len(sources))
    context = _facturability_context(month, "recurso")
    context.update(_period_context(request, period))
    context.update(
        {
            "labels": [
                build_month_facturability(item.month, {}).short_label
                for item in sources
            ],
            "workdays": [count_business_days(item.month) for item in sources],
            "rows": rows,
            "team_by_month": by_month,
            "team_average": overall,
            "no_roster": ", ".join(
                build_month_facturability(item.month, {}).short_label
                for item in sources
                if item.gse.get("plantillaAviso")
            ),
            "error": " · ".join(
                f"{item.month}: {item.error}" for item in sources if item.error
            ),
            "role_options": role_options,
        },
    )

    return render(request, "portal/facturabilidad_recurso.html", context)


def _peek_investment() -> InvestmentView | None:
    """Inversion del mes actual solo si ya se leyo (para Operativa)."""
    month = str(timezone.localdate().strftime("%Y-%m"))
    sources = peek_month_sources(month)

    if sources is None:
        return None

    return build_investment_view(sources.gse, month)


@require_GET
def inversion(request: HttpRequest) -> HttpResponse:
    """
    Muestra las horas de inversion comercial y operativa del mes.

    Args:
        request: Peticion HTTP; acepta ?mes=YYYY-MM.

    Returns:
        La pagina de inversion.
    """
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())

    month = _facturability_month(request)
    sources = load_month_sources(month)
    context = _facturability_context(month, "inversion")
    context.update(
        {
            "investment": build_investment_view(sources.gse, month),
            "error": sources.error,
        },
    )

    return render(request, "portal/inversion.html", context)


def _role_scope(
    request: HttpRequest,
    sources: list[MonthSources],
) -> tuple[tuple[frozenset[str], None], list[RoleOption]]:
    """
    Roles elegidos (?roles=1&rol=DEV&rol=QA) o, si no hay, los operativos.

    Args:
        request: Peticion HTTP.
        sources: Meses leidos, para saber que roles existen.

    Returns:
        ((claves de roles, hoy), opciones para el filtro).
    """
    all_roles = list_roles(item.gse for item in sources)
    allowed = default_role_keys(all_roles)
    available = tuple(name for name in all_roles if role_key(name) in allowed)

    if request.GET.get("roles") == "1":
        chosen = frozenset(
            role_key(name)
            for name in request.GET.getlist("rol")
            if role_key(name) in allowed
        )
    else:
        chosen = default_role_keys(available)

    options = [
        RoleOption(
            label=name,
            key=role_key(name),
            checked=role_key(name) in chosen,
            display=display_role(name),
        )
        for name in available
    ]

    return (chosen, None), options


@require_GET
def operations_resumen(request: HttpRequest) -> HttpResponse:
    """
    Fragmento de la tarjeta Operations; Operativa lo carga aparte.

    Lee GSE y Recursos de enero al ultimo mes cerrado. Va separado para
    que esa lectura no haga lenta la pagina Operativa.

    Args:
        request: Peticion HTTP.

    Returns:
        El HTML de la tarjeta (sin la pagina completa).
    """
    if _needs_login(request):
        return HttpResponse(status=401)

    today = timezone.localdate()
    month = last_closed_month(today)
    sources = load_year_sources(month)
    roles = default_role_keys(list_roles(item.gse for item in sources))
    months = [
        build_month_facturability(
            item.month,
            item.gse,
            item.error,
            (roles, None),
        )
        for item in sources
    ]

    return render(
        request,
        "portal/_operations_summary.html",
        {
            "ops": build_operations_summary(
                months,
                month_closed=month != str(today.strftime("%Y-%m")),
            ),
        },
    )
