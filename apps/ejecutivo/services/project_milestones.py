"""Hitos, fases y suspensiones de un proyecto desde Historico_Proyectos."""

import functools
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from core.utils.cell_types import CellValue, SheetRow
from core.utils.dates import to_datetime, to_utc_iso
from core.utils.text import get_flexible_value, to_text

"""BKD.040.007 - Hitos del proyecto
Equivale a calcularHitosProyecto() de ProyectoEjecutivoService.gs:
- Las filas "<Fase> EST" son el plan.
- Las filas "<Fase>" (u "OP") son la ejecucion real.
- "Suspendido" y "Completed" son marcadores.
"""

JsonObject = dict[str, Any]

ESTIMATED_SUFFIX = re.compile(r"\bEST$", re.IGNORECASE)
PHASE_SUFFIX = re.compile(r"\s*(EST|OP)$", re.IGNORECASE)
MARKER_STATUS = re.compile(r"^(suspendido|completed)$", re.IGNORECASE)
SUSPENDED_MARKER = re.compile(r"^suspendido$", re.IGNORECASE)
COMPLETED_MARKER = re.compile(r"^completed$", re.IGNORECASE)

UPCOMING_WINDOW_DAYS = 60
ISO_DATE_ONLY = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)

STATE_PENDING = "Pendiente"
STATE_IN_PROGRESS = "En curso"
STATE_COMPLETED = "Completado"


@dataclass(slots=True)
class HistoryEvent:
    """Una fila del historico ya interpretada."""

    phase: str
    start: CellValue
    finish: CellValue


@dataclass(slots=True)
class ProjectMilestones:
    """Resultado equivalente a calcularHitosProyecto()."""

    milestones: list[JsonObject] = field(default_factory=list)
    upcoming: list[JsonObject] = field(default_factory=list)
    delivery_manager: str = ""
    service: str = ""
    suspension_starts: list[str | None] = field(default_factory=list)
    suspensions: list[JsonObject] = field(default_factory=list)
    full_history: list[JsonObject] = field(default_factory=list)

    def to_json(self) -> JsonObject:
        """
        Construye el JSON con las llaves originales.

        Returns:
            El diccionario de hitos.
        """
        return {
            "lista": self.milestones,
            "proximos": self.upcoming,
            "deliveryManager": self.delivery_manager,
            "servicio": self.service,
            "periodosSuspension": self.suspension_starts,
            "suspensiones": self.suspensions,
            "historialCompleto": self.full_history,
        }


def calculate_project_milestones(
    history_rows: Sequence[SheetRow],
    project_id: str,
    now: datetime,
) -> ProjectMilestones:
    """
    Calcula los hitos del proyecto a partir de Historico_Proyectos.

    Args:
        history_rows: Filas de Historico_Proyectos.
        project_id: ID del proyecto (se compara sin espacios ni
            mayusculas).
        now: Fecha y hora local actual.

    Returns:
        Los hitos, el historial y las suspensiones del proyecto.
    """
    normalized_id = to_text(project_id).strip().lower()
    rows = [
        row
        for row in history_rows
        if to_text(get_flexible_value(row, ["Project ID", "ID_Proyecto"]))
        .strip()
        .lower()
        == normalized_id
    ]

    if not rows:
        return ProjectMilestones()

    planned: list[HistoryEvent] = []
    real_history: list[HistoryEvent] = []
    markers: list[HistoryEvent] = []

    for row in rows:
        status = to_text(get_flexible_value(row, ["Status", "Fase"])).strip()
        start = get_flexible_value(row, ["Start", "Fecha_Inicio"])
        finish = get_flexible_value(row, ["Finish", "Fecha_Fin"])

        if ESTIMATED_SUFFIX.search(status):
            planned.append(HistoryEvent(strip_phase(status), start, finish))
        elif MARKER_STATUS.match(status):
            markers.append(HistoryEvent(status, start, finish))
        else:
            real_history.append(
                HistoryEvent(strip_phase(status), start, finish)
            )

    for events in (planned, real_history, markers):
        events.sort(key=functools.cmp_to_key(compare_by_start))

    is_completed = any(
        COMPLETED_MARKER.match(marker.phase) for marker in markers
    )
    last_event = find_last_event(real_history, markers)
    milestones = build_milestones(
        planned,
        real_history,
        last_event,
        is_completed,
        now.date(),
    )
    suspensions = [
        marker for marker in markers if SUSPENDED_MARKER.match(marker.phase)
    ]

    return ProjectMilestones(
        milestones=milestones,
        upcoming=select_upcoming(milestones, now),
        delivery_manager=first_text(
            rows,
            ["Delivery Manager", "Delivery Manag", "DM"],
        ),
        service=first_text(rows, ["Service", "Servicio"]),
        suspension_starts=[safe_iso(marker.start) for marker in suspensions],
        suspensions=[
            {
                "fechaInicio": safe_iso(marker.start),
                "fechaFin": safe_iso(marker.finish),
            }
            for marker in suspensions
        ],
        full_history=[
            {
                "fase": event.phase,
                "fechaInicio": safe_iso(event.start),
                "fechaFin": safe_iso(event.finish),
                "enCurso": (
                    not event.finish
                    and event is last_event
                    and not is_completed
                ),
            }
            for event in real_history
        ],
    )


