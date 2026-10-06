"""Historicos y bitacora de automatizaciones en Google Sheets."""

import logging
from collections.abc import Mapping
from datetime import datetime

from core.exceptions import SheetNotFoundError
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.cell_types import CellValue
from core.utils.text import to_text

"""BKD.004.006 - Historicos y bitacora
Equivale a appendHistorico() y logAutomatizacion() de SheetService.gs.
"""

logger = logging.getLogger(__name__)

TIMESTAMP_HEADER = "Timestamp"


def append_history(
    reader: SheetReader,
    writer: SheetWriter,
    history_sheet_name: str,
    data: Mapping[str, CellValue | datetime],
    field_aliases: Mapping[str, str] | None,
    now: datetime,
) -> None:
    """
    Agrega una fila a una hoja historica (solo se agregan filas).

    Si la hoja historica no existe no hace nada, igual que el original.

    Args:
        reader: Repositorio de lectura.
        writer: Repositorio de escritura.
        history_sheet_name: Nombre de la hoja historica.
        data: Datos del registro que cambio.
        field_aliases: Encabezado historico -> campo de data.
        now: Fecha que se escribe en la columna Timestamp.
    """
    try:
        values = reader.read_values(history_sheet_name)
    except SheetNotFoundError:
        logger.info(
            "La hoja historica %s no existe; se omite el registro.",
            history_sheet_name,
        )
        return

    headers = [to_text(header) for header in values[0]] if values else []
    aliases = field_aliases or {}
    row: list[CellValue | datetime] = []

    for header in headers:
        if header == TIMESTAMP_HEADER:
            row.append(now)
        elif header in aliases and aliases[header] in data:
            row.append(data[aliases[header]])
        else:
            row.append(data.get(header, ""))

    writer.append_row(history_sheet_name, row)


def log_automation(
    reader: SheetReader,
    writer: SheetWriter,
    process_name: str,
    result: str,
    detail: str,
    duration_ms: int | None,
    now: datetime,
) -> None:
    """
    Escribe una entrada en la hoja Log_Automatizaciones.

    Args:
        reader: Repositorio de lectura.
        writer: Repositorio de escritura.
        process_name: Nombre del proceso ejecutado.
        result: Resultado del proceso.
        detail: Detalle adicional.
        duration_ms: Duracion en milisegundos, si se midio.
        now: Fecha del registro.
    """
    if not reader.sheet_exists(sheet_names.SHEET_AUTOMATION_LOG):
        return

    writer.append_row(
        sheet_names.SHEET_AUTOMATION_LOG,
        [
            now,
            process_name,
            result,
            detail,
            duration_ms if duration_ms is not None else "",
        ],
    )
