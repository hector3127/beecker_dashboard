"""Reglas de seleccion, estado y horas de los proyectos IXB/RaaS."""

import functools
import re
from collections.abc import Sequence
from datetime import date, datetime

from apps.azure_devops.services.project_resolver import normalize_azure_name
from apps.ejecutivo.services.project_milestones import ProjectMilestones
from core.time_entries.models import TimeEntry
from core.utils.cell_types import SheetRow
from core.utils.dates import to_datetime
from core.utils.numbers import round_half_up
from core.utils.text import extract_base_id, get_flexible_value, to_text

"""BKD.040.009 - Reglas IXB/RaaS
Equivale a _altoNivelIdPreferidoIXB(), _altoNivelFilaVigenteIXB(),
_altoNivelDeliveryManagerDesdeHistorico(),
_altoNivelProyectoFinalizadoHistorico(), _altoNivelStatusIXB(),
_statusActualProyecto() y al filtro por nomenclatura de Clockify.
"""

SPRINT_NUMBER = re.compile(r"_S(\d+)$", re.IGNORECASE)
CHANGE_REQUEST = re.compile(r"_CR(\d*)$", re.IGNORECASE)
NOMENCLATURE_IN_TEXT = re.compile(r"(?:^|[^A-Z0-9])(S\d+|CR\d*)(?:$|[^A-Z0-9])")
EXACT_NOMENCLATURE = re.compile(r"^(S\d+|CR\d*)$")

CLOSED_PROJECT_STATES = frozenset(
    {
        "CERRADO",
        "CLOSED",
        "COMPLETED",
        "COMPLETADO",
        "CANCELLED",
        "CANCELED",
        "CANCELADO",
        "INACTIVE",
        "INACTIVO",
        "NOT APPLICABLE",
    },
)
COMPLETED_STATES = frozenset({"COMPLETED", "COMPLETADO"})
SUSPENDED_STATES = frozenset({"SUSPENDIDO", "SUSPENDED"})

HISTORY_ID_COLUMNS = ["Project ID", "Project_ID", "Proyecto", "ID_Proyecto"]
HISTORY_MANAGER_COLUMNS = ["Delivery Manager", "Delivery_Manager"]
HISTORY_STATUS_COLUMNS = ["Status", "Estado", "Fase"]
HISTORY_START_COLUMNS = ["Start", "Fecha_Inicio", "Inicio"]
HISTORY_FINISH_COLUMNS = ["Finish", "Fecha_Fin", "Fin"]
PROJECT_MANAGER_COLUMNS = [
    "Delivery Manager",
    "Delivery Manag",
    "Scrum_Master",
    "Scrum Master",
    "SM",
    "Sponsor",
]

STATUS_SUSPENDED = "Suspendido"
STATUS_PENDING = "Pendiente"
STATUS_GRACE_DAYS = 1


def compare_project_ids(first_id: str, second_id: str) -> int:
    """
    Ordena IDs: con sufijo antes que base, S# mayor y CR# mayor primero.

    Args:
        first_id: Primer ID.
        second_id: Segundo ID.

    Returns:
        Negativo si first_id va antes.
    """
    first_specific = "_" in first_id
    second_specific = "_" in second_id

    if first_specific != second_specific:
        return -1 if first_specific else 1

    first_sprint = SPRINT_NUMBER.search(first_id)
    second_sprint = SPRINT_NUMBER.search(second_id)

    if first_sprint and second_sprint:
        return int(second_sprint.group(1)) - int(first_sprint.group(1))

    first_change = CHANGE_REQUEST.search(first_id)
    second_change = CHANGE_REQUEST.search(second_id)

    if bool(first_change) != bool(second_change):
        return -1 if first_change else 1

    if first_change and second_change:
        first_number = int(first_change.group(1) or 0)
        second_number = int(second_change.group(1) or 0)
        return second_number - first_number

    return 0


def sort_project_ids(project_ids: Sequence[str]) -> list[str]:
    """
    Quita duplicados y ordena por prioridad de nomenclatura.

    Args:
        project_ids: IDs del grupo.

    Returns:
        Los IDs ordenados, el mas especifico primero.
    """
    unique_ids = [
        project_id for project_id in dict.fromkeys(project_ids) if project_id
    ]

    return sorted(unique_ids, key=functools.cmp_to_key(compare_project_ids))


