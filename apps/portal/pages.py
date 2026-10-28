"""Paginas del frontend nuevo: solo entregan la plantilla de frontend/."""

from typing import Any
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from apps.access.checks import require_capability, scope_for
from apps.portal import views
from apps.portal.services.eva4 import month_picker
from apps.portal.services.executive_period import (
    period_view,
)
from apps.portal.services.executive_period import (
    query_string as executive_query_string,
)
from apps.portal.services.return_navigation import (
    account_back_url,
    return_context,
)

"""BKD.120.014 - Paginas del frontend
Cada pagina valida el acceso y renderiza su plantilla; los datos los pide
el JS a /api/v1/. Aqui no hay calculos.
"""


def _login_needed(request: HttpRequest) -> bool:
    """Si el portal exige sesion y la persona no la tiene."""
    return bool(
        settings.PORTAL_LOGIN_REQUIRED and not request.user.is_authenticated
    )


@require_GET
@ensure_csrf_cookie  # el JS lee la cookie para firmar sus POST
def guia(request: HttpRequest) -> HttpResponse:
    """Muestra los componentes y estados del frontend nuevo."""
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    return render(request, "pages/guia.html", {"active": ""})


@require_GET
@require_capability("view_operations")
def eva4(request: HttpRequest) -> HttpResponse:
    """EVA-04: el JS pide los datos a /api/v1/screens/eva4/."""
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    return render(
        request,
        "pages/eva4.html",
        {
            "active": "operativa",
            "loaded_at": timezone.localtime(),
            "picker": month_picker(
                request.GET.get("mes"), timezone.localdate()
            ),
        },
    )


@require_GET
@require_capability("view_operations")
def operativa(request: HttpRequest) -> HttpResponse:
    """Operativa: el JS pinta el ultimo corte y refresca por bloques."""
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    return render(request, "pages/operativa.html", {"active": "operativa"})


@require_GET
@require_capability("view_operations")
def account_hours(request: HttpRequest, slug: str) -> HttpResponse:
    """Monthly account hours in the modular frontend, with account return."""
    from urllib.parse import urlencode

    from django.urls import reverse

    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    client = views.authorized_account(request, slug)
    if isinstance(client, HttpResponse):
        return client
    back = (
        reverse("portal:cuenta", kwargs={"slug": slug})
        + "?"
        + urlencode({"nombre": client})
    )
    return render(
        request,
        "pages/account_hours.html",
        {
            "active": "operativa",
            "client": client,
            "year": timezone.localdate().year,
            "today": timezone.localdate().isoformat(),
            **return_context(request, back, client),
        },
    )


@require_GET
@ensure_csrf_cookie  # el JS firma el POST de actualizar costos
@period_view
@require_capability("view_costs")
def margins(request: HttpRequest) -> HttpResponse:
    """Margen vendido vs. real: el JS pide las cifras a la API."""
    from urllib.parse import urlencode

    from django.urls import reverse

    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    account = request.GET.get("nombre", "").strip()
    if account and not scope_for(request).allows_account(account):
        raise Http404("No existe esa cuenta.")
    costs = {"vista": "proyectos"}
    if account:
        costs["nombre"] = account
    query = urlencode(costs)
    if executive_query_string():
        query += "&" + executive_query_string()
    return render(
        request,
        "pages/margins.html",
        {
            "active": "ejecutiva",
            "account_filter": account,
            "costs_url": reverse("portal:costos_detalle") + "?" + query,
            **return_context(
                request,
                account_back_url(account),
                account or "Business Overview",
            ),
        },
    )


@require_GET
@require_capability("view_operations")
def delivery_manager(request: HttpRequest, slug: str) -> HttpResponse:
    """Delivery Manager: el JS pide sus datos por pasos a la API."""
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    name = (
        request.GET.get("nombre", "").strip() or slug.replace("-", " ").title()
    )
    return render(
        request,
        "pages/delivery_manager.html",
        {
            "active": "operativa",
            "loaded_at": timezone.localtime(),
            "slug": slug,
            "dm_name": name,
            "dm_initials": "".join(w[0] for w in name.split()[:2]).upper(),
        },
    )


