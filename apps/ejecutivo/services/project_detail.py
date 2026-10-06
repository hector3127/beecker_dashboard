"""Detalle por recurso de un proyecto: horas, costos, roles y areas."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apps.ejecutivo.services.project_milestones import safe_iso
from core.time_entries.models import TimeEntry
from core.utils.cell_types import CellValue, SheetRow
from core.utils.dates import to_datetime
from core.utils.numbers import round_half_up, round_half_up_int, to_number
from core.utils.text import get_flexible_value, normalize_name

"""BKD.040.010 - Detalle del proyecto
Equivale a getDetalleProyectoCompleto(): cruza Recursos con las horas de
Clockify del proyecto y calcula totales, horas por rol, distribucion por
area e insights.
"""

JsonObject = dict[str, Any]

STATUS_ON_TIME = "En tiempo"
STATUS_AT_RISK = "En riesgo"
STATUS_EXCEEDED = "Excedido"
AT_RISK_PCT = 90
FULL_PCT = 100
ON_TRACK_TOLERANCE = -5
NO_ROLE = "Sin rol"

# (textos del rol, area) en el orden en que se evaluan.
ROLE_CATEGORIES = (
    (("developer", "ml engineer", "arquitecto"), "Desarrollo"),
    (("tester", "code review", "qa"), "Testing"),
    (("business analy", "analista"), "Análisis"),
    (("scrum master", "pm", "project"), "Soporte"),
)
OTHER_CATEGORY = "Otros"


@dataclass(slots=True)
class ProjectDetailSources:
    """Datos ya leidos que necesita el detalle del proyecto."""

    project_rows: Sequence[SheetRow]
    resource_rows: Sequence[SheetRow]
    entries: Sequence[TimeEntry]
    band_info: Mapping[str, tuple[CellValue, float]]


def build_project_detail(
    project_id: str,
    sources: ProjectDetailSources,
    now: datetime,
) -> JsonObject:
    """
    Construye el detalle del proyecto.

    Args:
        project_id: ID interno del proyecto.
        sources: Datos ya leidos.
        now: Fecha y hora local actual.

    Returns:
        El mismo objeto que regresaba getDetalleProyectoCompleto().
    """
    project = find_project_row(sources.project_rows, project_id) or {}
    elapsed_pct = calculate_elapsed_pct(
        project.get("Fecha_Inicio"),
        project.get("Fecha_Fin_Estimada"),
        now,
    )
    rows = build_resource_rows(project_id, sources)
    totals = build_totals(rows)

    return {
        "proyecto": {
            "id": project_id,
            "nombre": project.get("Nombre") or project_id,
            "cliente": project.get("Cliente") or "",
            "estado": project.get("Estado") or "",
            "fechaInicio": safe_iso(project.get("Fecha_Inicio")),
            "fechaFin": safe_iso(project.get("Fecha_Fin_Estimada")),
            "pctTiempoTranscurrido": elapsed_pct,
        },
        "filas": rows,
        "totales": totals,
        "porRol": build_role_breakdown(rows),
        "distribucionCategoria": build_category_distribution(
            rows,
            totals["horasReales"],
        ),
        "insights": build_insights(rows, totals, elapsed_pct),
    }


def build_error_detail(project_id: str, message: str) -> JsonObject:
    """
    Construye la respuesta vacia que el original regresaba con error.

    Args:
        project_id: ID interno del proyecto.
        message: Mensaje del error.

    Returns:
        El detalle vacio con errorServidor.
    """
    return {
        "proyecto": {
            "id": project_id,
            "nombre": project_id,
            "cliente": "",
            "estado": "",
            "fechaInicio": None,
            "fechaFin": None,
            "pctTiempoTranscurrido": None,
        },
        "filas": [],
        "totales": {
            "horasEstimadas": 0,
            "horasReales": 0,
            "costoEstimado": 0,
            "costoReal": 0,
            "balance": 0,
            "pctCumplimientoHoras": 0,
            "pctCumplimientoFinanciero": 0,
        },
        "porRol": [],
        "distribucionCategoria": [],
        "insights": [],
        "errorServidor": message,
    }


def find_project_row(
    project_rows: Sequence[SheetRow],
    project_id: str,
) -> SheetRow | None:
    """
    Busca la fila del proyecto con comparacion exacta del ID.

    Args:
        project_rows: Filas de la hoja Proyectos.
        project_id: ID interno del proyecto.

    Returns:
        La fila, o None si no existe.
    """
    return next(
        (row for row in project_rows if row.get("ID_Proyecto") == project_id),
        None,
    )


def calculate_elapsed_pct(
    start_value: CellValue,
    end_value: CellValue,
    now: datetime,
) -> float | None:
    """
    Calcula el porcentaje de tiempo transcurrido del proyecto.

    Args:
        start_value: Fecha de inicio de la hoja.
        end_value: Fecha fin estimada de la hoja.
        now: Fecha y hora local actual.

    Returns:
        El porcentaje con un decimal, o None sin fechas validas.
    """
    start = to_datetime(start_value) if start_value else None
    end = to_datetime(end_value) if end_value else None

    if start is None or end is None or end <= start:
        return None

    total_seconds = (end - start).total_seconds()
    elapsed_seconds = min(
        max((now - start).total_seconds(), 0.0),
        total_seconds,
    )

    return round_half_up(elapsed_seconds / total_seconds * 100, 1)


def sum_hours_by_resource(
    entries: Sequence[TimeEntry],
) -> tuple[dict[str, float], dict[str, float]]:
    """
    Suma horas facturables y no facturables por recurso.

    Args:
        entries: Registros de Clockify del proyecto.

    Returns:
        Horas facturables y no facturables por nombre normalizado.
    """
    billable: dict[str, float] = {}
    non_billable: dict[str, float] = {}

    for entry in entries:
        key = normalize_name(entry.resource_name)
        target = billable if entry.is_billable else non_billable
        target[key] = target.get(key, 0) + entry.duration_hours

    return billable, non_billable


def build_resource_rows(
    project_id: str,
    sources: ProjectDetailSources,
) -> list[JsonObject]:
    """
    Crea una fila por asignacion de Recursos del proyecto.

    Args:
        project_id: ID interno del proyecto.
        sources: Datos ya leidos.

    Returns:
        Las filas ordenadas por horas reales de mayor a menor.
    """
    billable, non_billable = sum_hours_by_resource(sources.entries)
    rows: list[JsonObject] = []

    for assignment in sources.resource_rows:
        if get_flexible_value(assignment, ["Proyecto"]) != project_id:
            continue

        name = get_flexible_value(
            assignment,
            ["Nombre del recurso", "Nombre_del_recurso", "Recurso", "Nombre"],
        )
        position = get_flexible_value(
            assignment,
            ["Posicion", "Posición", "Rol"],
        )
        estimated_hours = to_number(
            get_flexible_value(
                assignment,
                ["Horas Estimadas", "Horas_Estimadas", "HorasEstimadas"],
            ),
        )
        key = normalize_name(name or "")
        real_hours = round_half_up(billable.get(key, 0), 2)
        band, costing_rate = sources.band_info.get(key, ("", 0.0))
        rows.append(
            {
                "posicion": position or "",
                "nombre": name or "",
                "banda": band or "",
                "costingRate": costing_rate or 0,
                "horasEstimadas": estimated_hours,
                "horasReales": real_hours,
                "horasNoFact": round_half_up(non_billable.get(key, 0), 2),
                "costoEstimado": round_half_up(
                    estimated_hours * (costing_rate or 0),
                    2,
                ),
                "costoReal": round_half_up(real_hours * (costing_rate or 0), 2),
                "balance": round_half_up(estimated_hours - real_hours, 2),
                "pctCumplimiento": (
                    round_half_up(real_hours / estimated_hours * 100, 1)
                    if estimated_hours
                    else 0
                ),
                "estado": resource_status(real_hours, estimated_hours),
            },
        )

    rows.sort(key=lambda row: -row["horasReales"])

    return rows


def resource_status(real_hours: float, estimated_hours: float) -> str:
    """
    Estado del recurso segun el consumo de sus horas estimadas.

    Args:
        real_hours: Horas facturables registradas.
        estimated_hours: Horas estimadas de la asignacion.

    Returns:
        En tiempo, En riesgo o Excedido.
    """
    if not estimated_hours:
        return STATUS_ON_TIME

    consumed_pct = real_hours / estimated_hours * 100

    if consumed_pct > FULL_PCT:
        return STATUS_EXCEEDED

    if consumed_pct >= AT_RISK_PCT:
        return STATUS_AT_RISK

    return STATUS_ON_TIME


def build_totals(rows: Sequence[JsonObject]) -> JsonObject:
    """
    Suma horas y costos de todas las filas.

    Args:
        rows: Filas por recurso.

    Returns:
        Los totales con balance y porcentajes de cumplimiento.
    """
    totals: JsonObject = {
        field: round_half_up(sum(row[field] for row in rows), 2)
        for field in (
            "horasEstimadas",
            "horasReales",
            "horasNoFact",
            "costoEstimado",
            "costoReal",
        )
    }
    totals["balance"] = round_half_up(
        totals["horasEstimadas"] - totals["horasReales"],
        2,
    )
    totals["pctCumplimientoHoras"] = (
        round_half_up(totals["horasReales"] / totals["horasEstimadas"] * 100, 1)
        if totals["horasEstimadas"]
        else 0
    )
    totals["pctCumplimientoFinanciero"] = (
        round_half_up(totals["costoReal"] / totals["costoEstimado"] * 100, 1)
        if totals["costoEstimado"]
        else 0
    )

    return totals


def build_role_breakdown(rows: Sequence[JsonObject]) -> list[JsonObject]:
    """
    Agrupa horas estimadas y reales por rol (Posicion).

    Args:
        rows: Filas por recurso.

    Returns:
        Los roles ordenados por horas estimadas de mayor a menor.
    """
    by_role: dict[str, list[float]] = {}

    for row in rows:
        role = row["posicion"] or NO_ROLE
        role_hours = by_role.setdefault(role, [0.0, 0.0])
        role_hours[0] += row["horasEstimadas"]
        role_hours[1] += row["horasReales"]

    roles: list[JsonObject] = [
        {
            "rol": role,
            "horasEstimadas": round_half_up(estimated, 2),
            "horasReales": round_half_up(real, 2),
        }
        for role, (estimated, real) in by_role.items()
    ]
    roles.sort(key=lambda role: -role["horasEstimadas"])

    return roles


def categorize_role(role: CellValue) -> str:
    """
    Clasifica un rol en un area, como categoriaPorRol().

    Args:
        role: Posicion del recurso.

    Returns:
        Desarrollo, Testing, Analisis, Soporte u Otros.
    """
    lowered_role = str(role or "").lower()

    for keywords, category in ROLE_CATEGORIES:
        if any(keyword in lowered_role for keyword in keywords):
            return category

    return OTHER_CATEGORY


def build_category_distribution(
    rows: Sequence[JsonObject],
    total_real_hours: float,
) -> list[JsonObject]:
    """
    Distribuye las horas reales por area.

    Args:
        rows: Filas por recurso.
        total_real_hours: Horas reales totales.

    Returns:
        Las areas ordenadas por horas de mayor a menor.
    """
    hours_by_category: dict[str, float] = {}

    for row in rows:
        category = categorize_role(row["posicion"])
        hours_by_category[category] = (
            hours_by_category.get(category, 0) + row["horasReales"]
        )

    categories: list[JsonObject] = [
        {
            "nombre": category,
            "horas": round_half_up(hours, 2),
            "pct": (
                round_half_up(hours / total_real_hours * 100, 1)
                if total_real_hours
                else 0
            ),
        }
        for category, hours in hours_by_category.items()
    ]
    categories.sort(key=lambda category: -category["horas"])

    return categories


def build_insights(
    rows: Sequence[JsonObject],
    totals: JsonObject,
    elapsed_pct: float | None,
) -> list[JsonObject]:
    """
    Genera los mensajes de avance, recursos sin horas y financiero.

    Args:
        rows: Filas por recurso.
        totals: Totales del proyecto.
        elapsed_pct: Porcentaje de tiempo transcurrido.

    Returns:
        Los insights con tipo, titulo y texto.
    """
    insights: list[JsonObject] = []

    if elapsed_pct is not None:
        difference = totals["pctCumplimientoHoras"] - elapsed_pct

        if difference >= ON_TRACK_TOLERANCE:
            insights.append(
                {
                    "tipo": "ok",
                    "titulo": "Buen avance",
                    "texto": "El consumo de horas va acorde al tiempo "
                    "transcurrido del proyecto.",
                },
            )
        else:
            gap = abs(round_half_up_int(difference))
            insights.append(
                {
                    "tipo": "warning",
                    "titulo": "Atención requerida",
                    "texto": f"El consumo de horas va {gap} pts por debajo "
                    "del tiempo transcurrido.",
                },
            )

    without_hours = [
        str(row["nombre"])
        for row in rows
        if row["horasReales"] == 0 and row["horasEstimadas"] > 0
    ]

    if without_hours:
        insights.append(
            {
                "tipo": "info",
                "titulo": "Oportunidad",
                "texto": ", ".join(without_hours) + " no registra horas aún. "
                "Revisar asignación o bloqueo.",
            },
        )

    financial_pct = totals["pctCumplimientoFinanciero"]
    insights.append(
        {
            "tipo": "ok" if financial_pct <= FULL_PCT else "error",
            "titulo": "Financiero",
            "texto": f"El proyecto lleva {format_js_number(financial_pct)}% "
            "del presupuesto estimado consumido.",
        },
    )

    return insights


def format_js_number(value: float) -> str:
    """
    Escribe un numero como String(x) de JavaScript (5 y no 5.0).

    Args:
        value: Numero a escribir.

    Returns:
        El texto del numero.
    """
    if float(value).is_integer():
        return str(int(value))

    return repr(float(value))