def build_milestones(
    planned: Sequence[HistoryEvent],
    real_history: Sequence[HistoryEvent],
    last_event: HistoryEvent | None,
    is_completed: bool,
    today: date,
) -> list[JsonObject]:
    """
    Combina el plan con la ejecucion real de cada fase.

    Args:
        planned: Fases planeadas (EST).
        real_history: Ejecucion real ordenada por inicio.
        last_event: Ultimo evento cronologico del proyecto.
        is_completed: Indica si existe el marcador Completed.
        today: Dia local de hoy; una fase con fin hoy sigue en curso.

    Returns:
        Los hitos con fechas plan, fechas reales y estado.
    """
    milestones: list[JsonObject] = []

    for order, planned_event in enumerate(planned, start=1):
        occurrences = [
            event
            for event in real_history
            if event.phase.lower() == planned_event.phase.lower()
        ]
        last_occurrence = occurrences[-1] if occurrences else None
        state = STATE_PENDING

        if last_occurrence is not None:
            is_last_overall = last_occurrence is last_event
            state = (
                STATE_IN_PROGRESS
                if (not last_occurrence.finish and is_last_overall)
                or finishes_today_or_later(last_occurrence, today)
                else STATE_COMPLETED
            )

        if is_completed:
            state = STATE_COMPLETED

        milestones.append(
            {
                "orden": order,
                "nombre": planned_event.phase,
                "fechaInicioPlan": safe_iso(planned_event.start),
                "fechaFinPlan": safe_iso(planned_event.finish),
                "fechaInicioReal": (
                    safe_iso(last_occurrence.start) if last_occurrence else None
                ),
                "fechaFinReal": (
                    safe_iso(last_occurrence.finish)
                    if last_occurrence
                    else None
                ),
                "estado": state,
            },
        )

    return milestones


def finishes_today_or_later(event: HistoryEvent, today: date) -> bool:
    """
    Indica si la fase termina hoy o despues (todavia no se cierra).

    Args:
        event: Evento real de la fase.
        today: Dia local de hoy.

    Returns:
        True cuando el fin es hoy o una fecha futura.
    """
    finish = to_datetime(event.finish)

    return finish is not None and finish.date() >= today


def select_upcoming(
    milestones: Sequence[JsonObject],
    now: datetime,
) -> list[JsonObject]:
    """
    Elige los hitos pendientes que vencen en los proximos 60 dias.

    Args:
        milestones: Hitos del proyecto.
        now: Fecha y hora local actual.

    Returns:
        Los hitos no completados con fecha fin plan dentro de la ventana.
    """
    window_end = now + timedelta(days=UPCOMING_WINDOW_DAYS)
    upcoming: list[JsonObject] = []

    for milestone in milestones:
        if milestone["estado"] == STATE_COMPLETED:
            continue

        planned_end = to_datetime(milestone["fechaFinPlan"])

        if planned_end is not None and planned_end <= window_end:
            upcoming.append(milestone)

    return upcoming


def find_last_event(
    real_history: Sequence[HistoryEvent],
    markers: Sequence[HistoryEvent],
) -> HistoryEvent | None:
    """
    Encuentra el ultimo evento cronologico (fases reales y marcadores).

    Args:
        real_history: Ejecucion real.
        markers: Marcadores Suspendido/Completed.

    Returns:
        El ultimo evento, o None si no hay eventos.
    """
    all_events = sorted(
        [*real_history, *markers],
        key=functools.cmp_to_key(compare_by_start),
    )

    return all_events[-1] if all_events else None


def compare_by_start(first: HistoryEvent, second: HistoryEvent) -> int:
    """
    Compara dos eventos por fecha de inicio como el sort del original.

    Un evento sin fecha valida se considera igual a cualquiera, igual que
    una comparacion con NaN en JavaScript.

    Args:
        first: Primer evento.
        second: Segundo evento.

    Returns:
        Negativo, cero o positivo.
    """
    first_start = to_datetime(first.start)
    second_start = to_datetime(second.start)

    if first_start is None or second_start is None:
        return 0

    if first_start < second_start:
        return -1

    return 1 if first_start > second_start else 0


def strip_phase(status: str) -> str:
    """
    Quita el sufijo EST u OP del estatus.

    Args:
        status: Estatus de la fila.

    Returns:
        El nombre de la fase.
    """
    return PHASE_SUFFIX.sub("", status).strip()


def first_text(rows: Sequence[SheetRow], candidate_names: list[str]) -> str:
    """
    Regresa el primer valor no vacio de una columna.

    Args:
        rows: Filas del proyecto.
        candidate_names: Nombres posibles de la columna.

    Returns:
        El primer valor encontrado como texto.
    """
    for row in rows:
        value = get_flexible_value(row, candidate_names)

        if value:
            return to_text(value)

    return ""


def safe_iso(value: CellValue | datetime) -> str | None:
    """
    Convierte una fecha a ISO UTC, como fechaSeguraRecursos().

    Args:
        value: Fecha de la celda.

    Returns:
        La fecha ISO, o None si no es una fecha valida.
    """
    if not value:
        return None

    if isinstance(value, str) and ISO_DATE_ONLY.fullmatch(value):
        # new Date("2026-10-15") en JavaScript es medianoche UTC, no local.
        try:
            return date.fromisoformat(value).strftime("%Y-%m-%dT00:00:00.000Z")
        except ValueError:
            return None

    moment = to_datetime(value)

    return to_utc_iso(moment) if moment is not None else None
