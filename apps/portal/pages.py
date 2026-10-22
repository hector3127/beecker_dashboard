"""Paginas del frontend nuevo: solo entregan la plantilla de frontend/."""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

"""BKD.120.014 - Paginas del frontend
Cada pagina valida el acceso y renderiza su plantilla; los datos los pide
el JS a /api/v1/. Aqui no hay calculos.
"""


@require_GET
@ensure_csrf_cookie  # el JS lee la cookie para firmar sus POST
def guia(request: HttpRequest) -> HttpResponse:
    """Muestra los componentes y estados del frontend nuevo."""
    if settings.PORTAL_LOGIN_REQUIRED and not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    return render(request, "pages/guia.html", {"active": ""})
