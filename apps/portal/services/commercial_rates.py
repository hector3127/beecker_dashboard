"""Cotizacion USD del mes actual; no transmite datos del backlog."""

import math
from datetime import UTC, datetime
from typing import Any

import requests
from django.core.cache import cache


def validate_rates(payload: Any, today: Any) -> Any:
    """Valida las cotizaciones y su fecha de actualizacion."""
    if payload.get("result") != "success" or payload.get("base_code") != "USD":
        raise ValueError("Respuesta de tipo de cambio invalida.")
    updated = datetime.fromtimestamp(
        float(payload["time_last_update_unix"]), UTC
    ).date()
    if (updated.year, updated.month) != (
        today.year,
        today.month,
    ) or updated > today:
        raise ValueError(
            "La cotizacion disponible no corresponde al mes actual."
        )
    rates = {
        code: float(value)
        for code, value in payload["rates"].items()
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value > 0
    }
    rates["USD"] = 1.0
    return {"rates": rates, "date": updated.isoformat()}


def load_rates(today: Any) -> Any:
    """Carga cotizaciones USD del mes con cache corta."""
    key = "commercial:usd-rates:" + today.isoformat()
    value = cache.get(key)
    if value:
        return value
    response = requests.get(
        "https://open.er-api.com/v6/latest/USD", timeout=(5, 15)
    )
    response.raise_for_status()
    value = validate_rates(response.json(), today)
    cache.set(key, value, 3600)
    return value


def convert_usd(amount: Any, currency: Any, rates: Any) -> Any:
    """Convierte un importe a USD si existe una cotizacion."""
    if amount is None:
        return None
    code = currency.strip().upper()
    if code == "USD":
        return amount
    rate = rates.get(code)
    return amount / rate if rate and rate > 0 else None
