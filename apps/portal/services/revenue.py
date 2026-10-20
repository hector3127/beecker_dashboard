"""Ingresos reales: suma de USD Global Adj (DataRevenue, columna H)."""

from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.cache import cache

from apps.portal.services.executive_period import (
    bounds,
    cache_suffix,
    contains,
    current,
)
from core.sheets.factory import build_sheet_repository
from core.utils.dates import to_datetime
from core.utils.source_refresh import force_sources

INVOICE_STATUSES = frozenset(
    {"invoiced", "invoiced factoring", "collected", "collected factoring"}
)

REVENUE_STATUSES = frozenset(
    {
        "confirmed",
        "invoiced",
        "invoiced factoring",
        "collected",
        "collected factoring",
    }
)


def load_revenue() -> dict[str, Any]:
    """Suma ingresos y la proporcion cobrada del ejercicio 2026."""
    cached: dict[str, Any] | None = cache.get(
        "portal:revenue:DataRevenue:H:2026:v5" + cache_suffix()
    )
    if cached is not None and not force_sources.get():
        return cached
    rows = build_sheet_repository().read_values("DataRevenue")
    total = Decimal("0")
    count = 0
    collected = Decimal("0")
    invoiced = Decimal("0")
    for row in rows[1:]:
        moment = to_datetime(row[6]) if len(row) > 6 else None
        if (
            not moment
            or not contains(moment)
            or str(row[0]).strip().casefold() not in REVENUE_STATUSES
        ):
            continue
        if len(row) < 8 or row[7] in ("", None):
            continue
        if any(
            str(cell).strip().casefold()
            in {"total", "grand total", "total general", "subtotal"}
            for cell in row[:7]
        ):
            continue
        try:
            amount = Decimal(
                str(row[7]).replace(",", "").replace("$", "").strip()
            )
        except InvalidOperation:
            continue
        if amount.is_finite():
            total += amount
            status = str(row[0]).strip().casefold()
            if status in {"collected", "collected factoring"}:
                collected += amount
                invoiced += amount
            elif status in {"invoiced", "invoiced factoring"}:
                invoiced += amount
            count += 1
    if not count and not current():
        raise ValueError("DataRevenue no contiene importes numericos en H")
    result = {
        "total": str(total.quantize(Decimal("0.01"))),
        "records": count,
        "booking_revenue": str(total.quantize(Decimal("0.01"))),
        "invoice_validation": (
            "Pendiente de validar fechas e importes mensuales con Florencia"
        ),
        "includes_factoring": True,
        "collected": str(collected.quantize(Decimal("0.01"))),
        "invoiced": str(invoiced.quantize(Decimal("0.01"))),
        "collections_percent": round(float(collected / invoiced * 100), 2)
        if invoiced
        else None,
        "source": (
            f"DataRevenue · {bounds()[0]:%d/%m/%Y} - "
            f"{bounds()[1]:%d/%m/%Y} · H (USD Global Adj)"
        ),
    }
    cache.set(
        "portal:revenue:DataRevenue:H:2026:v5" + cache_suffix(), result, 300
    )
    return result