def read_project_id(row: SheetRow) -> str:
    """
    Lee el ID_Proyecto de una fila de Proyectos.

    Args:
        row: Fila de la hoja Proyectos.

    Returns:
        El ID sin espacios externos.
    """
    return to_text(row.get("ID_Proyecto")).strip()


def select_current_row(rows: Sequence[SheetRow], base_id: str) -> SheetRow:
    """
    Elige la nomenclatura vigente del grupo (no cerrada y mas especifica).

    Args:
        rows: Filas de Proyectos del mismo ID base.
        base_id: ID base del grupo.

    Returns:
        La fila representativa.
    """
    open_rows = [
        row
        for row in rows
        if normalize_azure_name(
            to_text(get_flexible_value(row, ["Estado", "Status"])),
        )
        not in CLOSED_PROJECT_STATES
    ]
    candidates = open_rows or list(rows)
    sorted_ids = sort_project_ids([read_project_id(row) for row in candidates])
    preferred_id = sorted_ids[0] if sorted_ids else base_id

    return next(
        (row for row in candidates if read_project_id(row) == preferred_id),
        candidates[0],
    )


def read_history_id(row: SheetRow) -> str:
    """
    Lee el ID del proyecto de una fila del historico.

    Args:
        row: Fila de Historico_Proyectos.

    Returns:
        El ID sin espacios externos.
    """
    return to_text(get_flexible_value(row, HISTORY_ID_COLUMNS)).strip()


def find_delivery_manager(
    history_rows: Sequence[SheetRow],
    reference_rows: Sequence[SheetRow],
    base_id: str,
) -> str:
    """
    Busca el Delivery Manager en el historico, prefiriendo el ID exacto.

    Args:
        history_rows: Filas de Historico_Proyectos.
        reference_rows: Filas de Proyectos de la nomenclatura vigente.
        base_id: ID base del grupo.

    Returns:
        El Delivery Manager, o cadena vacia.
    """
    sorted_ids = sort_project_ids(
        [read_project_id(row) for row in reference_rows],
    )

    for project_id in sorted_ids:
        for history_row in history_rows:
            manager = to_text(
                get_flexible_value(history_row, HISTORY_MANAGER_COLUMNS),
            ).strip()

            if read_history_id(history_row) == project_id and manager:
                return manager

    wanted_base = extract_base_id(
        base_id or (sorted_ids[0] if sorted_ids else "")
    )

    for history_row in history_rows:
        history_id = read_history_id(history_row)
        manager = to_text(
            get_flexible_value(history_row, HISTORY_MANAGER_COLUMNS),
        ).strip()

        if (
            history_id
            and manager
            and extract_base_id(history_id) == wanted_base
        ):
            return manager

    return ""


def read_project_manager(row: SheetRow) -> str:
    """
    Lee el responsable desde la fila de Proyectos (respaldo del DM).

    Args:
        row: Fila de Proyectos.

    Returns:
        El Delivery Manager, Scrum Master o Sponsor.
    """
    return to_text(get_flexible_value(row, PROJECT_MANAGER_COLUMNS))


def select_history_rows(
    history_rows: Sequence[SheetRow],
    project_id: str,
    base_id: str,
    allow_base: bool,
) -> list[SheetRow]:
    """
    Filtra el historico por ID exacto y, si se permite, por ID base.

    Args:
        history_rows: Filas de Historico_Proyectos.
        project_id: ID buscado.
        base_id: ID base.
        allow_base: Permite usar el ID base cuando no hay filas exactas.

    Returns:
        Las filas del proyecto.
    """
    exact_rows = [
        row for row in history_rows if read_history_id(row) == project_id
    ]

    if exact_rows or not allow_base:
        return exact_rows

    return [
        row
        for row in history_rows
        if extract_base_id(read_history_id(row)) == base_id
    ]


