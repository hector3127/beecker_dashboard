"""Etapas del Gantt IXB/RaaS desde Historico_Proyectos A:I."""

import collections
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from apps.clockify.services.date_ranges import (
    STAGE_DISCOVERY,
    find_header_row,
    normalize_history_text,
    normalize_project_id,
    parse_sheet_date,
    pick_stage_date,
    read_cell,
)
from core.utils.cell_types import CellValue
from core.utils.text import to_text

"""BKD.040.011 - Etapas del historico
Equivale a obtenerEtapasHistoricoAIProyecto(),
_ixsHitosDesdeEtapasEjecutivo_() y _ixsAvanceEstimadoEtapasEjecutivo_():
- Las filas "<Etapa> EST" son el plan; las demas son la ejecucion real.
- El avance suma 1 por etapa completada y la fraccion transcurrida de
  la etapa en curso.
"""

JsonObject = dict[str, Any]

HISTORY_COLUMN_COUNT = 9
HISTORY_HEADERS = ("project id", "status", "start", "finish")
STAGE_NAMES = (
    ("discovery", "Discovery"),
    ("development", "Development"),
    ("deployment", "Deployment"),
)
SUSPENDED_STATUS = re.compile(r"^suspend")
ESTIMATED_STATUS = re.compile(r"\best\b")
PHASE_SUFFIX = re.compile(r"\s+(EST|OP)$", re.IGNORECASE)
ISO_DAY = re.compile(r"^(\d{4})-(\d{1,2})-(\d{1,2})")
DAY_MONTH_YEAR = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{4})")
UPCOMING_WINDOW_DAYS = 60
MAX_OPEN_PCT = 99
GENERAL_WORK_ITEMS = "general"
FULL_PCT = 100

STATE_PENDING = "Pendiente"
STATE_IN_PROGRESS = "En curso"
STATE_COMPLETED = "Completado"


@dataclass(slots=True)
class HistoryStages:
    """Plan, ejecucion real y suspensiones de un proyecto."""

    milestones: list[JsonObject] = field(default_factory=list)
    real_history: list[JsonObject] = field(default_factory=list)
    suspensions: list[JsonObject] = field(default_factory=list)


@dataclass(slots=True)
class StageProgress:
    """Avance estimado por etapas."""

    pct: float | None
    current_stage_pct: float | None


def read_history_stages(
    history_values: Sequence[Sequence[CellValue]],
    project_id: str,
) -> HistoryStages | None:
    """
    Lee las etapas del proyecto en las columnas A:I del historico.

    Args:
        history_values: Celdas de Historico_Proyectos.
        project_id: ID interno del proyecto.

    Returns:
        Las etapas, o None si no hay encabezados o Discovery.
    """
    normalized_id = normalize_project_id(project_id)

    if not normalized_id:
        return None

    rows = [list(row[:HISTORY_COLUMN_COUNT]) for row in history_values]
    header_index = find_header_row(
        rows,
        HISTORY_HEADERS,
        normalize_history_text,
    )

    if header_index is None:
        return None

    headers = [normalize_history_text(cell) for cell in rows[header_index]]
    id_column, status_column, start_column, finish_column = (
        headers.index(header) for header in HISTORY_HEADERS
    )
    first_data_row = header_index + 1
    matches = [
        row
        for row in rows[first_data_row:]
        if normalize_project_id(read_cell(row, id_column)) == normalized_id
    ]

    if (
        pick_stage_date(matches, STAGE_DISCOVERY, status_column, start_column)
        is None
    ):
        return None

    stages = HistoryStages()

    for row in matches:
        add_history_row(
            stages,
            normalize_history_text(read_cell(row, status_column)),
            format_day(read_cell(row, start_column)),
            format_day(read_cell(row, finish_column)),
        )

    return stages


def add_history_row(
    stages: HistoryStages,
    status: str,
    start: str,
    finish: str,
) -> None:
    """
    Clasifica una fila del historico como plan, real o suspension.

    Args:
        stages: Etapas acumuladas.
        status: Status normalizado.
        start: Inicio YYYY-MM-DD.
        finish: Fin YYYY-MM-DD, o vacio.
    """
    if not start:
        return

    stage = next(
        (name for key, name in STAGE_NAMES if key in status),
        "",
    )

    if SUSPENDED_STATUS.match(status):
        stages.suspensions.append(
            {"fechaInicio": start, "fechaFin": finish or start},
        )
    elif stage and ESTIMATED_STATUS.search(status):
        stages.milestones.append(
            {
                "nombre": stage,
                "fechaInicioPlan": start,
                "fechaFinPlan": finish or start,
            },
        )
    elif stage:
        stages.real_history.append(
            {
                "fase": stage,
                "fechaInicio": start,
                "fechaFin": finish,
                "enCurso": not finish,
            },
        )


