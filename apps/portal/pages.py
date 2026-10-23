"""Paginas del frontend nuevo: solo entregan la plantilla de frontend/."""

from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from apps.access.checks import require_capability, scope_for
from apps.portal import views
from apps.portal.services.eva4 import anterior_disponible, month_picker
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
    """EVA-04: el JS pide los datos a /api/v1/screens/eva4/.

    Hasta ANTERIOR_HASTA, ?vista=anterior entrega la pantalla de antes.
    """
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    if anterior_disponible() and request.GET.get("vista") == "anterior":
        return views.eva4(request)
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
    """Margen vendido vs. real: el JS pide las cifras a la API.

    Hasta ANTERIOR_HASTA, ?vista=anterior entrega la pantalla de antes.
    """
    from urllib.parse import urlencode

    from django.urls import reverse

    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    if anterior_disponible() and request.GET.get("vista") == "anterior":
        return views.oportunidades_financieras(request)
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
    """Delivery Manager: el JS pide sus datos por pasos a la API.

    Hasta ANTERIOR_HASTA, ?vista=anterior entrega la pantalla de antes.
    """
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    if anterior_disponible() and request.GET.get("vista") == "anterior":
        return views.delivery_manager(request, slug)
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
    """Cuenta: el JS pide el resumen, las horas y las finanzas a la API.

    Hasta ANTERIOR_HASTA, ?vista=anterior entrega la pantalla de antes.
    """
    from django.urls import reverse
    from django.utils.text import slugify

    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    if anterior_disponible() and request.GET.get("vista") == "anterior":
        return views.cuenta(request, slug)
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
    """Diccionario de datos: el JS pide las definiciones a la API.

    Hasta ANTERIOR_HASTA, ?vista=anterior entrega la pantalla de antes.
    """
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    if anterior_disponible() and request.GET.get("vista") == "anterior":
        return views.diccionario_datos(request)
    return render(request, "pages/dictionary.html", {"active": "ejecutiva"})