@require_GET
@ensure_csrf_cookie  # el JS firma los cambios de acuerdos
@period_view
def account(request: HttpRequest, slug: str) -> HttpResponse:
    """Cuenta: el JS pide el resumen, las horas y las finanzas a la API."""
    from django.urls import reverse
    from django.utils.text import slugify

    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    client = views.authorized_account(request, slug)
    if isinstance(client, HttpResponse):
        return client
    name = quote(client, safe="/")
    back = quote(request.get_full_path(), safe="/")
    margins = (
        f"{reverse('portal:oportunidades_financieras')}"
        f"?nombre={name}&volver={back}"
    )
    if executive_query_string():
        margins += "&" + executive_query_string()
    hours = (
        f"{reverse('portal:cuenta_horas', kwargs={'slug': slugify(client)})}"
        f"?nombre={name}&volver={back}"
    )
    return render(
        request,
        "pages/account.html",
        {
            "active": "operativa",
            "loaded_at": timezone.localtime(),
            "client": client,
            "margins_url": margins,
            "hours_url": hours,
            **return_context(request, reverse("portal:operativa"), "Operativa"),
        },
    )


@require_GET
def dictionary(request: HttpRequest) -> HttpResponse:
    """Diccionario de datos: el JS pide las definiciones a la API."""
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    return render(request, "pages/dictionary.html", {"active": "ejecutiva"})


@require_GET
@require_capability("view_operations", whole_portfolio=True)
def kpis_dm(request: HttpRequest) -> HttpResponse:
    """KPIs de Delivery Managers: el JS pide las cifras a la API."""
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    return render(
        request,
        "pages/kpis_dm.html",
        {"active": "operativa", "loaded_at": timezone.localtime()},
    )


@require_GET
@ensure_csrf_cookie  # el JS firma la actualizacion del corte y los acuerdos
@period_view
@require_capability("view_executive")
def executive(request: HttpRequest) -> HttpResponse:
    """Business Overview: el JS pide el corte preparado a la API.

    Si el corte falta, la pagina pide prepararlo en segundo plano (como antes).
    """
    from apps.portal.services.data_dictionary import glossary_groups
    from apps.portal.services.executive_operations import (
        cached_operations_snapshot,
    )
    from apps.portal.services.executive_period import current, parse
    from apps.portal.services.executive_refresh import request_refresh
    from apps.portal.services.financial_cache import cached_financial_snapshot

    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    financial = cached_financial_snapshot()
    operations = cached_operations_snapshot()
    chosen = current() or parse(
        {"periodo": "anio", "anio": str(timezone.localdate().year)}
    )
    if (
        not financial
        or not operations
        or not financial.get("commercial")
        or request.GET.get("actualizar") == "1"
    ) and not getattr(request, "portal_warmer", False):
        request_refresh()
    return render(
        request,
        "pages/executive.html",
        {
            "active": "ejecutiva",
            "glossary": glossary_groups(),
            "executive_selected": chosen,
            "executive_query": executive_query_string(),
            "executive_year": chosen.start.year,
            "executive_label": chosen.label,
        },
    )


@require_GET
@require_capability("view_commercial", whole_portfolio=True)
def commercial(request: HttpRequest) -> HttpResponse:
    """Comercial: la plantilla modular pinta el contexto de la vista."""
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    return views.comercial_response(request, "pages/commercial.html")


def _current(
    request: HttpRequest, view: Any, template: str, *args: Any
) -> HttpResponse:
    """Sirve solo la plantilla vigente con el contexto y permisos existentes."""
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    request.portal_template = template  # type: ignore[attr-defined]
    return view(request, *args)  # type: ignore[no-any-return]


@require_GET
def all_accounts(request: HttpRequest) -> HttpResponse:
    """Todas las cuentas: auditoria financiera del año."""
    return _current(request, views.todas_cuentas, "pages/all_accounts.html")