def read_history_status(row: SheetRow) -> str:
    """
    Lee el estatus normalizado de una fila del historico.

    Args:
        row: Fila de Historico_Proyectos.

    Returns:
        El estatus en mayusculas y sin acentos.
    """
    return normalize_azure_name(
        to_text(get_flexible_value(row, HISTORY_STATUS_COLUMNS)),
    )


def read_history_date(row: SheetRow, column_names: list[str]) -> date | None:
    """
    Lee una fecha del historico como dia local.

    Args:
        row: Fila de Historico_Proyectos.
        column_names: Nombres posibles de la columna.

    Returns:
        La fecha, o None si la celda no es fecha.
    """
    moment = to_datetime(get_flexible_value(row, column_names))

    return moment.date() if moment is not None else None


def is_finished_in_history(
    history_rows: Sequence[SheetRow],
    project_id: str,
    base_id: str,
    today: date,
) -> bool:
    """
    Indica si el proyecto ya esta Completed en el historico.

    Un ID con sufijo solo se cierra con su propia fila Completed:
    RAS.001 Completed no cierra RAS.001_CR1. El dia del Completed el
    proyecto sigue visible; se cierra cuando esa fecha ya paso. Una
    suspension que ya termino no lo mantiene abierto, pero una que
    sigue vigente hoy lo deja visible como Suspendido.

    Args:
        history_rows: Filas de Historico_Proyectos.
        project_id: ID de la nomenclatura vigente.
        base_id: ID base.
        today: Fecha local de hoy.

    Returns:
        True si la fecha del Completed ya paso (es menor a hoy).
    """
    rows = select_history_rows(
        history_rows,
        project_id,
        base_id,
        allow_base="_" not in project_id,
    )

    has_active_suspension = any(
        read_history_status(row) in SUSPENDED_STATES
        and is_active_period(
            read_history_date(row, HISTORY_START_COLUMNS),
            read_history_date(row, HISTORY_FINISH_COLUMNS),
            today,
        )
        for row in rows
    )

    if has_active_suspension:
        return False

    for row in rows:
        if read_history_status(row) not in COMPLETED_STATES:
            continue

        closing_date = read_history_date(
            row,
            HISTORY_FINISH_COLUMNS,
        ) or read_history_date(row, HISTORY_START_COLUMNS)

        if closing_date is not None and closing_date < today:
            return True

    return False


def is_active_period(
    start: date | None, finish: date | None, today: date
) -> bool:
    """
    Indica si hoy cae en un periodo; sin fin, el periodo sigue vigente.

    Args:
        start: Inicio del periodo.
        finish: Fin del periodo, si existe.
        today: Fecha local de hoy.

    Returns:
        True si el periodo esta vigente.
    """
    if start is None:
        return False

    if finish is None:
        return today >= start

    return start <= today <= finish


def has_active_gantt_suspension(
    milestones: ProjectMilestones,
    today: date,
) -> bool:
    """
    Revisa las suspensiones calculadas para el Gantt.

    Args:
        milestones: Hitos del proyecto.
        today: Fecha local de hoy.

    Returns:
        True si alguna suspension esta vigente.
    """
    for suspension in milestones.suspensions:
        start = to_datetime(suspension["fechaInicio"])
        finish = to_datetime(suspension["fechaFin"])

        if is_active_period(
            start.date() if start else None,
            finish.date() if finish else None,
            today,
        ):
            return True

    return False


def calculate_current_status(
    milestones: ProjectMilestones,
    now: datetime,
) -> str:
    """
    Estado actual segun el historico, como _statusActualProyecto().

    Args:
        milestones: Hitos del proyecto.
        now: Fecha y hora local actual.

    Returns:
        Suspendido, la fase en curso o la ultima fase iniciada.
    """
    history = milestones.full_history

    if not history:
        return STATUS_PENDING

    for suspension in milestones.suspensions:
        start = to_datetime(suspension["fechaInicio"]) or datetime(1970, 1, 1)
        finish = to_datetime(suspension["fechaFin"]) or now

        if start <= now <= finish:
            return STATUS_SUSPENDED

    in_progress = next((event for event in history if event["enCurso"]), None)

    if in_progress is not None:
        return str(in_progress["fase"])

    latest = max(
        history,
        key=lambda event: to_datetime(event["fechaInicio"]) or datetime.min,
    )

    return str(latest["fase"])


