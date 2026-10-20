"""Explicit local return destinations for nested portal details."""

from urllib.parse import urlsplit, parse_qs, unquote
from django.urls import resolve, Resolver404

LABELS = {
    "portal:ejecutiva": "Business Overview",
    "portal:todas_cuentas": "Todas las cuentas",
    "portal:operativa": "Operativa",
    "portal:comercial": "Comercial",
    "portal:cuenta": "la cuenta",
    "portal:delivery_manager": "Delivery Manager",
    "portal:costos_detalle": "Detalle de costos",
    "portal:proyecto_detalle": "el proyecto",
    "portal:eva1": "EVA 1",
    "portal:eva3": "EVA 3",
    "portal:eva4": "EVA 4",
}


def return_context(request, default_url, default_label):
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