def format_day(value: CellValue) -> str:
    """
    Convierte la celda a YYYY-MM-DD.

    Args:
        value: Fecha de la celda.

    Returns:
        La fecha, o cadena vacia si no es fecha.
    """
    day = parse_sheet_date(value)

    return day.isoformat() if day is not None else ""


def stage_day(value: object) -> datetime | None:
    """
    Lee la fecha de una etapa a medianoche local, como _ixsDiaEtapa_().

    Args:
        value: Texto ISO (YYYY-MM-DD...) o dd/mm/aaaa.

    Returns:
        La medianoche local, o None.
    """
    if not value:
        return None

    text = to_text(value if isinstance(value, str | int | float) else "")
    text = text.strip()
    iso_match = ISO_DAY.match(text)

    if iso_match:
        year, month, day = (int(part) for part in iso_match.groups())
    else:
        day_match = DAY_MONTH_YEAR.match(text)

        if not day_match:
            return None

        day, month, year = (int(part) for part in day_match.groups())

    return build_local_day(year, month, day)


def build_local_day(year: int, month: int, day: int) -> datetime | None:
    """
    Crea la fecha local permitiendo desbordes como new Date(y, m, d).

    Args:
        year: Anio.
        month: Mes 1-12 (puede desbordar).
        day: Dia (puede desbordar).

    Returns:
        La medianoche local, o None si el anio no es valido.
    """
    extra_years, month_index = divmod(month - 1, 12)

    try:
        first_day = datetime(year + extra_years, month_index + 1, 1)
    except ValueError:
        return None

    return first_day + timedelta(days=day - 1)


def milestones_from_stages(
    stages: HistoryStages,
    previous: JsonObject,
    today: date,
) -> JsonObject:
    """
    Arma los hitos del Gantt con el plan y la ejecucion real.

    Args:
        stages: Etapas del historico A:I.
        previous: Hitos calculados antes (para DM y servicio).
        today: Fecha local de hoy.

    Returns:
        Los hitos con la forma de calcularHitosProyecto().
    """
    today_start = datetime(today.year, today.month, today.day)
    used_by_stage: dict[str, int] = {}
    planned_count = collections.Counter(
        phase_key(planned.get("nombre") or "Fase")
        for planned in stages.milestones
    )
    milestones: list[JsonObject] = []

    for order, planned in enumerate(stages.milestones, start=1):
        name = to_text(planned.get("nombre") or "Fase").strip()
        key = phase_key(name)
        occurrence = used_by_stage.get(key, 0)
        used_by_stage[key] = occurrence + 1
        events = sorted(
            (
                event
                for event in stages.real_history
                if phase_key(event["fase"]) == key
            ),
            key=lambda event: day_ms(stage_day(event["fechaInicio"])),
        )
        real = pick_real_event(events, occurrence, planned_count[key])
        real_start = real["fechaInicio"] if real else ""
        real_finish = (real["fechaFin"] if real else "") or ""
        milestones.append(
            {
                "orden": order,
                "nombre": name,
                "fechaInicioPlan": planned.get("fechaInicioPlan") or "",
                "fechaFinPlan": planned.get("fechaFinPlan") or "",
                "fechaInicioReal": real_start or "",
                "fechaFinReal": real_finish,
                "estado": milestone_state(real, real_start, today_start),
            },
        )

    window_end = today_start + timedelta(days=UPCOMING_WINDOW_DAYS)
    upcoming = [
        milestone
        for milestone in milestones
        if milestone["estado"] != STATE_COMPLETED
        and (planned_end := stage_day(milestone["fechaFinPlan"])) is not None
        and planned_end <= window_end
    ]

    return {
        "lista": milestones,
        "proximos": upcoming,
        "deliveryManager": previous.get("deliveryManager") or "",
        "servicio": previous.get("servicio") or "",
        "historialCompleto": stages.real_history,
        "suspensiones": stages.suspensions,
        "periodosSuspension": [
            suspension["fechaInicio"]
            for suspension in stages.suspensions
            if suspension["fechaInicio"]
        ],
    }