def resolve_ixb_status(
    azure_stage: str,
    azure_finish: datetime | None,
    reference_history: Sequence[SheetRow],
    milestones: ProjectMilestones,
    now: datetime,
) -> str:
    """
    Estado de la fila IXB/RaaS, como _altoNivelStatusIXB().

    Mientras no pase mas de un dia de la fecha fin de Azure se conserva
    la etapa de Azure. Despues se revisa si hay una suspension vigente.

    Args:
        azure_stage: Etapa calculada con Azure (vacia si no hay Azure).
        azure_finish: Fecha fin de Deployment en Azure.
        reference_history: Filas del historico del proyecto.
        milestones: Hitos del proyecto (respaldo del Gantt).
        now: Fecha y hora local actual.

    Returns:
        La etapa de Azure, Suspendido o el estado del historico.
    """
    fallback = (
        azure_stage
        or calculate_current_status(milestones, now)
        or STATUS_PENDING
    )

    if azure_finish is None:
        return fallback

    today = now.date()

    if (today - azure_finish.date()).days <= STATUS_GRACE_DAYS:
        return fallback

    for row in reference_history:
        if read_history_status(row) not in SUSPENDED_STATES:
            continue

        if is_active_period(
            read_history_date(row, HISTORY_START_COLUMNS),
            read_history_date(row, HISTORY_FINISH_COLUMNS),
            today,
        ):
            return STATUS_SUSPENDED

    if has_active_gantt_suspension(milestones, today):
        return STATUS_SUSPENDED

    return fallback


def extract_nomenclature(text: str) -> str:
    """
    Extrae S#/CR# de un tag o tarea, como _clockifyExtraerNomenclaturaTexto().

    Args:
        text: Texto del tag o la tarea.

    Returns:
        La nomenclatura en mayusculas, o cadena vacia.
    """
    upper_text = text.upper().strip()

    if not upper_text:
        return ""

    match = NOMENCLATURE_IN_TEXT.search(upper_text)

    if match:
        return match.group(1)

    return upper_text if EXACT_NOMENCLATURE.match(upper_text) else ""


def project_nomenclature(project_id: str) -> str:
    """
    Nomenclatura del ID IXB/RaaS: lo que sigue al primer guion bajo.

    Args:
        project_id: ID interno, por ejemplo RAS.001_CR1.

    Returns:
        La nomenclatura (CR1), o S1 si el ID no tiene sufijo.
    """
    parts = project_id.strip().split("_")

    if len(parts) <= 1:
        return "S1"

    return "_".join(parts[1:]).strip().upper() or "S1"


def belongs_to_nomenclature(entry: TimeEntry, nomenclature: str) -> bool:
    """
    Indica si un registro pertenece a la nomenclatura del proyecto.

    Si el tag o la tarea declaran otra nomenclatura se excluye; si no
    declaran ninguna, el registro cuenta por estar dentro del rango.

    Args:
        entry: Registro de Clockify.
        nomenclature: Nomenclatura del proyecto (S1, S2, CR1...).

    Returns:
        True si el registro pertenece.
    """
    explicit = [
        nomenclature_found
        for nomenclature_found in (
            *(extract_nomenclature(tag) for tag in entry.tags),
            extract_nomenclature(entry.task_name),
        )
        if nomenclature_found
    ]

    return all(found == nomenclature for found in explicit)


def calculate_exact_burn(
    entries: Sequence[TimeEntry], project_id: str
) -> float:
    """
    Suma las horas facturables de la nomenclatura vigente.

    Equivale a _altoNivelBurnExactoIXB() con
    obtenerHorasClockifyPorProyectoJerarquia().

    Args:
        entries: Registros de Clockify del proyecto.
        project_id: ID de la nomenclatura vigente.

    Returns:
        Las horas facturables, sin registros repetidos.
    """
    nomenclature = project_nomenclature(project_id)
    unique_entries = {
        entry.entry_id: entry
        for entry in entries
        if entry.is_billable and belongs_to_nomenclature(entry, nomenclature)
    }

    return round_half_up(
        sum(entry.duration_hours for entry in unique_entries.values()),
        2,
    )
