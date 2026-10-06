"""Alta de oportunidades y consumo de Clockify de la vista de cuenta."""

import logging
import math
import re
from collections.abc import Callable, Mapping, Sequence
from datetime import date
from typing import Any

from apps.ejecutivo.constants import SHEET_MPB
from apps.ejecutivo.services.account_view import (
    AccountCache,
    find_opportunity_source,
    json_number,
    load_mpb_projects,
    load_opportunities,
    normalize_value,
    sheet_values,
)
from apps.ejecutivo.services.mpb_values import (
    parse_mpb_date,
    parse_mpb_hours,
    parse_mpb_number,
    read_cell,
)
from core.exceptions import DashboardError
from core.sheets.protocols import SheetReader, SheetWriter
from core.time_entries.models import TimeEntry
from core.utils.cell_types import CellValue
from core.utils.js_values import js_null_text, js_number, js_or_text
from core.utils.locks import script_lock
from core.utils.numbers import round_half_up

"""BKD.040.011 - Acciones de la vista de cuenta
Equivale a beeCuentaGuardarOportunidad() y obtenerConsumosMPBCuenta():
agrega una oportunidad al backlog y calcula en Clockify, por lotes, las
horas consumidas de los proyectos MPB de la cuenta. Las horas de un
proyecto finalizado se guardan en la columna BL de MPB.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]
ProjectLoader = Callable[[str, tuple[date, date]], list[TimeEntry]]

OPPORTUNITY_LOCK_SECONDS = 15
MPB_LOCK_SECONDS = 10
MAX_NAME = 250
MAX_MANAGER = 160
MAX_STAGE = 100
FORMULA_START = re.compile(r"^[=+@\-]")
MAX_PENDING_IDS = 1000
MAX_BATCH = 4
DEFAULT_BATCH = 3
BURN_COLUMN = 64
BURN_HEADER = "Horas consumidas (Clockify)"


class AccountError(DashboardError):
    """Error de la vista de cuenta con el mensaje del original."""

    code = "ERR_ACCOUNT"
    expose_detail = True


def save_opportunity(
    sheets: tuple[SheetReader, SheetWriter],
    client: object,
    payload_value: object,
    cache: AccountCache,
) -> JsonObject:
    """
    Agrega una oportunidad al backlog (beeCuentaGuardarOportunidad).

    Args:
        sheets: Lector y escritor de Sheets.
        client: Cuenta.
        payload_value: name, manager, stage, close y hours.
        cache: Cache de la hoja de oportunidades.

    Returns:
        {"ok", "source", "items"} con la lista actualizada.

    Raises:
        AccountError: Con los mensajes de validacion del original.
    """
    reader, writer = sheets

    if not normalize_value(client):
        raise AccountError("Selecciona una cuenta.")

    payload: Mapping[str, Any] = (
        payload_value if isinstance(payload_value, dict) else {}
    )
    name = js_or_text(payload.get("name")).strip()
    manager = js_or_text(payload.get("manager")).strip()
    stage = js_or_text(payload.get("stage")).strip()
    close_value = payload.get("close")
    close = parse_mpb_date(close_value) if isinstance(close_value, str) else ""

    if not name or not manager or not stage:
        raise AccountError("Completa oportunidad, Delivery Manager y stage.")

    if (
        len(name) > MAX_NAME
        or len(manager) > MAX_MANAGER
        or len(stage) > MAX_STAGE
    ):
        raise AccountError("Uno de los campos excede la longitud permitida.")

    if any(FORMULA_START.match(text) for text in (name, manager, stage)):
        raise AccountError(
            "Los campos de texto no pueden comenzar con operadores de fórmula.",
        )

    with script_lock(OPPORTUNITY_LOCK_SECONDS):
        source = find_opportunity_source(reader, cache)

        if source is None:
            raise AccountError(
                "No se encontró una hoja con las columnas del backlog.",
            )

        width = max(
            (len(row) for row in sheet_values(reader, source.sheet)), default=0
        )
        values: list[CellValue] = [""] * width
        columns = source.columns
        values[columns["account"]] = js_null_text(client).strip()
        values[columns["name"]] = name

        if columns["manager"] >= 0:
            values[columns["manager"]] = manager

        values[columns["stage"]] = stage

        if columns["close"] >= 0:
            values[columns["close"]] = close

        hours = payload.get("hours")
        values[columns["hours"]] = json_number(
            parse_mpb_hours(
                hours if isinstance(hours, str | int | float) else ""
            ),
        )
        writer.append_row(source.sheet, values)

        return {"ok": True, **load_opportunities(reader, client, cache)}


def load_account_consumption(
    sheets: tuple[SheetReader, SheetWriter],
    request: tuple[object, object, object, object],
    load_entries: ProjectLoader,
    today: date,
    cache: AccountCache,
) -> JsonObject:
    """
    Horas de Clockify de un lote de proyectos MPB (obtenerConsumosMPBCuenta).

    Args:
        sheets: Lector y escritor de Sheets.
        request: Cuenta, offset, limit e IDs pendientes de la vista.
        load_entries: Lee los registros de Clockify de un proyecto.
        today: Fecha local de hoy.
        cache: Cache de 5 minutos de los proyectos MPB de la cuenta.

    Returns:
        {"ok", "items", "next", "total"}.
    """
    reader, writer = sheets
    client, offset, limit, pending_ids = request
    projects = load_mpb_projects(reader, client, cache)
    start = max(0.0, number_or_zero(offset))
    size = min(MAX_BATCH, max(1.0, number_or_zero(limit) or DEFAULT_BATCH))
    ids: Sequence[object] = (
        pending_ids
        if isinstance(pending_ids, list) and len(pending_ids) <= MAX_PENDING_IDS
        else [
            project["id"]
            for project in projects
            if project["burnGuardado"] is None
        ]
    )
    by_id = {normalize_value(project["id"]): project for project in projects}
    selected = list(ids)[math.trunc(start) : math.trunc(start + size)]
    to_save: list[tuple[int, float]] = []
    items = [
        consumption_item(
            (js_or_text(item_id), by_id.get(normalize_value(item_id))),
            load_entries,
            today,
            to_save,
        )
        for item_id in selected
    ]

    if to_save:
        save_burns(reader, writer, to_save)

    next_value = start + len(items)

    return {
        "ok": True,
        "items": items,
        "next": json_number(next_value),
        "total": len(ids),
    }


def number_or_zero(value: object) -> float:
    """Number(x) || 0."""
    number = js_number(value)

    return 0.0 if math.isnan(number) else number


def consumption_item(
    selection: tuple[str, JsonObject | None],
    load_entries: ProjectLoader,
    today: date,
    to_save: list[tuple[int, float]],
) -> JsonObject:
    """
    Horas de un proyecto del lote.

    Args:
        selection: ID pedido y proyecto de MPB (None si ya no es de la cuenta).
        load_entries: Lee los registros de Clockify.
        today: Fecha local de hoy.
        to_save: Acumula (fila de MPB, horas) de los proyectos finalizados.

    Returns:
        {"id", "burn"} con "guardado" o "error" cuando aplica.
    """
    requested_id, project = selection

    if project is None:
        return {
            "id": requested_id,
            "burn": None,
            "error": "El proyecto ya no pertenece a esta cuenta en MPB",
        }

    project_id = project["id"]

    if project["finalizado"] and project["burnGuardado"] is not None:
        return {
            "id": project_id,
            "burn": project["burnGuardado"],
            "guardado": True,
        }

    if not project["inicio"]:
        return {
            "id": project_id,
            "burn": None,
            "error": "Sin fecha INICIO en MPB",
        }

    today_text = today.isoformat()
    end_text = (
        (project["fin"] or today_text) if project["finalizado"] else today_text
    )

    try:
        date_range = (
            date.fromisoformat(project["inicio"]),
            date.fromisoformat(end_text),
        )
    except ValueError:
        return {
            "id": project_id,
            "burn": None,
            "error": "La fecha INICIO o FIN de MPB no es valida",
        }

    try:
        entries = load_entries(project_id, date_range)
    except DashboardError as error:
        return {"id": project_id, "burn": None, "error": error.detail}

    burn = round_half_up(
        sum(
            entry.duration_hours
            for entry in entries
            if entry.entry_date is not None
            and project["inicio"]
            <= entry.entry_date.date().isoformat()
            <= end_text
        ),
        2,
    )

    if project["finalizado"]:
        to_save.append((project["mpbFila"], burn))

    return {"id": project_id, "burn": json_number(burn)}


def save_burns(
    reader: SheetReader,
    writer: SheetWriter,
    to_save: Sequence[tuple[int, float]],
) -> None:
    """
    Guarda en BL las horas de los proyectos finalizados sin valor.

    Un fallo se registra en el log y no afecta la respuesta, como en el
    original.
    """
    try:
        with script_lock(MPB_LOCK_SECONDS):
            values = sheet_values(reader, SHEET_MPB)
            header = read_cell(values[0] if values else [], BURN_COLUMN - 1)

            if not header:
                writer.write_cell(SHEET_MPB, 1, BURN_COLUMN, BURN_HEADER)

            for row_number, burn in to_save:
                row = (
                    values[row_number - 1] if row_number <= len(values) else []
                )
                existing = parse_mpb_number(read_cell(row, BURN_COLUMN - 1))

                if existing is None or existing < 0:
                    writer.write_cell(
                        SHEET_MPB,
                        row_number,
                        BURN_COLUMN,
                        json_number(burn),
                    )
    except DashboardError as error:
        logger.warning(
            "MPB: se calcularon horas, pero no se guardaron en BL: %s",
            error.detail,
        )