def calculate_work_item_progress(
    closed: int,
    total: int,
    open_points: float = 0.0,
) -> float | None:
    """
    Avance por work items: cada WI pesa lo mismo.

    Un WI cerrado aporta 100 puntos; los abiertos aportan sus puntos de
    avance registrados (0 si no hay), con tope de 99 por WI.

    Args:
        closed: Work items cerrados.
        total: Work items totales.
        open_points: Suma de puntos de avance de los WIs abiertos.

    Returns:
        El porcentaje (0 a 100), o None si no hay work items.
    """
    if total <= 0:
        return None

    points = FULL_PCT * closed + open_points

    return min(FULL_PCT, math.floor(points / total * 10) / 10)


def pick_real_event(
    events: Sequence[JsonObject],
    occurrence: int,
    planned_total: int,
) -> JsonObject | None:
    """
    Elige el evento real de una fase planeada.

    La ultima aparicion planeada toma el ultimo evento real: una fase
    que se reanuda despues de una suspension cuenta con su ultimo tramo.

    Args:
        events: Eventos reales de la fase, por fecha de inicio.
        occurrence: Posicion de esta fase entre las planeadas iguales.
        planned_total: Cuantas veces se planeo esa fase.

    Returns:
        El evento real, o None si todavia no hay.
    """
    if occurrence >= len(events):
        return None

    if occurrence == planned_total - 1:
        return events[-1]

    return events[occurrence]


def milestone_state(
    real: JsonObject | None,
    real_start: str,
    today_start: datetime,
) -> str:
    """
    Estado de un hito segun su ejecucion real.

    Args:
        real: Evento real que corresponde al hito.
        real_start: Inicio real.
        today_start: Medianoche local de hoy.

    Returns:
        En curso, Completado o Pendiente.
    """
    if not real and not real_start:
        return STATE_PENDING

    if real and real.get("enCurso"):
        return STATE_IN_PROGRESS

    real_finish = real.get("fechaFin") if real else ""
    finish_day = stage_day(real_finish)

    if real_finish and finish_day is not None and finish_day < today_start:
        return STATE_COMPLETED

    return STATE_IN_PROGRESS


def phase_key(name: object) -> str:
    """
    Nombre de fase sin EST/OP y en minusculas.

    Args:
        name: Nombre de la fase.

    Returns:
        La llave para comparar fases.
    """
    text = to_text(name if isinstance(name, str) else "").strip()

    return PHASE_SUFFIX.sub("", text).lower()


def day_ms(moment: datetime | None) -> float:
    """
    Valor para ordenar fechas; sin fecha cuenta como 0.

    Args:
        moment: Fecha.

    Returns:
        Los segundos desde la epoca, o 0.
    """
    return moment.timestamp() if moment is not None else 0.0


def estimate_stage_progress(
    phases: Sequence[JsonObject],
    now: datetime,
) -> StageProgress:
    """
    Estima el avance por etapas a la fecha de corte.

    Cada etapa completada aporta una unidad; la etapa en curso aporta
    la fraccion transcurrida de su duracion (incluido el dia final) y
    no pasa de 99% mientras siga abierta.

    Args:
        phases: Hitos del proyecto.
        now: Fecha y hora local de corte.

    Returns:
        El avance total y el de la etapa en curso.
    """
    if not phases:
        return StageProgress(None, None)

    progress_sum = 0.0
    completed = 0
    current_pct: float | None = None

    for phase in phases:
        state = to_text(phase.get("estado") or "").strip().lower()

        if state == STATE_COMPLETED.lower():
            progress_sum += 1
            completed += 1
            continue

        if state != STATE_IN_PROGRESS.lower():
            continue

        start = stage_day(
            phase.get("fechaInicioReal") or phase.get("fechaInicioPlan"),
        )
        end = stage_day(phase.get("fechaFinReal") or phase.get("fechaFinPlan"))

        if start is None or end is None or end < start:
            continue

        # El ultimo dia cuenta conforme transcurre.
        exclusive_end = end + timedelta(days=1)
        fraction = min(
            1.0,
            max(
                0.0,
                (now - start).total_seconds()
                / (exclusive_end - start).total_seconds(),
            ),
        )
        progress_sum += fraction
        current_pct = (
            min(MAX_OPEN_PCT, math.floor(fraction * 1000) / 10)
            if fraction < 1
            else FULL_PCT
        )

    estimated = math.floor(progress_sum / len(phases) * 1000) / 10

    if completed == len(phases) - 1 and current_pct is not None:
        estimated = max(
            math.floor(completed / len(phases) * 1000) / 10,
            current_pct,
        )

    return StageProgress(
        pct=(
            min(MAX_OPEN_PCT, estimated)
            if progress_sum < len(phases)
            else FULL_PCT
        ),
        current_stage_pct=current_pct,
    )
