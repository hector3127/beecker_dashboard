"""Executive commercial figures from the same source and FX as Comercial."""

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.cache import cache
from django.http import QueryDict
from django.utils import timezone

from apps.portal.services.commercial_view import build_commercial_context
from apps.portal.services.executive_period import bounds
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.utils.dates import to_datetime
from core.utils.source_refresh import force_sources


def future_delivery(reader: Any = None, today: Any = None) -> dict[str, Any]:
    """Revenue Confirmed futuro por fecha G e importe H, dentro del corte."""
    today = today or timezone.localdate()
    start, end = bounds()
    rows = (reader or build_sheet_repository()).read_values("DataRevenue")
    if not rows:
        raise ValueError(
            "DataRevenue no disponible para calcular revenue futuro"
        )
    total = Decimal("0")
    count = 0
    for row in rows[1:]:
        if len(row) < 8 or str(row[0]).strip().casefold() != "confirmed":
            continue
        if any(
            str(cell).strip().casefold()
            in {"total", "grand total", "total general", "subtotal"}
            for cell in row[:7]
        ):
            continue
        moment = to_datetime(row[6])
        if not moment or not (
            start <= moment.date() <= end and moment.date() > today
        ):
            continue
        try:
            amount = Decimal(
                str(row[7]).replace(",", "").replace("$", "").strip()
            )
        except InvalidOperation:
            continue
        if not amount.is_finite():
            continue
        total += amount
        count += 1
    return {
        "delivery": str(total.quantize(Decimal("0.01"))),
        "delivery_count": count,
        "delivery_as_of": today.isoformat(),
        "delivery_rule": "confirmed_future_g_v1",
        "delivery_note": (
            "Revenue futuro Confirmed según DataRevenue G; importe H del "
            "periodo seleccionado"
        ),
    }


def commercial_summary() -> dict[str, Any]:
    """Resume ventas ganadas y oportunidades del periodo en USD."""
    start, end = bounds()
    key = f"portal:executive-commercial:v3:{timezone.localdate()}:{start}:{end}"
    saved: dict[str, Any] | None = cache.get(key)
    if saved is not None and not force_sources.get():
        return saved
    params = QueryDict(mutable=True)
    params.update({"desde": start.isoformat(), "hasta": end.isoformat()})
    data = build_commercial_context(params)
    if data.get("error"):
        raise ValueError(data["error"])
    unique_params = params.copy()
    unique_params["unique_opportunities"] = "1"
    unique_data = build_commercial_context(unique_params)
    if unique_data.get("error"):
        raise ValueError(unique_data["error"])
    result = {
        "won": data["won_usd"] if data["won_count"] else 0,
        "open": unique_data["open_usd"] if unique_data["open_count"] else 0,
        "won_count": data["won_count"],
        "open_count": unique_data["open_count"],
        "open_duplicates_removed": unique_data.get("duplicates_removed", 0),
        "open_rule": "unique_open_close_date_v1",
        "open_note": (
            "Oportunidades abiertas únicas de Backlog_Proyectos; fecha de "
            "cierre dentro del periodo seleccionado"
        ),
        "pending_usd": data["pending_usd"],
        "delivery": None,
        "delivery_note": "Sin saldo por ejecutar en la fuente comercial",
        "source": "Backlog_Proyectos",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "fx_date": data["fx_date"],
        "fx_error": data["fx_error"],
    }
    try:
        result.update(future_delivery())
    except (DashboardError, ValueError) as error:
        result["delivery_note"] = (
            "No se pudo consultar el revenue futuro de Finanzas"
        )
        result["delivery_error"] = str(error)
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
