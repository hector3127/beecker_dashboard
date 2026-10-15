"""Vista que sirve el panel original con el adaptador de Django."""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
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

    project_id = request.GET.get("proyecto", "").strip()
    if project_id:
        return redirect("portal:proyecto_detalle", project_id=project_id)

    account = request.GET.get("cuenta", "").strip()
    if account:
        from urllib.parse import urlencode

        from django.urls import reverse

        from apps.portal.services.slugs import build_slug

        return redirect(
            reverse("portal:cuenta", args=[build_slug(account)])
            + "?"
            + urlencode({"nombre": account})
        )

    return redirect("portal:facturabilidad_area")
