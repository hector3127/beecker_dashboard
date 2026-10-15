"""Tarjeta Operations de Operativa: facturabilidad global por mes."""

from collections.abc import Sequence
from datetime import date

from apps.portal.constants import FACTURABILITY_TARGET_PERCENT
from apps.portal.schemas import ChartBar, MonthFacturability, OperationsSummary
from apps.portal.services.capacity import format_month

"""BKD.120.026 - Resumen de Operations
Toma la facturabilidad de enero al ultimo mes cerrado (el mes en curso
todavia no tiene todas sus horas) y la compara con la meta de 70%.
"""

CHART_LEFT = 14.0
CHART_WIDTH = 506.0
BAR_RATIO = 0.71
MAX_BAR_WIDTH = 40.0
BASELINE = 100.0
HEIGHT_PER_POINT = 0.78
MAX_PERCENT = 115.0
TEXT_GAP = 6.0
FIRST_MONTH = 1


def last_closed_month(today: date) -> str:
    """
    Ultimo mes completo; en enero se usa enero.

    Args:
        today: Fecha local de hoy.

    Returns:
        El mes YYYY-MM.
    """
    if today.month == FIRST_MONTH:
        return today.strftime("%Y-%m")

    return f"{today.year}-{today.month - 1:02d}"


def build_operations_summary(
    months: Sequence[MonthFacturability],
    month_closed: bool = True,
) -> OperationsSummary:
    """
    Arma la tarjeta con el ultimo mes y la grafica por mes.

    Args:
        months: Facturabilidad de enero al mes elegido, en orden.
        month_closed: False cuando el ultimo mes todavia esta en curso.

    Returns:
        El mes destacado, su diferencia contra la meta y las barras.
    """
    selected = months[-1] if months else None
    gap = (
        round(selected.global_percent - FACTURABILITY_TARGET_PERCENT, 2)
        if selected is not None and selected.global_percent is not None
        else None
    )

    return OperationsSummary(
        selected=selected,
        month_label=format_month(selected.month) if selected else "",
        target=FACTURABILITY_TARGET_PERCENT,
        gap=gap,
        gap_abs=abs(gap) if gap is not None else None,
        month_closed=month_closed,
        bars=build_chart_bars(months),
        errors=tuple(
            f"{item.label}: {item.error}" for item in months if item.error
        ),
    )


def build_chart_bars(
    months: Sequence[MonthFacturability],
) -> tuple[ChartBar, ...]:
    """
    Calcula la posicion de cada barra en un SVG de 520 x 126.

    Args:
        months: Facturabilidad por mes.

    Returns:
        Una barra por mes; el ultimo se marca como actual.
    """
    if not months:
        return ()

    slot = CHART_WIDTH / len(months)
    width = round(min(slot * BAR_RATIO, MAX_BAR_WIDTH), 1)
    bars = []

    for index, month in enumerate(months):
        percent = month.global_percent
        shown = min(max(percent or 0.0, 0.0), MAX_PERCENT)
        height = round(shown * HEIGHT_PER_POINT, 1)
        x = round(CHART_LEFT + index * slot + (slot - width) / 2, 1)
        bars.append(
            ChartBar(
                x=x,
                y=round(BASELINE - height, 1),
                width=width,
                height=height,
                center=round(x + width / 2, 1),
                text_y=round(BASELINE - height - TEXT_GAP, 1),
                value_text=_format_percent(percent),
                label=month.short_label,
                current=index == len(months) - 1,
                month=month.month,
                month_label=format_month(month.month),
                global_percent=month.global_percent,
                fixed_percent=month.fixed_percent,
                variable_percent=month.variable_percent,
            ),
        )

    return tuple(bars)


def _format_percent(value: float | None) -> str:
    """68% para enteros, 99.5% con un decimal; guion sin dato."""
    if value is None:
        return "—"

    rounded = round(value, 1)

    if rounded == int(rounded):
        return f"{int(rounded)}%"

    return f"{rounded}%"
