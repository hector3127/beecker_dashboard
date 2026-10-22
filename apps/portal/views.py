"""Pantallas Ejecutiva, Operativa y Comercial."""

import hashlib
from typing import Any

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.cache import cache
from django.http import Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from apps.access.checks import resolve, scope_for
from apps.access.scope import AccessScope
from apps.portal.constants import KPI_HISTORY_CHART_MANAGERS
from apps.portal.schemas import (
    CapacityFilters,
    InvestmentView,
    KpiHistory,
    Period,
    RoleOption,
)
from apps.portal.services.account_options import account_names
from apps.portal.services.capacity import (
    build_capacity_csv,
    build_capacity_view,
    normalize_month,
    parse_workday_hours,
)
from apps.portal.services.capacity_loader import load_capacity
from apps.portal.services.closed_aer_burn import fill_closed_burn
from apps.portal.services.eva_loader import (
    build_eva1_card,
    load_eva1,
    load_eva2,
    load_eva2_closed,
)
from apps.portal.services.executive_period import (
    current as executive_period,
)
from apps.portal.services.executive_period import (
    period_view,
)
from apps.portal.services.executive_period import (
    query_string as executive_query_string,
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
from apps.portal.services.kpi_quarterly import build_quarter_averages
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
)
from apps.portal.services.portfolio_loader import (
    load_portfolio as load_portfolio,  # pages.cuenta lo llama por aqui
)
from apps.portal.services.portfolio_summary import (
    build_donut_segments,
    summarize_delivery_managers,
    summarize_portfolio,
)
from apps.portal.services.project_loader import load_project_dashboard
from apps.portal.services.project_page import build_project_page
from apps.portal.services.return_navigation import return_context
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


@require_http_methods(["GET", "POST"])
@period_view
def actualizacion_ejecutiva(request: HttpRequest) -> HttpResponse:
    """Starts or checks an executive refresh without waiting for sources."""
    from django.http import JsonResponse

    from apps.portal.services.executive_refresh import (
        refresh_status,
        request_refresh,
    )

    if _needs_login(request):
        return JsonResponse({"error": "Inicia sesion"}, status=401)
    status = (
        request_refresh(force=True)
        if request.method == "POST"
        else refresh_status()
    )
    from apps.portal.services.executive_operations import (
        cached_operations_snapshot,
    )
    from apps.portal.services.financial_cache import cached_financial_snapshot

    snapshot = cached_financial_snapshot()
    status = {
        **status,
        "has_financial_cut": bool(snapshot.get("loaded_at")),
        "has_commercial_cut": bool(snapshot.get("commercial")),
        "has_operations_cut": (
            cached_operations_snapshot().get("projects") is not None
        ),
    }
    response = JsonResponse(status)
    response["Cache-Control"] = "no-store"
    return response


def _operativa_key(request: Any) -> str:
    filters = "|".join(request.GET.get(k, "") for k in ("servicio", "cuenta"))
    scope = scope_for(request)
    if not scope.unrestricted:
        # Cada alcance tiene su propio corte: nunca se comparte con otro.
        filters += "|" + scope.signature()
    return (
        "portal:operativa:snapshot:v10:"
        + timezone.localdate().isoformat()
        + ":"
        + hashlib.sha256(filters.encode()).hexdigest()
    )


_OPS_BLOCKS = ("base", "eva3", "inversion", "capacidad", "eva4")
_OPS_FRESH_SECONDS = 300


def _operativa_fresh_key(request: Any, block: str) -> str:
    """Separa la vigencia de cada bloque del corte guardado."""
    return (
        _operativa_key(request)
        + ":fresh:"
        + block
        + (":v2" if block == "eva4" else "")
    )


def _operativa_is_fresh(request: Any) -> bool:
    """Solo omite la actualizacion cuando todos los bloques estan vigentes."""
    keys = [_operativa_fresh_key(request, block) for block in _OPS_BLOCKS]
    markers = cache.get_many(keys)
    return all(markers.get(key) for key in keys)


def _operations_summary_key() -> str:
    """Identifica el resumen por su ultimo mes cerrado."""
    return "portal:ops:summary-data:v1:" + last_closed_month(
        timezone.localdate()
    )


def _scope_operativa_investment(request: Any, context: dict[str, Any]) -> None:
    """Limit displayed investment to the projects in the filtered portfolio."""
    if scope_for(request).unrestricted and not any(
        request.GET.get(key, "").strip() for key in ("servicio", "cuenta")
    ):
        return
    investment = context.get("investment")
    if not investment or not investment.get("complete"):
        return
    project_ids = {
        pid
        for manager in context.get("managers", ())
        for pid in manager.project_ids
    }
    by_project = investment.get("by_project", {})
    context["investment"] = {
        **investment,
        "totals": {
            category: sum(
                by_project[pid].get(category, 0)
                for pid in project_ids
                if pid in by_project
            )
            for category in ("operational", "commercial")
        },
    }


