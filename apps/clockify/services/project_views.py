"""Rango, etapas, registros y resumen por task de un proyecto Clockify."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from apps.clockify.constants import REPORT_TIMEZONE, SHEET_MPB
from apps.clockify.services.date_ranges import ProjectDateRange
from apps.ejecutivo.services.history_stages import read_history_stages
from apps.ejecutivo.services.ixb_rules import (
    belongs_to_nomenclature,
    extract_nomenclature,
)
from apps.ejecutivo.services.project_hours import hierarchy_nomenclature
from core.exceptions import DashboardError, describe_error
from core.time_entries.models import TimeEntry
from core.utils.cell_types import CellValue, SheetRow
from core.utils.js_values import js_locale_key
from core.utils.numbers import round_half_up

"""BKD.020.015 - Vistas de un proyecto Clockify
Equivale a obtenerRangoClockifyProyecto(),
obtenerEtapasHistoricoAIProyecto(), getRegistrosClockifyProyecto() y
obtenerResumenTasksTagsClockifyProyecto() de ClockifyService.gs.
"""

JsonObject = dict[str, Any]

NO_STAGES_ERROR = (
    "No se encontraron etapas de este ID en Historico_Proyectos A:I."
)
NO_TASK = "Sin task"
ACTIVE_STATUS = "ACTIVE"
TAG_OPERATIONAL = "inv_operativa"
TAG_COMMERCIAL = "inv_comercial"
EMPTY_SUMMARY = {
    "ok": False,
    "tasks": [],
    "invOperativa": 0,
    "invComercial": 0,
    "totalHoras": 0,
}


@dataclass(frozen=True, slots=True)
class ProjectSources:
    """Hojas y reloj que usan las vistas del proyecto."""

    project_rows: Sequence[SheetRow]
    history_values: Sequence[Sequence[CellValue]]
    today: date


def day_text(day: date | None) -> str | None:
    """YYYY-MM-DD o None."""
    return day.isoformat() if day else None


def utc_midnight_iso(day: date | None) -> str | None:
    """
    Fecha como lo regresaba fechaSeguraRecursos('YYYY-MM-DD').

    new Date('YYYY-MM-DD') es medianoche UTC; toISOString() la escribe
    con milisegundos y Z.
    """
    if day is None:
        return None

    return f"{day.isoformat()}T00:00:00.000Z"


def range_dates(date_range: ProjectDateRange) -> JsonObject:
    """{ok, fechaInicio, fechaFin} (obtenerRangoClockifyProyecto)."""
    return {
        "ok": True,
        "fechaInicio": utc_midnight_iso(date_range.start_date),
        "fechaFin": utc_midnight_iso(date_range.end_date),
    }


def history_stages(
    sources: ProjectSources,
    project_id: str,
    history_range: ProjectDateRange,
) -> JsonObject | None:
    """
    Rango y etapas del historico A:I (_clockifyRangoHistoricoAI_).

    Returns:
        {fechaInicio, fechaFin, hitos, historialCompleto, suspensiones},
        o None si el ID no tiene Discovery.
    """
    stages = read_history_stages(sources.history_values, project_id)

    if stages is None or history_range.start_date is None:
        return None

    return {
        "fechaInicio": day_text(history_range.start_date),
        "fechaFin": day_text(history_range.end_date or sources.today),
        "hitos": stages.milestones,
        "historialCompleto": stages.real_history,
        "suspensiones": stages.suspensions,
    }


def stages_response(
    sources: ProjectSources,
    project_id: object,
    history_range: ProjectDateRange,
) -> JsonObject:
    """Etapas para el Gantt (obtenerEtapasHistoricoAIProyecto)."""
    clean_id = str(project_id or "").strip()
    stages = history_stages(sources, clean_id, history_range)

    if stages is None:
        return {"ok": False, "error": NO_STAGES_ERROR}

    return {"ok": True, **stages}


def range_payload(
    sources: ProjectSources,
    project_id: str,
    date_range: ProjectDateRange,
) -> JsonObject:
    """
    El objeto rango que regresaba obtenerHorasClockifyPorProyecto().

    AER/T&M traen fuente MPB; el resto trae tambien las etapas del
    historico A:I, como en el original.
    """
    dates = {
        "fechaInicio": day_text(date_range.start_date),
        "fechaFin": day_text(date_range.end_date),
    }

    if date_range.source == SHEET_MPB:
        return {**dates, "fuente": SHEET_MPB}

    return history_stages(sources, project_id, date_range) or dates


def clock_text(moment: datetime | None) -> str:
    """HH:mm en hora local, o vacio."""
    return moment.strftime("%H:%M") if moment else ""


def entry_row(entry: TimeEntry) -> JsonObject:
    """Registro con el formato de getRegistrosClockifyProyecto()."""
    day = entry.entry_date or entry.started_at

    return {
        "id": entry.entry_id,
        "fecha": day.strftime("%Y-%m-%d") if day else "",
        "recurso": entry.resource_name,
        "actividad": entry.task_name or NO_TASK,
        "descripcion": entry.description,
        "inicio": clock_text(entry.started_at),
        "fin": clock_text(entry.ended_at),
        "duracion": entry.duration_hours,
        "billable": entry.is_billable,
        "fueraHorario": None,
    }


def project_entries(
    sources: ProjectSources,
    project_value: object,
    load_hours: Callable[[str], Any],
) -> JsonObject:
    """
    Registros del proyecto respetando su nomenclatura S#/CR#.

    Equivale a getRegistrosClockifyProyecto() sobre
    obtenerHorasClockifyPorProyectoJerarquia().

    Args:
        sources: Proyectos, historico y fecha de hoy.
        project_value: ID interno del proyecto.
        load_hours: Horas del proyecto (ProjectHours).

    Returns:
        {ok, registros, rango, nomenclatura}.
    """
    project_id = str(project_value or "").strip()

    try:
        hours = load_hours(project_id)
    except DashboardError as error:
        return {"ok": False, "registros": [], "error": describe_error(error)}

    nomenclature = hierarchy_nomenclature(project_id, sources.project_rows)
    entries = [
        entry
        for entry in hours.entries
        if not nomenclature or belongs_to_nomenclature(entry, nomenclature)
    ]

    return {
        "ok": True,
        "registros": [entry_row(entry) for entry in entries],
        "rango": range_payload(sources, project_id, hours.date_range),
        "nomenclatura": nomenclature or None,
    }


def day_limit_iso(day: date, end_of_day: bool) -> str:
    """
    Inicio o fin del dia con el desfase local (_clockifyLimiteDiaISO).

    Args:
        day: Dia del rango.
        end_of_day: True para 23:59:59.

    Returns:
        Texto RFC 3339, por ejemplo 2026-01-05T00:00:00-06:00.
    """
    noon = datetime.combine(day, time(12), tzinfo=UTC)
    offset = noon.astimezone(ZoneInfo(REPORT_TIMEZONE)).strftime("%z")
    offset_text = f"{offset[:3]}:{offset[3:]}" if len(offset) == 5 else "Z"
    clock = "T23:59:59" if end_of_day else "T00:00:00"

    return f"{day.isoformat()}{clock}{offset_text}"


def unique_entries(entries: Sequence[TimeEntry]) -> list[TimeEntry]:
    """Deduplica por ID del registro (o por sus datos si no trae ID)."""
    unique: dict[str, TimeEntry] = {}

    for entry in entries:
        key = (
            f"id:{entry.entry_id}"
            if entry.entry_id
            else "|".join(
                (
                    "cmp",
                    entry.resource_name,
                    str(entry.started_at or ""),
                    str(entry.ended_at or ""),
                    entry.task_id,
                    entry.description,
                ),
            )
        )
        unique.setdefault(key, entry)

    return list(unique.values())


def allowed_tasks(
    tasks: Sequence[Mapping[str, Any]],
    nomenclature: str,
) -> list[Mapping[str, Any]]:
    """Tasks activas de la nomenclatura del ID (todas si no tiene)."""
    allowed = []

    for task in tasks:
        status = str(task.get("status") or "").upper().strip()

        if status and status != ACTIVE_STATUS:
            continue

        if nomenclature and (
            extract_nomenclature(str(task.get("name") or "")) != nomenclature
        ):
            continue

        allowed.append(task)

    return allowed


@dataclass(slots=True)
class TaskTotals:
    """Horas acumuladas del resumen."""

    total: float = 0.0
    without_task: float = 0.0
    operational: float = 0.0
    commercial: float = 0.0


def add_entry_hours(
    entry: TimeEntry,
    nomenclature: str,
    by_task: dict[str, JsonObject],
    totals: TaskTotals,
    allowed_ids: set[str],
) -> None:
    """Suma un registro si pasa los filtros de task y tag."""
    task_id = entry.task_id

    if task_id and nomenclature and task_id not in allowed_ids:
        return

    tags = [tag.strip() for tag in entry.tags]
    tag_nomenclatures = [
        found for found in map(extract_nomenclature, tags) if found
    ]

    if nomenclature and any(
        found != nomenclature for found in tag_nomenclatures
    ):
        return

    hours = entry.duration_hours

    if not hours:
        return

    totals.total += hours

    if not task_id:
        totals.without_task += hours
    else:
        by_task.setdefault(
            task_id,
            {"id": task_id, "nombre": entry.task_name or task_id, "horas": 0},
        )
        by_task[task_id]["horas"] += hours

    lower_tags = [tag.lower() for tag in tags]

    if TAG_OPERATIONAL in lower_tags:
        totals.operational += hours

    if TAG_COMMERCIAL in lower_tags:
        totals.commercial += hours


def tasks_summary(
    sources: ProjectSources,
    project_value: object,
    load_hours: Callable[[str], Any],
    load_tasks: Callable[[str], list[JsonObject]],
) -> JsonObject:
    """
    Horas por Task y tags INV_Operativa / INV_Comercial.

    Equivale a obtenerResumenTasksTagsClockifyProyecto(): parte de todos
    los registros del rango, filtra por las Tasks activas de la
    nomenclatura (o sin task) y por los tags S#/CR#.

    Args:
        sources: Proyectos, historico y fecha de hoy.
        project_value: ID interno del proyecto.
        load_hours: Horas del proyecto (ProjectHours).
        load_tasks: Tasks del proyecto de Clockify por su ID.

    Returns:
        {ok, proyectoClockify, nomenclatura, rango, rangoConsulta, tasks,
        totalHoras, invOperativa, invComercial, totalEntriesRaw,
        totalEntriesUnicas, taskIdsPermitidas}.
    """
    project_id = str(project_value or "").strip()

    try:
        hours = load_hours(project_id)
    except DashboardError as error:
        return {**EMPTY_SUMMARY, "error": describe_error(error)}

    try:
        tasks = load_tasks(hours.project_id) if hours.project_id else []
    except DashboardError:
        tasks = []

    nomenclature = hierarchy_nomenclature(project_id, sources.project_rows)
    permitted = allowed_tasks(tasks, nomenclature)
    allowed_order = list(
        dict.fromkeys(
            str(task.get("id") or "") for task in permitted if task.get("id")
        ),
    )
    allowed_ids = set(allowed_order)
    by_task: dict[str, JsonObject] = {
        str(task.get("id") or ""): {
            "id": str(task.get("id") or ""),
            "nombre": str(task.get("name") or "Sin nombre"),
            "horas": 0,
        }
        for task in permitted
    }
    totals = TaskTotals()
    unique = unique_entries(hours.entries)

    for entry in unique:
        add_entry_hours(entry, nomenclature, by_task, totals, allowed_ids)

    task_rows = sorted(
        (
            {**task, "horas": round_half_up(task["horas"], 2)}
            for task in by_task.values()
            if round_half_up(task["horas"], 2) > 0
        ),
        key=lambda task: (-task["horas"], js_locale_key(task["nombre"])),
    )

    if totals.without_task > 0:
        task_rows.append(
            {
                "id": "",
                "nombre": NO_TASK,
                "horas": round_half_up(totals.without_task, 2),
            },
        )

    date_range = hours.date_range
    has_range = date_range.start_date and date_range.end_date

    return {
        "ok": True,
        "proyectoClockify": hours.project_name,
        "nomenclatura": nomenclature or None,
        "rango": range_payload(sources, project_id, date_range),
        "rangoConsulta": (
            {
                "inicio": day_limit_iso(date_range.start_date, False),
                "fin": day_limit_iso(date_range.end_date, True),
            }
            if has_range
            else None
        ),
        "tasks": task_rows,
        "totalHoras": round_half_up(totals.total, 2),
        "invOperativa": round_half_up(totals.operational, 2),
        "invComercial": round_half_up(totals.commercial, 2),
        "totalEntriesRaw": len(hours.entries),
        "totalEntriesUnicas": len(unique),
        "taskIdsPermitidas": allowed_order,
    }
