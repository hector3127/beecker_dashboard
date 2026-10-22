"""Paginas del frontend nuevo: solo entregan la plantilla de frontend/."""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

from apps.access.checks import require_capability, scope_for
from apps.portal import views
from apps.portal.services.eva4 import anterior_disponible, month_picker
from apps.portal.services.executive_period import bounds, period_view
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
@require_capability("view_costs")
@period_view
def margenes(request: HttpRequest) -> HttpResponse:
    """Comparativa de margenes: el JS pide los datos a la API."""
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    account = request.GET.get("nombre", "").strip()
    if account and not scope_for(request).allows_account(account):
        raise Http404("No existe esa cuenta.")
    start, end = bounds()
    navigation = return_context(
        request, account_back_url(account), account or "Business Overview"
    )
    return render(
        request,
        "pages/margenes.html",
        {
            **navigation,
            "active": "ejecutiva",
            "account": account,
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    )


@require_GET
def cuenta(request: HttpRequest, slug: str) -> HttpResponse:
    """Cuenta: el JS pinta los datos de la API.

    Mientras se completa la migracion, ?vista=nueva abre la pagina nueva y
    sin ella sigue la anterior (views.cuenta).
    """
    if request.GET.get("vista") != "nueva" or request.GET.get("bloque"):
        return views.cuenta(request, slug)
    if _login_needed(request):
        return redirect_to_login(request.get_full_path())
    client = views.authorized_account(request, slug)
    if isinstance(client, HttpResponse):
        return client
    navigation = return_context(
        request, reverse("portal:operativa"), "Operativa"
    )
    return render(
        request,
        "pages/cuenta.html",
        {**navigation, "active": "operativa", "client": client},
    )
