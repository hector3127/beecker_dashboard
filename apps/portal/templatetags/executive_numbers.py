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
        suffix = "K" if abs(amount) >= 1000 else ""
        amount = amount / 1000 if suffix else amount
        return format(amount.quantize(Decimal("1"), rounding=ROUND_DOWN), ",.0f") + suffix
    except (InvalidOperation, ValueError, TypeError):
        return "Pendiente"
