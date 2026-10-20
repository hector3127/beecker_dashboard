from decimal import Decimal, InvalidOperation, ROUND_DOWN
from django import template

register = template.Library()


@register.filter
def money_k(value):
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
def money_dollar(value):
    formatted = money_k(value)
    if formatted == "Pendiente":
        return formatted
    return (
        "-$" + formatted[1:] if formatted.startswith("-") else "$" + formatted
    )


@register.filter
def hours_number(value):
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
