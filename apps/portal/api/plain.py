"""Convierte los objetos de las pantallas a datos JSON con sus nombres."""

from dataclasses import fields, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

"""BKD.120.025 - Datos planos
Las pantallas ya arman sus cifras con dataclasses de portal/schemas.py, cuyos
campos tienen nombre. Este convertidor los entrega tal cual: fechas ISO,
numeros como numeros, tuplas como listas. Un tipo que no conoce es un error:
nunca se serializa algo a ciegas.
"""


def plain(value: Any) -> Any:
    """Valor JSON equivalente a `value`."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if is_dataclass(value) and not isinstance(value, type):
        return {f.name: plain(getattr(value, f.name)) for f in fields(value)}
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [plain(item) for item in value]
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    raise TypeError(f"No se puede convertir {type(value).__name__} a JSON.")