@require_GET
@require_capability("view_costs")
def costs(request: HttpRequest) -> HttpResponse:
    """Detalle de costos por proyecto (o la comparativa de margenes).

    Aqui ?vista= elige entre proyectos y margenes.
    """
    scope = scope_for(request)
    named = request.GET.get("nombre", "").strip()
    if named and not scope.allows_account(named):
        raise Http404("No existe esa cuenta.")
    if not named and not scope.unrestricted:
        raise PermissionDenied  # el listado completo es del portafolio entero
    if request.GET.get("vista") != "proyectos":
        return margins(request)
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    return _current(request, views.costos_detalle, "pages/costs.html")


@require_GET
def investment(request: HttpRequest) -> HttpResponse:
    """Inversion operativa y comercial del mes."""
    return _current(request, views.inversion, "pages/investment.html")


@require_GET
def capacity(request: HttpRequest) -> HttpResponse:
    """Asignaciones mensuales con los mismos filtros, calculos y CSV."""
    return _current(request, views.capacidad_instalada, "pages/capacity.html")


@require_GET
@ensure_csrf_cookie
@require_capability("view_operations", whole_portfolio=True)
def capacity_daily(request: HttpRequest) -> HttpResponse:
    """Capacidad diaria modular; el JS lee las asignaciones por API."""
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    return render(request, "pages/capacity_daily.html", {"active": "operativa"})


@require_GET
def billability(request: HttpRequest) -> HttpResponse:
    """Facturabilidad modular con los datos y permisos originales."""
    return _current(request, views.facturabilidad, "pages/billability.html")


@require_GET
def billability_specialty(request: HttpRequest) -> HttpResponse:
    """Facturabilidad modular con los datos y permisos originales."""
    return _current(
        request,
        views.facturabilidad_especialidad,
        "pages/billability_specialty.html",
    )


@require_GET
def billability_resource(request: HttpRequest) -> HttpResponse:
    """Facturabilidad modular con los datos y permisos originales."""
    return _current(
        request, views.facturabilidad_recurso, "pages/billability_resource.html"
    )


@require_GET
def billability_area(request: HttpRequest) -> HttpResponse:
    """GSE por area con transporte API y el mismo permiso de portafolio."""
    return _current(
        request, views.facturabilidad_area, "pages/billability_area.html"
    )


@require_GET
@ensure_csrf_cookie
def eva1(request: HttpRequest) -> HttpResponse:
    """Pantalla EVA modular con el contexto y acceso originales."""
    return _current(request, views.eva1, "pages/eva1.html")


@require_GET
def eva2(request: HttpRequest) -> HttpResponse:
    """Pantalla EVA modular con el contexto y acceso originales."""
    return _current(request, views.eva2, "pages/eva2.html")


@require_GET
def eva3(request: HttpRequest) -> HttpResponse:
    """Pantalla EVA modular con el contexto y acceso originales."""
    return _current(request, views.eva3, "pages/eva3.html")


@require_GET
def eva1_cerrados(request: HttpRequest) -> HttpResponse:
    """Fragmento vigente con la respuesta de acceso original."""
    request.portal_template = "partials/eva_closed.html"  # type: ignore[attr-defined]
    return views.eva1_cerrados(request)


@require_GET
def eva3_cerrados(request: HttpRequest) -> HttpResponse:
    """Fragmento vigente con la respuesta de acceso original."""
    request.portal_template = "partials/eva3_closed.html"  # type: ignore[attr-defined]
    return views.eva3_cerrados(request)


@require_GET
def project(request: HttpRequest, project_id: str) -> HttpResponse:
    """Proyecto simple con los mismos datos, calculos y alcance por cuenta."""
    return _current(request, views.proyecto, "pages/project.html", project_id)


@require_GET
@ensure_csrf_cookie  # el JS firma las escrituras del proyecto
@require_capability("view_operations")
def project_detail(request: HttpRequest, project_id: str) -> HttpResponse:
    """Detalle del proyecto: el JS pide todo a la API."""
    from django.urls import reverse

    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    views.ensure_project_visible(request, project_id)
    return render(
        request,
        "pages/project_detail.html",
        {
            **return_context(request, reverse("portal:operativa"), "Operativa"),
            "active": "operativa",
            "project_id": project_id,
            "project_context": {"id": project_id},
        },
    )
