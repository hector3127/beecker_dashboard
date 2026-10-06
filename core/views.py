"""Vista que sirve el panel original con el adaptador de Django."""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET

"""BKD.006.003 - Portal
Equivale a doGet() de Codigo.gs: entrega el index del panel.
"""


@require_GET
@ensure_csrf_cookie
def portal_home(request: HttpRequest) -> HttpResponse:
    """
    Muestra el panel con el mismo HTML que servia Apps Script.

    Args:
        request: Peticion HTTP.

    Returns:
        La pagina principal del panel.
    """
    if settings.PORTAL_LOGIN_REQUIRED and not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())

    return render(request, "core/index.html")
