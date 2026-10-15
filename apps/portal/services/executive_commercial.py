"""Executive commercial figures from the same source and FX as Comercial."""

from typing import Any

from django.core.cache import cache
from django.http import QueryDict

from apps.portal.services.commercial_view import build_commercial_context
from apps.portal.services.executive_period import bounds


def commercial_summary() -> dict[str, Any]:
    """Resume ventas ganadas y oportunidades del periodo en USD."""
    start, end = bounds()
    key = f"portal:executive-commercial:v1:{start}:{end}"
    saved = cache.get(key)
    if saved is not None:
        return saved
    params = QueryDict(mutable=True)
    params.update({"desde": start.isoformat(), "hasta": end.isoformat()})
    data = build_commercial_context(params)
    if data.get("error"):
        raise ValueError(data["error"])
    result = {
        "won": data["won_usd"] if data["won_count"] else 0,
        "open": data["open_usd"] if data["open_count"] else 0,
        "won_count": data["won_count"],
        "open_count": data["open_count"],
        "pending_usd": data["pending_usd"],
        "delivery": None,
        "delivery_note": "Sin saldo por ejecutar en la fuente comercial",
        "source": "Backlog_Proyectos",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "fx_date": data["fx_date"],
        "fx_error": data["fx_error"],
    }
    cache.set(key, result, 300)
    return result


def warm_commercial_summary() -> dict[str, Any]:
    """Incluye Comercial real en la precarga financiera del mismo periodo."""
    from apps.portal.services.financial_cache import (
        cached_financial_snapshot,
        snapshot_key,
    )

    summary = commercial_summary()
    snapshot = {**cached_financial_snapshot(), "commercial": summary}
    cache.set(snapshot_key(), snapshot, 86400)
    return {"ok": True, "error": ""}