def _in_scope(request: Any, projects: Any) -> list[Any]:
    """Los proyectos que la persona de la peticion puede ver."""
    return scope_for(request).filter_projects(
        projects, lambda p: p.project_id, lambda p: p.client
    )


def _account_options(request: Any, fallback: Any) -> list[str]:
    """Cuentas del selector: el catalogo financiero, solo las permitidas."""
    return scope_for(request).filter_accounts(account_names(fallback))


def _scoped_eva4(request: Any) -> dict[str, Any]:
    """Corte de EVA-04 con solo lo que el alcance permite."""
    from apps.portal.services import eva4

    return eva4.restrict(
        eva4.cached_eva4(), scope_for(request), timezone.localdate()
    )


def _operativa_snapshot(request: Any) -> dict[str, Any] | None:
    """Compone bloques independientes sin perder respuestas paralelas."""
    key = _operativa_key(request)
    saved = cache.get(key)
    if saved is None:
        return None
    context = dict(saved)
    keys = [key + ":block:" + block for block in _OPS_BLOCKS[1:]]
    patches = cache.get_many(keys)
    for block_key in keys:
        context.update(patches.get(block_key, {}))
    context["eva4"] = _scoped_eva4(request)
    context["clients"] = _account_options(request, context.get("clients", ()))
    _scope_operativa_investment(request, context)
    return context


def operativa_context(request: Any) -> dict[str, Any]:
    """Corte guardado de Operativa; la plantilla y la API lo comparten."""
    context = _operativa_snapshot(request)
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
            "consumption_pending": True,
            "eva1_card": EvaCard(available=False),
            "eva2_card": EvaCard(available=False),
            "eva3_card": EvaCard(available=False),
            "investment": {"complete": False, "loading": True},
            "capacity_live": {"loading": True},
            "selected_service": request.GET.get("servicio", ""),
            "selected_client": request.GET.get("cuenta", ""),
        }
    context = dict(context)
    context["clients"] = _account_options(request, context.get("clients", ()))
    context["eva4"] = _scoped_eva4(request)
    context["pending_blocks"] = ",".join(
        block
        for block in _OPS_BLOCKS
        if not cache.get(_operativa_fresh_key(request, block))
    )
    context["async_operativa"] = not (
        context.get("loaded_at") and _operativa_is_fresh(request)
    )
    summary_key = _operations_summary_key()
    context["operations_summary"] = cache.get(summary_key)
    context["summary_fresh"] = bool(
        context["operations_summary"] and cache.get(summary_key + ":fresh")
    )
    return context


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


def _operativa_investment(ixb: Any, aer: Any) -> dict[str, Any]:
    """Reuse the tagged-hours calculation for both EVA project populations."""
    from apps.portal.services.operational_sources import tagged_investment

    errors = [source.error for source in (ixb, aer) if source.error]
    if errors:
        return {"complete": False, "error": "; ".join(errors)}
    investment: dict[str, Any] = tagged_investment(
        [*ixb.view.projects, *aer.view.projects]
    )
    return investment


