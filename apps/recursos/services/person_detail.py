"""Detalle de horas de una persona (getDetallePersona)."""

from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from typing import Any

from apps.recursos.services.resource_records import Record
from apps.recursos.services.summary import (
    add,
    change_pct,
    pct,
    round2,
    window_hours,
)
from core.utils.js_values import js_str
from core.utils.text import get_flexible_value, normalize_name

"""BKD.090.004 - Detalle por persona
Equivale a getDetallePersona(), agruparPorPeriodo() y
obtenerProyectosAsignadosPersona(): marca registros sospechosos (dia de
mas de 10 h, registro de 4 h o mas, bloques redondos repetidos), horas
facturables y fuera de horario, y agrupa por dia, semana o mes.
"""

JsonObject = dict[str, Any]

LONG_RECORD_HOURS = 4
EXCESSIVE_DAY_HOURS = 10
ROUND_DURATIONS = (1, 2, 3, 4)
ROUND_BLOCKS_LIMIT = 3
MONTH_DAYS = 30
SUNDAY_OFFSET = 1
NAME_KEYS = ["Nombre del recurso", "Nombre_del_recurso", "Recurso", "Nombre"]


def clock(moment: Any) -> str:
    """HH:mm o vacio."""
    return moment.strftime("%H:%M") if moment else ""


def period_key(day: str, grouping: str) -> str:
    """Clave del grupo: dia, 'Semana del <domingo>' o YYYY-MM."""
    if grouping not in ("semana", "mes"):
        return day

    try:
        moment = date.fromisoformat(day)
    except ValueError:
        return "Semana del Invalid Date" if grouping == "semana" else "NaN-NaN"

    if grouping == "mes":
        return f"{moment.year}-{moment.month:02d}"

    # getDay(): domingo = 0; weekday(): lunes = 0.
    sunday = moment - timedelta(days=(moment.weekday() + SUNDAY_OFFSET) % 7)

    return f"Semana del {sunday.isoformat()}"


def group_by_period(
    rows: Sequence[JsonObject], grouping: str
) -> list[JsonObject]:
    """Horas y sospechosos por periodo (agruparPorPeriodo)."""
    groups: dict[str, JsonObject] = {}

    for row in rows:
        key = period_key(row["fecha"], grouping)
        group = groups.setdefault(
            key,
            {"periodo": key, "horas": 0.0, "sospechosos": 0},
        )
        group["horas"] += row["duracion"]

        if row["sospechoso"]:
            group["sospechosos"] += 1

    return sorted(
        (
            {**group, "horas": round2(group["horas"])}
            for group in groups.values()
        ),
        key=lambda group: group["periodo"],
    )


def suspicious_reason(
    record: Record,
    day_total: float,
    round_blocks: int,
) -> str:
    """Motivo por el que el registro es sospechoso, o vacio."""
    if day_total > EXCESSIVE_DAY_HOURS:
        return f"Día con más de {EXCESSIVE_DAY_HOURS} hrs registradas"

    if record.hours >= LONG_RECORD_HOURS:
        return f"Registro individual de {js_str(record.hours)} hrs"

    if record.hours in ROUND_DURATIONS and round_blocks >= ROUND_BLOCKS_LIMIT:
        return "Varios bloques redondos el mismo día (posible relleno)"

    return ""


