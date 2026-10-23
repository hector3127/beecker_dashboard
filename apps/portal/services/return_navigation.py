"""Explicit local return destinations for nested portal details."""

from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit

from django.http import HttpRequest
from django.urls import Resolver404, resolve, reverse
from django.utils.text import slugify

LABELS = {
    "portal:ejecutiva": "Business Overview",
    "portal:todas_cuentas": "Todas las cuentas",
    "portal:operativa": "Operativa",
    "portal:comercial": "Comercial",
    "portal:cuenta": "la cuenta",
    "portal:cuenta_horas": "Horas por mes",
    "portal:delivery_manager": "Delivery Manager",
    "portal:costos_detalle": "Detalle de costos",
    "portal:oportunidades_financieras": "Comparativa de márgenes",
    "portal:proyecto_detalle": "el proyecto",
    "portal:eva1": "EVA 1",
    "portal:eva3": "EVA 3",
    "portal:eva4": "EVA 4",
}


def return_context(
    request: HttpRequest, default_url: str, default_label: str
) -> dict[str, Any]:
    """Destino del boton de regreso: el de ?volver= si es local y conocido."""
    target = request.GET.get("volver", "")
    if (
        not isinstance(target, str)
        or len(target) > 8192
        or not target.startswith("/")
        or target.startswith("//")
        or "\\" in unquote(target)
        or any(ord(c) < 32 for c in target)
    ):
        return {"back_url": default_url, "back_label": default_label}
    parts = urlsplit(target)
    try:
        match = resolve(unquote(parts.path))
    except (Resolver404, ValueError):
        return {"back_url": default_url, "back_label": default_label}
    if parts.scheme or parts.netloc or match.view_name not in LABELS:
        return {"back_url": default_url, "back_label": default_label}
    label = LABELS[match.view_name]
    if match.view_name == "portal:cuenta":
        label = parse_qs(parts.query).get("nombre", ["la cuenta"])[0]
    return {"back_url": target, "back_label": label}


def account_back_url(account: str) -> str:
    """Cuenta (o Business Overview) con el periodo elegido, para regresar."""
    from urllib.parse import urlencode

    from apps.portal.services.executive_period import current, query_string

    back = (
        reverse("portal:cuenta", kwargs={"slug": slugify(account) or "cuenta"})
        + "?"
        + urlencode({"nombre": account})
        if account
        else reverse("portal:ejecutiva")
    )
    if current():
        back += ("&" if "?" in back else "?") + query_string()
    return back
