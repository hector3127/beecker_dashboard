"""Inversion operativa y comercial con las categorias de GSE."""

from collections.abc import Iterable, Mapping
from typing import Any

from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.portal.constants import (
    COMMERCIAL_CATEGORIES,
    INVESTMENT_TOP_ITEMS,
    OPERATIONAL_CATEGORIES,
    OTHERS_LABEL,
)
from apps.portal.schemas import HoursBar, InvestmentRow, InvestmentView
from apps.portal.services.capacity import format_month

"""BKD.120.025 - Inversion operativa y comercial
Horas del mes que no se facturan a un proyecto, leidas del detalle de GSE:
- Comercial: categorias "Inversion Comercial" y "Pre-Venta".
- Operativa: categorias "Inversion Operaciones" e "Internos".
GSE no trae el Delivery Manager de cada registro, asi que se agrupa por
especialidad (ROL de Bandas/rol).
"""

NO_AREA = "Sin especialidad"
NO_PROJECT = "Sin proyecto"
COMMERCIAL_KEYS = {
    normalize_capacity_text(name) for name in COMMERCIAL_CATEGORIES
}
OPERATIONAL_KEYS = {
    normalize_capacity_text(name) for name in OPERATIONAL_CATEGORIES
}


def classify_investment(categories: Iterable[object]) -> tuple[str, str]:
    """
    Indica si un registro es inversion y de que tipo.

    Args:
        categories: Categorias del registro en GSE.

    Returns:
        ("comercial"|"operativa"|"", categoria que lo decidio).
    """
    labels = [str(item) for item in categories if item]

    for label in labels:
        if normalize_capacity_text(label) in COMMERCIAL_KEYS:
            return "comercial", label

    for label in labels:
        if normalize_capacity_text(label) in OPERATIONAL_KEYS:
            return "operativa", label

    return "", ""


def build_investment_view(
    gse: Mapping[str, Any],
    month: str,
) -> InvestmentView:
    """
    Arma la pantalla de inversion de un mes.

    Args:
        gse: Resultado de gseObtenerMes (base en Sheets).
        month: Mes YYYY-MM.

    Returns:
        Totales, filas por especialidad y barras por tipo y proyecto.
    """
    by_area: dict[str, list[float]] = {}
    by_type: dict[str, float] = {}
    by_project: dict[str, float] = {}

    for row in _detail(gse):
        kind, label = classify_investment(row["categories"])

        if not kind:
            continue

        area = by_area.setdefault(row["area"] or NO_AREA, [0.0, 0.0])

        if kind == "comercial":
            area[0] += row["hours"]
            by_type[label] = by_type.get(label, 0.0) + row["hours"]
        else:
            area[1] += row["hours"]
            project = row["project"] or NO_PROJECT
            by_project[project] = by_project.get(project, 0.0) + row["hours"]

    rows = tuple(
        sorted(
            (
                InvestmentRow(name, values[0], values[1])
                for name, values in by_area.items()
            ),
            key=lambda item: (-item.total, item.name),
        ),
    )

    return InvestmentView(
        month=month,
        label=format_month(month),
        totals=InvestmentRow(
            "Total",
            sum(item.commercial for item in rows),
            sum(item.operational for item in rows),
        ),
        by_area=rows,
        commercial_by_type=build_bars(by_type),
        operational_by_project=build_bars(by_project),
    )


def build_bars(hours: Mapping[str, float]) -> tuple[HoursBar, ...]:
    """
    Barras de mayor a menor; lo que pasa del top se junta en "Otros".

    Args:
        hours: Horas por etiqueta.

    Returns:
        Las barras con su ancho relativo a la mayor.
    """
    ordered = sorted(hours.items(), key=lambda item: (-item[1], item[0]))
    top = ordered[:INVESTMENT_TOP_ITEMS]
    rest = sum(value for _, value in ordered[INVESTMENT_TOP_ITEMS:])

    if rest > 0:
        top.append((OTHERS_LABEL, rest))

    largest = max((value for _, value in top), default=0.0)

    return tuple(
        HoursBar(
            label=label,
            hours=value,
            width=round(value * 100 / largest, 1) if largest > 0 else 0.0,
        )
        for label, value in top
    )


def _detail(gse: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Filas de detalle de GSE con sus categorias."""
    raw = gse.get("detalle")

    if not isinstance(raw, list):
        return []

    rows = []

    for item in raw:
        if not isinstance(item, dict):
            continue

        categories = item.get("categorias")
        hours = item.get("horas")
        rows.append(
            {
                "area": str(item.get("area") or "").strip(),
                "project": str(item.get("proyecto") or "").strip(),
                "categories": (
                    categories
                    if isinstance(categories, list)
                    else [item.get("categoria")]
                ),
                "hours": (
                    float(hours)
                    if isinstance(hours, int | float)
                    and not isinstance(hours, bool)
                    else 0.0
                ),
            },
        )

    return rows