def person_detail(
    person: object,
    grouping: object,
    records: Sequence[Record],
    positions: Mapping[str, str],
    today: date,
) -> JsonObject:
    """
    Detalle de una persona (getDetallePersona).

    Args:
        person: Nombre tal como aparece en Clockify.
        grouping: dia, semana o mes (dia si viene vacio).
        records: Registros de todos los proyectos.
        positions: Posicion por nombre normalizado.
        today: Fecha local de hoy.

    Returns:
        KPIs, horas por proyecto, grupos y registros marcados.
    """
    own = sorted(
        (record for record in records if record.resource == person),
        key=lambda record: record.day,
    )
    day_totals: dict[str, float] = {}
    round_blocks: dict[str, int] = {}

    for record in own:
        add(day_totals, record.day, record.hours)

        if record.hours in ROUND_DURATIONS:
            round_blocks[record.day] = round_blocks.get(record.day, 0) + 1

    billable = not_billable = outside = 0.0
    outside_alerts = unbilled_alerts = 0
    by_project: dict[str, JsonObject] = {}
    rows = []

    for record in own:
        reason = suspicious_reason(
            record,
            day_totals[record.day],
            round_blocks.get(record.day, 0),
        )
        project = by_project.setdefault(
            record.project or "Sin proyecto",
            {"facturable": 0.0, "noFacturable": 0.0},
        )

        if record.billable:
            billable += record.hours
            project["facturable"] += record.hours
        else:
            not_billable += record.hours
            project["noFacturable"] += record.hours
            unbilled_alerts += 1

        if record.outside_schedule:
            outside += record.hours
            outside_alerts += 1

        rows.append(
            {
                "proyecto": record.project,
                "descripcion": record.description,
                "fecha": record.day,
                "horaInicio": clock(record.started_at),
                "horaFin": clock(record.ended_at),
                "duracion": record.hours,
                "sospechoso": bool(reason),
                "motivo": reason,
                "fueraDeHorario": record.outside_schedule,
                "facturable": record.billable,
            },
        )

    total = sum(record.hours for record in own)
    project_hours: list[JsonObject] = sorted(
        (
            {
                "proyecto": name,
                "facturable": round2(values["facturable"]),
                "noFacturable": round2(values["noFacturable"]),
                "total": round2(values["facturable"] + values["noFacturable"]),
            }
            for name, values in by_project.items()
        ),
        key=lambda item: -item["total"],
    )

    return {
        "persona": person,
        "rol": positions.get(normalize_name(js_str(person))) or "",
        "totalHoras": round2(total),
        "horasFacturables": round2(billable),
        "pctFacturables": pct(billable, total),
        "horasNoFacturables": round2(not_billable),
        "pctNoFacturables": pct(not_billable, total),
        "horasFueraHorario": round2(outside),
        "pctFueraHorario": pct(outside, total),
        "pctCambioMensual": change_pct(
            window_hours(day_totals, today, 0, MONTH_DAYS),
            window_hours(day_totals, today, MONTH_DAYS, MONTH_DAYS),
        ),
        "horasPorProyecto": project_hours,
        "proyectosPrincipales": [
            {
                "proyecto": item["proyecto"],
                "horas": item["total"],
                "pct": pct(item["total"], total),
            }
            for item in project_hours
        ],
        "distribucionEstado": [
            {"nombre": name, "horas": round2(hours), "pct": pct(hours, total)}
            for name, hours in (
                ("Facturables", billable),
                ("No facturables", not_billable),
                ("Fuera de horario", outside),
            )
        ],
        "alertas": {
            "fueraHorario": outside_alerts,
            "sinFacturar": unbilled_alerts,
        },
        "registrosSospechosos": sum(1 for row in rows if row["sospechoso"]),
        "grupos": group_by_period(rows, str(grouping or "dia")),
        "registros": rows,
    }


def error_detail(person: object, message: str) -> JsonObject:
    """Respuesta de getDetallePersona cuando falla la carga."""
    return {
        "persona": person,
        "totalHoras": 0,
        "registrosSospechosos": 0,
        "grupos": [],
        "registros": [],
        "errorServidor": message,
    }


def assigned_projects(
    person: object,
    rows: Sequence[Mapping[str, Any]],
) -> JsonObject:
    """Proyectos asignados en Recursos (obtenerProyectosAsignadosPersona)."""
    name = normalize_name(js_str(person))
    projects = {
        js_str(get_flexible_value(row, ["Proyecto"]))
        for row in rows
        if normalize_name(get_flexible_value(row, NAME_KEYS)) == name
        and get_flexible_value(row, ["Proyecto"])
    }

    return {"ok": True, "proyectos": sorted(projects)}
