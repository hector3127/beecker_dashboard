"""Soporte del frontend: nonce y politica CSP, y configuracion para el JS."""

import json
import logging
import secrets
from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import resolve_url
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

"""BKD.001.006 - Soporte del frontend
Cada peticion recibe un nonce para el unico script en linea del layout (el
importmap). La politica CSP solo reporta mientras queden paginas con
scripts o estilos en linea; los avisos llegan a /csp-report/.
"""

logger = logging.getLogger("csp")

REPORT_PATH = "/csp-report/"
MAX_REPORT_BYTES = 8192
# Rutas con HTML ajeno al portal: sus avisos solo meterian ruido.
UNREPORTED_PREFIXES = ("/admin/", "/static/")


def build_policy(nonce: str) -> str:
    """Politica que cumple el layout nuevo, sin 'unsafe-inline'."""
    return "; ".join(
        [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{nonce}'",
            "style-src 'self' https://fonts.googleapis.com",
            "font-src https://fonts.gstatic.com",
            "img-src 'self' data:",
            "connect-src 'self'",
            "base-uri 'self'",
            "form-action 'self'",
            f"report-uri {REPORT_PATH}",
        ]
    )


class CspMiddleware:
    """Genera el nonce de la peticion y, si se pide, anuncia la politica."""

    def __init__(
        self, get_response: Callable[[HttpRequest], HttpResponse]
    ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Atiende la peticion y agrega la politica a la respuesta."""
        nonce = secrets.token_urlsafe(16)
        request.csp_nonce = nonce  # type: ignore[attr-defined]
        response = self.get_response(request)
        if settings.CSP_REPORT_ONLY and not request.path.startswith(
            UNREPORTED_PREFIXES
        ):
            response["Content-Security-Policy-Report-Only"] = build_policy(
                nonce
            )
        return response


def frontend_context(request: HttpRequest) -> dict[str, Any]:
    """Nonce y configuracion que el layout entrega al JS como JSON."""
    return {
        "csp_nonce": getattr(request, "csp_nonce", ""),
        "app_config": {
            "apiBase": settings.FRONTEND_API_BASE,
            "csrfCookie": settings.CSRF_COOKIE_NAME,
            "loginUrl": resolve_url(settings.LOGIN_URL),
        },
    }


@csrf_exempt
@require_POST
def csp_report(request: HttpRequest) -> HttpResponse:
    """Anota un aviso de CSP; los navegadores lo envian sin sesion."""
    if len(request.body) > MAX_REPORT_BYTES:
        return HttpResponse(status=413)
    try:
        report = json.loads(request.body or b"{}")
    except ValueError:
        return HttpResponse(status=400)
    # json.dumps evita que un aviso falso meta saltos de linea en el log.
    logger.warning("CSP: %s", json.dumps(report, ensure_ascii=False)[:600])
    return HttpResponse(status=204)
