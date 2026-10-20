"""Filtros de numeros ejecutivos para las plantillas del portal."""

from decimal import ROUND_DOWN, Decimal, InvalidOperation
from typing import Any

from django import template

register = template.Library()


@register.filter
def money_k(value: Any) -> Any:
    """Formatea dinero con K, M o B, truncando sin redondear."""
    if value is None or value == "":
        return "Pendiente"
    try:
        amount = Decimal(str(value))
        if not amount.is_finite():
            return "Pendiente"
        magnitude = abs(amount)
        unit, suffix = (
            (Decimal("1000000000"), "B")
            if magnitude >= 1000000000
            else (Decimal("1000000"), "M")
            if magnitude >= 1000000
            else (Decimal("1000"), "K")
            if magnitude >= 1000
            else (Decimal("1"), "")
        )
        precision = Decimal("0.01") if unit >= 1000000 else Decimal("1")
        amount = (amount / unit).quantize(precision, rounding=ROUND_DOWN)
        formatted = format(amount, ",f")
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        return formatted + suffix
    except (InvalidOperation, ValueError, TypeError):
        return "Pendiente"


@register.filter
def money_dollar(value: Any) -> Any:
    """Formatea dinero en dolares con las mismas abreviaturas."""
    formatted = money_k(value)
    if formatted == "Pendiente":
        return formatted
    return (
        "-$" + formatted[1:] if formatted.startswith("-") else "$" + formatted
    )


@register.filter
def hours_number(value: Any) -> Any:
    """Formatea horas con miles y sin decimales sobrantes."""
    try:
        number = Decimal(str(value))
        return (
            format(
                number.quantize(Decimal("0.01"), rounding=ROUND_DOWN), ",.2f"
            )
            .rstrip("0")
            .rstrip(".")
            if number.is_finite()
            else "Pendiente"
        )
    except (InvalidOperation, ValueError, TypeError):
        return "Pendiente"