def operativa_block_context(request: Any) -> dict[str, Any]:
    """
    Muestra la pantalla Operativa con filtros de Servicio y Cuenta.

    Args:
        request: Peticion HTTP; acepta ?servicio= y ?cuenta=.

    Returns:
        El contexto con los indicadores y los Delivery Managers.
    """
    from apps.portal.schemas import EvaCard

    block = request.GET.get("bloque", "")
    saved = _operativa_snapshot(request)
    if block == "eva4":
        from apps.portal.services.eva4 import load_eva4

        result = load_eva4()
        context = dict(saved or {})
        context.update({"eva4": result, "refresh_block": block})
        if result.get("error"):
            context["block_error"] = result["error"]
        else:
            cache.set(_operativa_fresh_key(request, "eva4"), True, 300)
        return context
    if (
        saved
        and request.GET.get("actualizar") != "1"
        and cache.get(_operativa_fresh_key(request, block or "base"))
    ):
        return {**saved, "refresh_block": block}
    if saved and block in {"inversion", "capacidad", "eva3"}:
        from apps.portal.services.operational_sources import (
            legacy_capacity,
        )

        context = dict(saved)
        if block == "inversion":
            context["investment"] = _operativa_investment(
                load_eva2(enrich=False), load_eva1(enrich=False)
            )
        elif block == "capacidad":
            context["capacity_live"] = legacy_capacity(
                timezone.localdate().strftime("%Y-%m")
            )
        else:
            aer = load_eva1()
            ixb = load_eva2()
            if aer.error or ixb.error:
                return {
                    **saved,
                    "refresh_block": block,
                    "block_error": aer.error or ixb.error,
                }
            context["eva3_card"] = build_eva1_card(aer)
            from apps.portal.services.operational_sources import eva_projects

            population = filter_projects(
                _in_scope(request, eva_projects(ixb, aer)),
                request.GET.get("servicio", ""),
                request.GET.get("cuenta", ""),
            )
            context["managers"] = summarize_delivery_managers(population)
            context["summary"] = summarize_portfolio(population)
            context["health"] = context["summary"].health
            context["donut"] = build_donut_segments(context["health"])
            context["consumption_pending"] = False
            context["eva1_card"] = EvaCard(
                available=True,
                total_projects=ixb.view.total_projects,
                time_cost=ixb.view.time_cost,
            )
            context["eva2_card"] = context["eva1_card"]
        block_error = _operativa_block_error(context, block)
        if block_error:
            return {**saved, "refresh_block": block, "block_error": block_error}
        if block == "inversion":
            cache.set("portal:ops:investment:v3", context["investment"], 86400)
        elif block == "capacidad":
            cache.set("portal:ops:capacity:v2", context["capacity_live"], 86400)
        _scope_operativa_investment(request, context)
        changed = {
            "inversion": ("investment",),
            "capacidad": ("capacity_live",),
            "eva3": (
                "managers",
                "summary",
                "health",
                "donut",
                "eva3_card",
                "eva1_card",
                "eva2_card",
                "consumption_pending",
            ),
        }[block]
        cache.set(
            _operativa_key(request) + ":block:" + block,
            {key: context[key] for key in changed},
            86400,
        )
        latest = _operativa_snapshot(request) or context
        cache.set(_operativa_key(request), latest, 86400)
        cache.set(
            _operativa_fresh_key(request, block), True, _OPS_FRESH_SECONDS
        )
        return {**latest, "refresh_block": block}
    load = PortfolioLoad(projects=(), loaded_at=timezone.localtime(), error="")
    selected_service = request.GET.get("servicio", "").strip()
    selected_client = request.GET.get("cuenta", "").strip()
    from apps.portal.schemas import EvaCard
    from apps.portal.services.operational_sources import (
        eva_projects,
        legacy_capacity,
    )

    ixb = load_eva2(enrich=block == "eva3")
    aer = load_eva1(enrich=False)
    eva_population = _in_scope(request, eva_projects(ixb, aer))
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
            "clients": _account_options(request, list_clients(eva_population)),
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
            "investment": cache.get("portal:ops:investment:v3")
            or {"complete": False, "loading": True},
            "capacity_live": cache.get("portal:ops:capacity:v2")
            or {"loading": True},
            "source_errors": [e for e in (ixb.error, aer.error) if e],
            "portfolio_unavailable": bool(ixb.error and aer.error),
        },
    )

    block = request.GET.get("bloque", "")
    if block == "inversion":
        context["investment"] = _operativa_investment(ixb, aer)
        cache.set("portal:ops:investment:v3", context["investment"], 86400)
    elif block == "capacidad":
        context["capacity_live"] = legacy_capacity(
            timezone.localdate().strftime("%Y-%m")
        )
        cache.set("portal:ops:capacity:v2", context["capacity_live"], 86400)
    elif block == "eva3":
        aer = load_eva1()
        context["eva3_card"] = build_eva1_card(aer)
        projects = filter_projects(
            _in_scope(request, eva_projects(ixb, aer)),
            selected_service,
            selected_client,
        )
        enriched = summarize_portfolio(projects)
        context.update(
            {
                "summary": enriched,
                "health": enriched.health,
                "donut": build_donut_segments(enriched.health),
                "managers": summarize_delivery_managers(projects),
                "has_projects": bool(projects),
            }
        )
    if saved and not block:
        # Esta carga rapida no trae el consumo completo de EVA 3; se conserva
        # lo ya calculado con el para que la salud no cambie al refrescar.
        context.update(
            {
                key: saved[key]
                for key in (
                    "managers",
                    "summary",
                    "health",
                    "donut",
                    "eva3_card",
                )
                if key in saved
            }
        )
    context["loading"] = False
    context["consumption_pending"] = (
        saved.get("consumption_pending", False)
        if saved and not block
        else block != "eva3"
    )
    _scope_operativa_investment(request, context)
    if saved and (ixb.error or aer.error) and not block:
        return {
            **saved,
            "source_errors": context["source_errors"],
            "stale": True,
        }
    if ixb.error or aer.error:
        return {**context, "refresh_block": block}
    if block and _operativa_block_error(context, block):
        return {
            **context,
            "refresh_block": block,
            "block_error": _operativa_block_error(context, block),
        }
    cache.set(_operativa_key(request), context, 86400)
    cache.set(
        _operativa_fresh_key(request, block or "base"),
        True,
        _OPS_FRESH_SECONDS,
    )
    if not saved:
        cache.set(
            _operativa_fresh_key(request, "base"), True, _OPS_FRESH_SECONDS
        )
    return {**context, "refresh_block": block}


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

    from apps.portal.services.commercial_view import (
        build_commercial_context,
        present_commercial_context,
    )

    key = "portal:commercial:context:v1:" + timezone.localdate().isoformat()
    filters = request.GET.copy()
    refreshing = filters.pop("actualizar", None) == ["1"]
    cached = cache.get(key) if not filters else None
    if cached is not None and (not refreshing or cache.get(key + ":fresh")):
        return render(
            request,
            "portal/comercial.html",
            {
                **present_commercial_context(cached),
                "page_stale": not cache.get(key + ":fresh"),
            },
        )
    context = build_commercial_context(filters)
    if not filters and not context.get("error") and not context.get("fx_error"):
        cache.set(key, context, 86400)
        cache.set(key + ":fresh", True, 300)
    elif cached is not None:
        context = {**cached, "refresh_failed": True}
    return render(
        request, "portal/comercial.html", present_commercial_context(context)
    )


