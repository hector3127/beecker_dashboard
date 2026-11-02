"""Inversión acumulada por tags y adaptadores GSE de compatibilidad."""

from collections.abc import Iterable, Mapping
from datetime import date
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
                "resource": str(item.get("recurso") or "").strip(),
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


def investment_breakdown(
    gse: Mapping[str, Any], view: InvestmentView
) -> dict[str, Any]:
    """Distribución y recursos desde los mismos registros y clasificación."""
    people: dict[tuple[str, str], list[float]] = {}
    projects: dict[tuple[str, str], dict[str, list[float]]] = {}
    for item in _detail(gse):
        kind, _ = classify_investment(item["categories"])
        if not kind:
            continue
        key = (item["resource"] or "Sin recurso", item["area"] or NO_AREA)
        values = people.setdefault(key, [0.0, 0.0])
        index = 0 if kind == "comercial" else 1
        values[index] += item["hours"]
        project = item["project"] or NO_PROJECT
        project_values = projects.setdefault(key, {}).setdefault(
            project, [0.0, 0.0]
        )
        project_values[index] += item["hours"]
    total = view.totals.total

    def share(value: float, denominator: float) -> float:
        return round(value * 100 / denominator, 1) if denominator else 0

    return {
        "areas": [
            {
                "name": r.name,
                "commercial": r.commercial,
                "operational": r.operational,
                "total": r.total,
                "share": share(r.total, total),
            }
            for r in view.by_area
        ],
        "people": [
            {
                "name": name,
                "area": area,
                "commercial": values[0],
                "operational": values[1],
                "total": sum(values),
                "projects": sorted(
                    [
                        {
                            "name": project,
                            "commercial": amounts[0],
                            "operational": amounts[1],
                            "total": sum(amounts),
                        }
                        for project, amounts in projects[(name, area)].items()
                    ],
                    key=lambda row: (-row["total"], row["name"]),
                ),
            }
            for (name, area), values in sorted(people.items())
        ],
        "commercial": [
            {
                "label": r.label,
                "hours": r.hours,
                "share": share(r.hours, view.totals.commercial),
                "width": r.width,
            }
            for r in view.commercial_by_type
        ],
        "operational": [
            {
                "label": r.label,
                "hours": r.hours,
                "share": share(r.hours, view.totals.operational),
                "width": r.width,
            }
            for r in view.operational_by_project
        ],
        "operational_share": share(view.totals.operational, total),
        "commercial_share": share(view.totals.commercial, total),
    }


def accumulated_investment_context(
    investment: Mapping[str, Any],
    today: date,
    roles: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Desglosa los registros acumulados de Operativa, sin filtro mensual."""
    from dataclasses import replace

    from apps.gse.services.cells import norm

    roles = roles or {}
    records = (
        investment.get("records", []) if investment.get("complete") else []
    )
    detail = [
        {
            "recurso": row["resource"],
            "area": roles.get(norm(row["resource"]), NO_AREA),
            "proyecto": row["project"],
            "horas": row["hours"],
            "categorias": [
                "Inversión Comercial"
                if row["category"] == "commercial"
                else "Inversión Operaciones"
            ],
        }
        for row in records
    ]
    month = today.strftime("%Y-%m")
    view = build_investment_view({"detalle": detail}, month)
    view = replace(
        view,
        label="Proyectos activos de EVA 1 y EVA 3",
        commercial_by_type=tuple(
            replace(bar, label="INV_COMERCIAL")
            for bar in view.commercial_by_type
        ),
    )
    history = []
    index = today.year * 12 + today.month - 1
    for offset in range(5, -1, -1):
        year, number = divmod(index - offset, 12)
        key = f"{year}-{number + 1:02d}"
        history.append(
            {
                "month": key,
                "label": format_month(key).split()[0][:3],
                **{
                    category: sum(
                        row["hours"]
                        for row in records
                        if row["category"] == category
                        and row.get("day")
                        and row["day"][:7] <= key
                    )
                    for category in ("commercial", "operational")
                },
                "error": "",
            }
        )
    days = [row["day"] for row in records if row.get("day")]
    return {
        "month": month,
        "investment": view,
        "investment_detail": investment_breakdown({"detalle": detail}, view),
        "investment_ready": bool(investment.get("complete")),
        "investment_project_count": investment.get("projects", 0),
        "investment_from": min(days) if days else "",
        "investment_to": max(days) if days else "",
        "investment_chart": {
            "history": history,
            "commercial": view.totals.commercial,
            "operational": view.totals.operational,
            "undated": sum(
                row["hours"] for row in records if not row.get("day")
            ),
        },
        "error": investment.get("error", ""),
    }
