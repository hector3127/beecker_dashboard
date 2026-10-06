"""Hojas propias del panel Daily: pendientes, ajustes y avance de work items."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from apps.daily.constants import (
    ADJUSTMENT_HEADERS,
    ALL_PROJECTS,
    DAILY_PENDING_HEADERS,
    PROGRESS_COLUMN_BY_FIELD,
    SHEET_DAILY_PENDING,
    SHEET_WORK_ITEM_PROGRESS,
    WORK_ITEM_PROGRESS_HEADERS,
)
from apps.daily.exceptions import DailyRequestError
from apps.ejecutivo.services.project_milestones import safe_iso
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.cell_types import CellValue, SheetRow
from core.utils.dates import to_datetime
from core.utils.numbers import to_number
from core.utils.text import to_text

"""BKD.070.007 - Hojas del Daily
Equivale a PendientesDailyService (Pendientes_Daily), a los Ajustes UAT
y Garantia (Ajustes_UAT, Ajustes_Garantia) y al avance manual de los
work items (WorkItems_Avance). Cada hoja se crea sola la primera vez.
"""

JsonObject = dict[str, Any]

PRIORITIES = ("Alta", "Media", "Baja")
PENDING_STATES = ("Abierto", "Completado")
COMPLETED = "Completado"
MAX_PCT = 100
STATE_COLUMN = 6
DEV_PCT_COLUMN = 4
QA_COLUMN = 5
PROJECT_COLUMN = 2


@dataclass(slots=True)
class DailySheets:
    """Lector y escritor de Sheets con el reloj del panel."""

    reader: SheetReader
    writer: SheetWriter
    now: datetime
    timestamp_ms: int

    def rows(self, sheet_name: str, headers: Sequence[str]) -> list[SheetRow]:
        """
        Crea la hoja si no existe y la lee como objetos.

        Args:
            sheet_name: Nombre de la hoja.
            headers: Encabezados de una hoja nueva.

        Returns:
            Las filas por encabezado.
        """
        self.writer.ensure_sheet(sheet_name, headers)

        return self.reader.read_as_objects(sheet_name)

    def find_row_number(
        self,
        sheet_name: str,
        headers: Sequence[str],
        record_id: object,
    ) -> int | None:
        """
        Busca la fila (base 1) cuyo ID en la columna A coincide.

        Args:
            sheet_name: Nombre de la hoja.
            headers: Encabezados de una hoja nueva.
            record_id: ID buscado (se compara como texto).

        Returns:
            El numero de fila, o None.
        """
        self.writer.ensure_sheet(sheet_name, headers)
        wanted_id = js_string(record_id)

        for row_number, row in enumerate(
            self.reader.read_values(sheet_name)[1:],
            start=2,
        ):
            first_cell = row[0] if row else ""

            if js_string(first_cell) == wanted_id:
                return row_number

        return None


def js_string(value: object) -> str:
    """
    Convierte a texto como String(x) de JavaScript.

    Args:
        value: Valor recibido o de la celda.

    Returns:
        El texto.
    """
    if value is None:
        return "null"

    if isinstance(value, str | int | float | bool):
        return to_text(value)

    return str(value)


def argument_text(value: object) -> str:
    """
    Convierte un argumento como String(x || '').trim().

    Args:
        value: Valor recibido.

    Returns:
        El texto sin espacios externos.
    """
    return js_string(value).strip() if value else ""


def clamp_pct(value: object) -> float:
    """
    Limita un porcentaje a 0-100, como Math.max(0, Math.min(100, x || 0)).

    Args:
        value: Valor recibido.

    Returns:
        El porcentaje.
    """
    number = (
        to_number(value) if isinstance(value, str | int | float | bool) else 0.0
    )
    clamped = max(0.0, min(float(MAX_PCT), number))

    return int(clamped) if clamped.is_integer() else clamped


def iso_ms(value: str | None) -> float:
    """
    Milisegundos de una fecha ISO; vacio cuenta como 0 (new Date(null)).

    Args:
        value: Fecha ISO o None.

    Returns:
        Los milisegundos.
    """
    if not value:
        return 0.0

    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))

    return moment.timestamp() * 1000


def is_true_cell(value: CellValue) -> bool:
    """
    Lee una casilla como String(x).trim().toUpperCase() === 'TRUE'.

    Args:
        value: Valor de la celda.

    Returns:
        True si la celda es verdadera.
    """
    return js_string(value).strip().upper() == "TRUE"


def list_daily_pending(
    sheets: DailySheets, project_filter: object
) -> JsonObject:
    """
    Pendientes abiertos, mas recientes primero (obtenerPendientesDaily).

    Args:
        sheets: Hojas del panel.
        project_filter: Proyecto o "Todos los proyectos".

    Returns:
        {"ok", "pendientes", "total"}.
    """
    rows = [
        row
        for row in sheets.rows(SHEET_DAILY_PENDING, DAILY_PENDING_HEADERS)
        if to_text(row.get("Estado") or "").strip() != COMPLETED
    ]

    if project_filter and project_filter != ALL_PROJECTS:
        rows = [row for row in rows if row.get("Proyecto") == project_filter]

    pending: list[JsonObject] = [
        {
            "id": row.get("ID"),
            "descripcion": row.get("Descripcion") or "",
            "proyecto": row.get("Proyecto") or "",
            "responsable": row.get("Responsable") or "",
            "prioridad": row.get("Prioridad") or "Media",
            "estado": row.get("Estado") or "Abierto",
            "fechaCreacion": safe_iso(row.get("Fecha_Creacion")),
            "fechaLimite": safe_iso(row.get("Fecha_Limite")),
        }
        for row in rows
    ]
    pending.sort(key=lambda item: -iso_ms(item["fechaCreacion"]))

    return {"ok": True, "pendientes": pending, "total": len(pending)}


def add_daily_pending(
    sheets: DailySheets,
    pending: tuple[object, object, object, object, object],
) -> JsonObject:
    """
    Agrega un pendiente abierto (agregarPendienteDaily).

    Args:
        sheets: Hojas del panel.
        pending: Descripcion, proyecto, responsable, prioridad y fecha
            limite.

    Returns:
        {"ok": True, "id"}.

    Raises:
        DailyRequestError: Cuando falta la descripcion.
    """
    description, project, owner, priority, due_date = pending
    description_text = argument_text(description)

    if not description_text:
        raise DailyRequestError("Falta la descripción del pendiente.")

    record_id = f"PND-{sheets.timestamp_ms}"
    due_moment = (
        to_datetime(due_date)
        if isinstance(due_date, str) and due_date
        else None
    )
    sheets.writer.ensure_sheet(SHEET_DAILY_PENDING, DAILY_PENDING_HEADERS)
    sheets.writer.append_row(
        SHEET_DAILY_PENDING,
        [
            record_id,
            description_text,
            argument_text(project),
            argument_text(owner),
            priority if priority in PRIORITIES else "Media",
            "Abierto",
            sheets.now,
            due_moment or "",
        ],
    )

    return {"ok": True, "id": record_id}


def update_daily_pending_state(
    sheets: DailySheets,
    record_id: object,
    new_state: object,
) -> JsonObject:
    """
    Marca un pendiente como Completado o lo reabre.

    Args:
        sheets: Hojas del panel.
        record_id: ID del pendiente.
        new_state: Abierto o Completado.

    Returns:
        {"ok": True}.

    Raises:
        DailyRequestError: Con estado invalido o ID inexistente.
    """
    if new_state not in PENDING_STATES:
        raise DailyRequestError("Estado inválido.")

    row_number = sheets.find_row_number(
        SHEET_DAILY_PENDING,
        DAILY_PENDING_HEADERS,
        record_id,
    )

    if row_number is None:
        raise DailyRequestError(
            f"No se encontró el pendiente con ID {js_string(record_id)}",
        )

    sheets.writer.write_cell(
        SHEET_DAILY_PENDING,
        row_number,
        STATE_COLUMN,
        str(new_state),
    )

    return {"ok": True}


def delete_daily_pending(sheets: DailySheets, record_id: object) -> JsonObject:
    """
    Elimina un pendiente (eliminarPendienteDaily).

    Args:
        sheets: Hojas del panel.
        record_id: ID del pendiente.

    Returns:
        {"ok": True}.

    Raises:
        DailyRequestError: Cuando el ID no existe.
    """
    row_number = sheets.find_row_number(
        SHEET_DAILY_PENDING,
        DAILY_PENDING_HEADERS,
        record_id,
    )

    if row_number is None:
        raise DailyRequestError(
            f"No se encontró el pendiente con ID {js_string(record_id)}",
        )

    sheets.writer.delete_row(SHEET_DAILY_PENDING, row_number)

    return {"ok": True}


def list_adjustments(
    sheets: DailySheets,
    sheet_name: str,
    project_filter: object,
) -> JsonObject:
    """
    Ajustes UAT o Garantia, mas recientes primero.

    Args:
        sheets: Hojas del panel.
        sheet_name: Ajustes_UAT o Ajustes_Garantia.
        project_filter: Proyecto o "Todos los proyectos".

    Returns:
        {"ok", "ajustes", "total"}.
    """
    rows = [
        row
        for row in sheets.rows(sheet_name, ADJUSTMENT_HEADERS)
        if row.get("ID")
    ]

    if project_filter and project_filter != ALL_PROJECTS:
        rows = [row for row in rows if row.get("Proyecto") == project_filter]

    adjustments: list[JsonObject] = [
        {
            "id": row.get("ID"),
            "ajuste": row.get("Ajuste") or "",
            "proyecto": row.get("Proyecto") or "",
            "devPct": to_number(row.get("Dev_Pct")),
            "qaListo": is_true_cell(row.get("QA_Listo")),
            "fechaCreacion": safe_iso(row.get("Fecha_Creacion")),
        }
        for row in rows
    ]
    adjustments.sort(key=lambda item: -iso_ms(item["fechaCreacion"]))

    return {"ok": True, "ajustes": adjustments, "total": len(adjustments)}


def add_adjustment(
    sheets: DailySheets,
    sheet_name: str,
    adjustment: tuple[object, object, object],
) -> JsonObject:
    """
    Agrega un ajuste con QA pendiente.

    Args:
        sheets: Hojas del panel.
        sheet_name: Ajustes_UAT o Ajustes_Garantia.
        adjustment: Descripcion, proyecto y % de desarrollo.

    Returns:
        {"ok": True, "id"}.

    Raises:
        DailyRequestError: Cuando falta la descripcion.
    """
    description, project, dev_pct = adjustment
    description_text = argument_text(description)

    if not description_text:
        raise DailyRequestError("Falta la descripción del ajuste.")

    record_id = f"ADJ-{sheets.timestamp_ms}"
    sheets.writer.ensure_sheet(sheet_name, ADJUSTMENT_HEADERS)
    sheets.writer.append_row(
        sheet_name,
        [
            record_id,
            description_text,
            argument_text(project),
            clamp_pct(dev_pct),
            False,
            sheets.now,
        ],
    )

    return {"ok": True, "id": record_id}


def update_adjustment(
    sheets: DailySheets,
    sheet_name: str,
    record_id: object,
    progress: tuple[object, object],
) -> JsonObject:
    """
    Actualiza el % de desarrollo y/o la casilla de QA.

    Args:
        sheets: Hojas del panel.
        sheet_name: Ajustes_UAT o Ajustes_Garantia.
        record_id: ID del ajuste.
        progress: % de desarrollo y QA listo (None no cambia).

    Returns:
        {"ok": True}.

    Raises:
        DailyRequestError: Cuando el ID no existe.
    """
    dev_pct, qa_ready = progress
    row_number = sheets.find_row_number(
        sheet_name, ADJUSTMENT_HEADERS, record_id
    )

    if row_number is None:
        raise DailyRequestError(
            f"No se encontró el ajuste con ID {js_string(record_id)}",
        )

    if dev_pct is not None:
        sheets.writer.write_cell(
            sheet_name,
            row_number,
            DEV_PCT_COLUMN,
            clamp_pct(dev_pct),
        )

    if qa_ready is not None:
        sheets.writer.write_cell(
            sheet_name, row_number, QA_COLUMN, bool(qa_ready)
        )

    return {"ok": True}


def delete_adjustment(
    sheets: DailySheets,
    sheet_name: str,
    record_id: object,
) -> JsonObject:
    """
    Elimina un ajuste.

    Args:
        sheets: Hojas del panel.
        sheet_name: Ajustes_UAT o Ajustes_Garantia.
        record_id: ID del ajuste.

    Returns:
        {"ok": True}.

    Raises:
        DailyRequestError: Cuando el ID no existe.
    """
    row_number = sheets.find_row_number(
        sheet_name, ADJUSTMENT_HEADERS, record_id
    )

    if row_number is None:
        raise DailyRequestError(
            f"No se encontró el ajuste con ID {js_string(record_id)}",
        )

    sheets.writer.delete_row(sheet_name, row_number)

    return {"ok": True}


def load_progress_map(sheets: DailySheets) -> dict[str, JsonObject]:
    """
    Avance guardado de cada work item (WorkItems_Avance).

    Args:
        sheets: Hojas del panel.

    Returns:
        ID del work item -> avance.
    """
    progress: dict[str, JsonObject] = {}

    for row in sheets.rows(
        SHEET_WORK_ITEM_PROGRESS, WORK_ITEM_PROGRESS_HEADERS
    ):
        if not row.get("ID_WorkItem"):
            continue

        progress[js_string(row.get("ID_WorkItem"))] = {
            "devPct": to_number(row.get("Dev_Pct")),
            "qaListo": is_true_cell(row.get("QA_Listo")),
            "ttProdListo": is_true_cell(row.get("TTProd_Listo")),
            "fechaLimiteDev": safe_iso(row.get("Fecha_Limite_Dev")),
            "demo": row.get("Demo") or "",
        }

    return progress


def save_work_item_progress(
    sheets: DailySheets,
    request: tuple[object, object, object],
    active_project: str,
) -> JsonObject:
    """
    Guarda un campo de avance de un work item (crea la fila si no existe).

    Args:
        sheets: Hojas del panel.
        request: ID del work item, campo y valor.
        active_project: Proyecto activo de Azure.

    Returns:
        {"ok": True}.

    Raises:
        DailyRequestError: Cuando el campo no existe.
    """
    work_item_id, field_name, value = request
    item_id = js_string(work_item_id)
    column = (
        PROGRESS_COLUMN_BY_FIELD.get(field_name)
        if isinstance(field_name, str)
        else None
    )

    if column is None:
        raise DailyRequestError(f"Campo desconocido: {js_string(field_name)}")

    row_number = sheets.find_row_number(
        SHEET_WORK_ITEM_PROGRESS,
        WORK_ITEM_PROGRESS_HEADERS,
        item_id,
    )
    value_to_save = progress_value(str(field_name), value)

    if row_number is None:
        new_row: list[CellValue] = [
            item_id,
            active_project,
            0,
            False,
            False,
            "",
            "",
        ]
        new_row[column - 1] = value_to_save
        sheets.writer.append_row(SHEET_WORK_ITEM_PROGRESS, new_row)
        return {"ok": True}

    sheets.writer.write_cell(
        SHEET_WORK_ITEM_PROGRESS,
        row_number,
        column,
        value_to_save,
    )

    if active_project:
        sheets.writer.write_cell(
            SHEET_WORK_ITEM_PROGRESS,
            row_number,
            PROJECT_COLUMN,
            active_project,
        )

    return {"ok": True}


def progress_value(field_name: str, value: object) -> CellValue:
    """
    Convierte el valor segun el campo de avance.

    Args:
        field_name: devConstruido, qa, ttProd, fechaLimiteDev o demo.
        value: Valor recibido.

    Returns:
        El valor a guardar.
    """
    if field_name == "devConstruido":
        return clamp_pct(value)

    if field_name in {"qa", "ttProd"}:
        return bool(value)

    if value is None or isinstance(value, str | int | float | bool):
        return value

    return str(value)