_DM_SECONDS = 300


def _dm_key(slug: str, stage: str, scope: AccessScope | None = None) -> str:
    # Cada alcance limitado tiene su propio corte: nunca se comparte con otro.
    extra = ":" + scope.signature() if scope and not scope.unrestricted else ""
    return "portal:delivery_manager:v3:" + slug + extra + ":" + stage


class ManagerUnavailableError(Exception):
    """No se pudo leer el portafolio y no hay a quien mostrar."""


def _dm_base(slug: str, scope: AccessScope) -> dict[str, Any]:
    """Paso 1: proyectos y estados del Delivery Manager (sin Clockify)."""
    from apps.portal.services.operational_sources import eva_projects

    ixb, aer = load_eva2(), load_eva1()
    load = PortfolioLoad(
        projects=eva_projects(ixb, aer),
        loaded_at=timezone.localtime(),
        error=" \u00b7 ".join(e for e in (ixb.error, aer.error) if e),
    )
    visible = scope.filter_projects(
        load.projects, lambda p: p.project_id, lambda p: p.client
    )
    found = find_manager(visible, slug)

    if found is None:
        if load.error:
            raise ManagerUnavailableError(load.error)

        raise Http404("No existe ese Delivery Manager.")

    detail = build_manager_detail(*found)
    visible_ids = {p.project_id for p in found[1]}
    all_sources: list[Any] = list(ixb.view.projects)
    all_sources.extend(aer.view.projects)
    sources = {
        p.project_id: p
        for p in all_sources
        if p.manager == found[0] and p.project_id in visible_ids
    }
    base = _base_context(load)
    base.update(
        {
            "active": "operativa",
            "detail": detail,
            "dm_name": detail.name,
            "dm_initials": detail.initials,
            "manager_name": found[0],
            "sources": sources,
        }
    )
    if not load.error:
        cache.set(_dm_key(slug, "base", scope), base, _DM_SECONDS)

    return base


def _dm_investment(base: dict[str, Any]) -> dict[str, Any]:
    """Paso 2: inversion por etiquetas de Clockify y riesgos abiertos."""
    from apps.portal.services.operational_sources import (
        aer_open_risks,
        tagged_investment,
    )

    sources = base["sources"]
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

    return {"investment": investment, "risks": risks}


def dm_rows(base: dict[str, Any], extra: dict[str, Any] | None) -> list[Any]:
    """Arma las filas; inversion y riesgo llegan en el paso 2."""
    from dataclasses import asdict

    from apps.portal.services.operational_sources import remaining_days

    sources = base["sources"]
    investment: dict[str, Any] = (
        extra["investment"] if extra else {"complete": False}
    )
    risks: dict[str, Any] = extra["risks"] if extra else {}
    rows = []
    for row in base["detail"].rows:
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
                else risks.get(
                    row.project_id, "\u2026" if not extra else "No disponible"
                ),
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
            hours.get("operational") if investment.get("complete") else None
        )
        data["investment_commercial"] = (
            hours.get("commercial") if investment.get("complete") else None
        )
        rows.append(data)

    return rows


def dm_state(
    slug: str, stage: str, scope: AccessScope
) -> tuple[dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    """Lo calculado del Delivery Manager hasta el paso pedido.

    Cada paso (base, inv, horas) se guarda por separado; pedir uno calcula la
    base si falta. Sin proyectos visibles para esta persona el DM no existe.

    Raises:
        Http404: Ningun proyecto visible tiene a ese Delivery Manager.
        ManagerUnavailableError: Las fuentes no respondieron.
    """
    from apps.portal.services.operational_sources import (
        manager_monthly_history,
    )

    base = cache.get(_dm_key(slug, "base", scope))
    if base is None:
        base = _dm_base(slug, scope)
    extra = cache.get(_dm_key(slug, "inv", scope))
    hours = cache.get(_dm_key(slug, "horas", scope))
    if stage == "inv" and extra is None:
        extra = _dm_investment(base)
        cache.set(_dm_key(slug, "inv", scope), extra, _DM_SECONDS)
    if stage == "horas" and hours is None:
        hours = manager_monthly_history(
            base["manager_name"], list(base["sources"].values())
        )
        cache.set(_dm_key(slug, "horas", scope), hours, _DM_SECONDS)
    return base, extra, hours


@require_GET
@ensure_csrf_cookie
def proyecto_detalle(request: HttpRequest, project_id: str) -> HttpResponse:
    """Abre todas las secciones del proyecto dentro del portal."""
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())
    from django.urls import reverse

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
def eva1_cerrados(request: HttpRequest) -> HttpResponse:
    """
    Entrega la tabla de proyectos IXB/RaaS cerrados para la tarjeta de EVA 1.

    Args:
        request: Peticion HTTP.

    Returns:
        Un fragmento HTML con la tabla del historico de proyectos cerrados.
    """
    if _needs_login(request):
        return HttpResponse(status=401)

    load = load_eva2_closed()

    return render(
        request,
        "portal/_eva_closed.html",
        {"projects": load.view.projects, "error": load.error},
    )


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
def eva4(request: HttpRequest) -> HttpResponse:
    """Pantalla anterior de EVA-04, para comparar hasta ANTERIOR_HASTA.

    La pantalla vigente la entrega pages.eva4, que llama a esta vista solo
    con ?vista=anterior mientras la fecha lo permita.
    """
    from apps.portal.services.eva4 import (
        ANTERIOR_HASTA,
        load_eva4,
        month_picker,
    )

    if _needs_login(request):
        return redirect_to_login(request.get_full_path())
    result = (
        load_eva4(request.GET["mes"]) if request.GET.get("mes") else load_eva4()
    )
    return render(
        request,
        "portal/eva4_anterior.html",
        {
            "active": "operativa",
            "eva4": result,
            "loaded_at": result.get("loaded_at"),
            "error": result.get("error"),
            "anterior_hasta": ANTERIOR_HASTA,
            "picker": month_picker(
                request.GET.get("mes") or result.get("month"),
                timezone.localdate(),
            ),
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
@ensure_csrf_cookie
def facturabilidad_area(request: HttpRequest) -> HttpResponse:
    """Muestra GSE en el portal con sus consultas RPC existentes."""
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())
    period = _period(request)
    return render(
        request,
        "portal/facturabilidad_area.html",
        {
            "active": "operativa",
            "area_year": period.end_month[:4],
            **_period_context(request, period),
        },
    )


@require_GET
@ensure_csrf_cookie
def capacidad_detalle(request: HttpRequest) -> HttpResponse:
    """Abre la capacidad mensual en su propia pagina, con carga progresiva."""
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())
    return render(
        request, "portal/capacidad_detalle.html", {"active": "operativa"}
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

    params = {key: request.GET.get(key, "") for key in request.GET}
    if not any(params.get(key) for key in ("periodo", "mes", "trim")):
        params["periodo"] = "anio"
    period = parse_period(params, timezone.localdate())
    history = load_kpi_history(period.year)
    load = PortfolioLoad(
        projects=(), error=history.error, loaded_at=timezone.localtime()
    )
    context = _base_context(load)
    context.update(_period_context(request, period))
    context.update(
        {
            "active": "operativa",
            "kpis": build_kpi_view(load.projects),
            "cut_label": timezone.localdate().strftime("%d/%m/%Y"),
            "cut_is_current": True,
            "history_error": history.error,
            "history_notice": history.notice,
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

        context.update(
            {
                "kpis": end_cut.view,
                "cut_label": end_cut.cut_label,
                "cut_is_current": end_cut.partial,
            },
        )

        context.update(
            {
                "month_matrix": months,
                "quarter_matrix": build_quarter_averages(
                    [
                        cut
                        for cut in history.history.months
                        if f"T{(int(cut.key[5:7]) - 1) // 3 + 1}" in quarters
                        and cut.key <= period.end_month
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
    chart["highlight"] = [
        f"{cut.label}*" if cut.partial else cut.label
        for cut in cuts
        if cut.key in period.months
    ]

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


def operations_summary_data(refresh: bool = False) -> Any:
    """Facturabilidad global de enero al ultimo mes cerrado.

    Lee GSE y Recursos; por eso se guarda aparte y solo se vuelve a leer
    cuando el corte caduca o se pide actualizar. Un resumen parcial no se
    guarda para no fijar un error.
    """
    today = timezone.localdate()
    month = last_closed_month(today)
    key = _operations_summary_key()
    cached = cache.get(key)
    if cached is not None and cache.get(key + ":fresh") and not refresh:
        return cached
    sources = load_year_sources(month)
    roles = default_role_keys(list_roles(item.gse for item in sources))
    months = [
        build_month_facturability(
            item.month, item.gse, item.error, (roles, None)
        )
        for item in sources
    ]
    summary = build_operations_summary(
        months, month_closed=month != str(today.strftime("%Y-%m"))
    )
    if sources and not summary.errors:
        cache.set(key, summary, 86400)
        cache.set(key + ":fresh", True, _OPS_FRESH_SECONDS)
    return summary


@require_GET
def eva3_cerrados(request: HttpRequest) -> HttpResponse:
    """Historico AER/T&M finalizado en 2026, exclusivamente desde MPB."""
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())
    from apps.ejecutivo.services.aer_tym_summary import (
        build_summary_row,
        find_mpb_header,
        resolve_columns,
    )
    from apps.portal.services.eva1 import build_eva1_view
    from core.exceptions import DashboardError
    from core.sheets.factory import build_sheet_repository

    error = ""
    rows = []
    try:
        values = build_sheet_repository().read_values("MPB")
        header = find_mpb_header(values)
        if header is None:
            error = "No se pudieron identificar los encabezados de MPB."
        else:
            columns = resolve_columns(values[header])
            for row in values[header + 1 :]:
                item = build_summary_row(
                    row, columns, timezone.localdate(), closed_year=2026
                )
                if item is not None:
                    rows.append(item)
    except DashboardError as exc:
        error = exc.build_message()
    return render(
        request,
        "portal/_eva3_closed.html",
        {
            "projects": build_eva1_view(rows).projects,
            "historic_rows": rows,
            "error": error,
        },
    )


def eva3_cerrados_burn(request: HttpRequest) -> HttpResponse:
    """Rellena el Burn de un proyecto AER cerrado."""
    import json

    if _needs_login(request):
        return JsonResponse({"error": "Inicia sesion"}, status=401)
    if request.method != "POST":
        return JsonResponse({"error": "Usa POST"}, status=405)
    try:
        project_id = json.loads(request.body).get("id", "")
        if not isinstance(project_id, str) or not project_id.strip():
            raise ValueError("Falta ID")
        return JsonResponse(fill_closed_burn(project_id))
    except Exception as error:  # noqa: BLE001
        return JsonResponse({"error": str(error)}, status=502)


@require_GET
@period_view
def ingresos(request: HttpRequest) -> HttpResponse:
    """Devuelve ingresos y cobranza de DataRevenue del ejercicio 2026."""
    from django.http import JsonResponse

    from apps.portal.services.revenue import load_revenue
    from core.exceptions import DashboardError

    if _needs_login(request):
        return JsonResponse({"error": "Inicia sesion"}, status=401)
    try:
        return JsonResponse(load_revenue())
    except (DashboardError, ValueError):
        return JsonResponse(
            {"error": "No se pudo consultar DataRevenue"},
            status=502,
        )


@require_GET
@period_view
def costos_revenue(request: HttpRequest) -> HttpResponse:
    """Devuelve costos preparados o calcula el desglose de un proyecto."""
    from django.http import JsonResponse

    from apps.portal.services.revenue_costs import (
        calculate_project_cost,
        cost_summary,
        key,
    )
    from core.exceptions import DashboardError

    if _needs_login(request):
        return JsonResponse({"error": "Inicia sesion"}, status=401)
    from apps.access.checks import resolve

    access = resolve(request)
    account_name = request.GET.get("nombre", "").strip()
    if access.enforced and not access.can("view_costs"):
        return JsonResponse({"error": "Sin acceso a costos"}, status=403)
    if account_name and not access.scope.allows_account(account_name):
        return JsonResponse({"error": "No existe esa cuenta"}, status=404)
    if not account_name and not access.scope.unrestricted:
        # El resumen es del equipo completo: no se recorta por cuenta.
        return JsonResponse({"error": "Sin acceso a costos"}, status=403)

    def prepare_missing(summary: Any) -> Any:
        if any(
            p.get("cost") is None and not p.get("future")
            for p in summary.get("projects", [])
        ):
            from apps.portal.services.executive_refresh import (
                refresh_status,
                request_refresh,
            )

            status = (
                request_refresh()
                if request.GET.get("actualizar") != "1"
                else refresh_status()
            )
            summary = {
                **summary,
                "preparing": status.get("state")
                in {"queued", "running", "busy"},
            }
        return summary

    try:
        pid = request.GET.get("id")
        account = request.GET.get("nombre", "").strip()
        from apps.portal.services.cost_audit_cache import (
            prepared_detail,
            prepared_summary,
            remember,
            remember_summary,
            summary_key,
        )

        if not pid and request.GET.get("actualizar") != "1":
            prepared = prepared_summary(account or None)
            if prepared is not None:
                return JsonResponse(prepare_missing(prepared))
        if pid:
            prepared = prepared_detail(pid, account or None)
            if prepared is not None:
                return JsonResponse(prepared)
        if pid and account:
            from apps.portal.services.revenue_costs import project_ids
            from core.sheets.factory import build_sheet_repository

            if pid.casefold() not in {
                p.casefold()
                for p in project_ids(build_sheet_repository(), account)
            }:
                return JsonResponse(
                    {"error": "El proyecto no pertenece a esta cuenta"},
                    status=400,
                )
        result = (
            calculate_project_cost(pid)
            if pid
            else cost_summary(account=account or None)
        )
        from apps.portal.services.project_profitability import (
            add_project_revenue,
        )
        from core.sheets.factory import build_sheet_repository

        result = add_project_revenue(
            result, build_sheet_repository(), account or None
        )
        if pid:
            remember(result, account or None)
            cache.delete(summary_key(account or None))
        else:
            result = prepare_missing(remember_summary(result, account or None))
        return JsonResponse(result)
    except (DashboardError, ValueError) as error:
        message = (
            error.detail if isinstance(error, DashboardError) else str(error)
        )
        if request.GET.get("id"):
            cache.set(key(request.GET["id"]) + ":error", message, 300)
        return JsonResponse({"error": message}, status=502)


@require_GET
@period_view
def rentabilidad_mensual(request: HttpRequest) -> HttpResponse:
    """Devuelve ingresos, costos y margen de los seis meses cerrados."""
    from django.http import JsonResponse

    from apps.portal.services.monthly_profitability import (
        load_monthly_profitability,
    )
    from core.exceptions import DashboardError

    if _needs_login(request):
        return JsonResponse({"error": "Inicia sesion"}, status=401)
    try:
        return JsonResponse(load_monthly_profitability())
    except (DashboardError, ValueError):
        return JsonResponse(
            {"error": "No se pudo consultar rentabilidad mensual"},
            status=502,
        )


@require_GET
@period_view
def costos_detalle(request: HttpRequest) -> HttpResponse:
    """Muestra costos, estados y personas con sus bandas y tarifas."""
    if request.GET.get("vista") != "proyectos":
        from apps.portal.pages import margenes

        return margenes(request)
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())
    from apps.portal.services.return_navigation import account_back_url

    account = request.GET.get("nombre", "").strip()
    back = account_back_url(account)
    navigation = return_context(request, back, account or "Business Overview")
    return render(
        request,
        "portal/costos_detalle.html",
        {
            "active": "ejecutiva",
            "loaded_at": timezone.localtime(),
            "cost_account": account,
            "cost_back": navigation["back_url"],
            "cost_back_label": navigation["back_label"],
            "executive_label": period.label
            if (period := executive_period())
            else "2026",
        },
    )


@require_GET
@period_view
def cuentas_rentabilidad(request: HttpRequest) -> HttpResponse:
    """Devuelve la rentabilidad por cuenta."""
    from django.http import JsonResponse

    from apps.portal.services.account_profitability import (
        load_account_profitability,
    )

    if _needs_login(request):
        return JsonResponse({"error": "Inicia sesion"}, status=401)
    try:
        return JsonResponse(
            load_account_profitability(
                refresh=request.GET.get("actualizar") == "1"
            )
        )
    except Exception:  # noqa: BLE001
        return JsonResponse(
            {"error": "No se pudo consultar rentabilidad por cuenta"},
            status=502,
        )


@require_GET
@period_view
def operaciones_ejecutiva(request: HttpRequest) -> HttpResponse:
    """Resume Operations para la vista ejecutiva."""
    from django.http import JsonResponse

    from apps.portal.services.executive_operations import (
        calculate_burn,
        operations_summary,
    )

    if _needs_login(request):
        return JsonResponse({"error": "Inicia sesion"}, status=401)
    try:
        pid = request.GET.get("id")
        return JsonResponse(
            calculate_burn(pid) if pid else operations_summary()
        )
    except Exception:  # noqa: BLE001
        return JsonResponse(
            {"error": "No se pudo completar la consulta de Operations"},
            status=502,
        )


@require_GET
@period_view
def todas_cuentas(request: HttpRequest) -> HttpResponse:
    """Full 2026 financial account audit, including intermediate and pending."""
    if _needs_login(request):
        return redirect_to_login(request.get_full_path())
    from apps.portal.services.account_profitability import (
        load_account_profitability,
    )

    try:
        data = load_account_profitability()
        context = {
            "active": "ejecutiva",
            "accounts": data["accounts"],
            "year": data["year"],
        }
    except Exception:  # noqa: BLE001
        context = {
            "active": "ejecutiva",
            "accounts": [],
            "year": 2026,
            "error": "No se pudo consultar Google Sheets. Intenta nuevamente.",
        }
    context["executive_query"] = executive_query_string()
    period = executive_period()
    context["executive_label"] = period.label if period else ""
    context["loaded_at"] = timezone.localtime()
    return render(request, "portal/todas_cuentas.html", context)


@require_http_methods(["GET", "POST"])
def acuerdos_ejecutivos(request: HttpRequest) -> HttpResponse:
    """Lista y guarda acuerdos segun la capacidad y el alcance de la persona."""
    from django.http import JsonResponse

    from apps.portal.services import agreements

    if _needs_login(request):
        return JsonResponse({"error": "Inicia sesion"}, status=401)
    access = resolve(request)
    writing = request.method == "POST"
    if not agreements.may(access, write=writing):
        return JsonResponse(
            {"error": "No tienes acceso a esta información."}, status=403
        )
    scope = access.scope
    locked = request.GET.get("account", "").strip()
    if writing:
        instance = None
        if request.POST.get("id"):
            instance = agreements.find_agreement(scope, request.POST["id"])
            if instance is None:
                return JsonResponse(
                    {"error": "El registro no existe"}, status=404
                )
        if (
            locked
            and instance
            and (
                agreements.agreement_account_key(instance.account)
                != agreements.agreement_account_key(locked)
            )
        ):
            return JsonResponse(
                {"error": "El registro no pertenece a esta cuenta"}, status=404
            )
        status_change = request.POST.get("action") == "status"
        try:
            if status_change:
                if instance is None:
                    return JsonResponse(
                        {"error": "Indica el registro a actualizar"},
                        status=400,
                    )
                agreements.change_status(
                    instance, request.POST.get("status", "")
                )
            else:
                values = request.POST.copy()
                if locked:
                    values["account"] = locked
                agreements.save_agreement(scope, values, instance)
        except agreements.InvalidStatusError:
            return JsonResponse({"error": "Estado no valido"}, status=400)
        except agreements.InvalidAgreementError as error:
            return JsonResponse({"errors": error.errors}, status=400)
        except agreements.OutOfScopeError:
            return JsonResponse(
                {"error": "No tienes acceso a esa cuenta."}, status=403
            )
    rows = agreements.visible_agreements(
        scope, locked, request.GET.get("pending_only") == "1"
    )
    return JsonResponse(
        {"items": rows, "can_edit": agreements.may(access, write=True)}
    )


@require_GET
@period_view
def comercial_ejecutiva(request: HttpRequest) -> HttpResponse:
    """Devuelve el resumen comercial ejecutivo."""
    from django.http import JsonResponse

    from apps.portal.services.executive_commercial import commercial_summary

    if _needs_login(request):
        return JsonResponse({"error": "Inicia sesion"}, status=401)
    try:
        return JsonResponse(commercial_summary())
    except Exception:  # noqa: BLE001
        return JsonResponse(
            {"error": "No se pudo consultar la fuente comercial"}, status=502
        )
