"""Resumen ejecutivo AER/T&M a partir de la hoja MPB."""

import re
from collections.abc import Sequence
from datetime import date
from typing import Any

from apps.ejecutivo.constants import (
    HEADER_SEARCH_ROWS,
    MPB_COLUMNS,
    ROLE_COLUMNS,
    SERVICE_AER,
    SERVICE_TYM,
    UNASSIGNED_MANAGER,
)
from apps.ejecutivo.services.mpb_values import (
    normalize_mpb,
    parse_mpb_date,
    parse_mpb_hours,
    parse_mpb_number,
    read_cell,
)
from core.exceptions import SheetColumnNotFoundError
from core.utils.cell_types import CellValue
from core.utils.numbers import round_half_up, round_half_up_int
from core.utils.text import to_text

"""BKD.040.003 - Resumen AER/T&M
Equivale a obtenerResumenAERTYMMPB(): una sola lectura de MPB con los
proyectos AER y T&M en progreso. Las horas consumidas de Clockify se
piden despues, en lotes, con obtenerConsumosResumenAERTYMMPB().
"""

JsonObject = dict[str, Any]

AER_TYM_SERVICE = re.compile(r"^(aer|t\s*&\s*m|tym|t\s*y\s*m)$")
IN_PROGRESS_STATUS = re.compile(
    r"^(en progreso|in progress|en desarrollo|en proceso)$",
)
REQUIRED_HEADERS = ("cliente", "estatus", "service")


def build_aer_tym_summary(
    mpb_values: Sequence[Sequence[CellValue]],
    today: date,
) -> JsonObject:
    """
    Construye la tabla de proyectos AER/T&M vigentes.

    Args:
        mpb_values: Celdas de la hoja MPB (columnas A:BL).
        today: Fecha local de hoy.

    Returns:
        {"ok": True, "filas": [...], "fuente": "MPB"}.

    Raises:
        SheetColumnNotFoundError: Cuando faltan los encabezados de MPB.
    """
    header_index = find_mpb_header(mpb_values)

    if header_index is None:
        raise SheetColumnNotFoundError(
            "No se encontraron los encabezados CLIENTE, SERVICE y ESTATUS "
            "en MPB.",
        )

    columns = resolve_columns(mpb_values[header_index])
    first_data_row = header_index + 1
    rows_by_id: dict[str, JsonObject] = {}

    for row in mpb_values[first_data_row:]:
        summary_row = build_summary_row(row, columns, today)

        if summary_row is not None:
            rows_by_id[normalize_mpb(summary_row["idProyecto"])] = summary_row

    return {"ok": True, "filas": list(rows_by_id.values()), "fuente": "MPB"}


def find_mpb_header(mpb_values: Sequence[Sequence[CellValue]]) -> int | None:
    """
    Busca la fila de encabezados de MPB entre las primeras 12 filas.

    Args:
        mpb_values: Celdas de la hoja MPB.

    Returns:
        El indice de la fila, o None.
    """
    for row_index, row in enumerate(mpb_values[:HEADER_SEARCH_ROWS]):
        normalized_cells = {normalize_mpb(cell) for cell in row}

        if all(header in normalized_cells for header in REQUIRED_HEADERS):
            return row_index

    return None


def resolve_columns(header_row: Sequence[CellValue]) -> dict[str, int]:
    """
    Ubica cada columna por encabezado o usa la posicion de respaldo.

    Args:
        header_row: Fila de encabezados.

    Returns:
        Nombre logico -> indice de columna.
    """
    headers = [normalize_mpb(cell) for cell in header_row]
    columns: dict[str, int] = {}

    for logical_name, (header_name, fallback_index) in MPB_COLUMNS.items():
        normalized_header = normalize_mpb(header_name)
        columns[logical_name] = (
            headers.index(normalized_header)
            if normalized_header in headers
            else fallback_index
        )

    return columns


def build_summary_row(
    row: Sequence[CellValue],
    columns: dict[str, int],
    today: date,
) -> JsonObject | None:
    """
    Convierte una fila de MPB si es AER/T&M en progreso.

    Args:
        row: Fila de MPB.
        columns: Indices de columna.
        today: Fecha local de hoy.

    Returns:
        La fila del resumen, o None si no aplica.
    """
    service = normalize_mpb(read_cell(row, columns["service"]))
    status = normalize_mpb(read_cell(row, columns["status"]))
    project_id = to_text(read_cell(row, columns["project_id"])).strip()

    if not AER_TYM_SERVICE.match(service):
        return None

    if not IN_PROGRESS_STATUS.match(status) or not project_id:
        return None

    budget = parse_mpb_hours(read_cell(row, columns["budget"]))
    stored_burn = parse_mpb_number(read_cell(row, columns["burn"]))
    burn = stored_burn if stored_burn is not None and stored_burn >= 0 else None
    end_date = parse_mpb_date(read_cell(row, columns["end"]))
    manager = to_text(read_cell(row, columns["manager"])).strip()

    return {
        "idProyecto": project_id,
        "cliente": to_text(read_cell(row, columns["client"])).strip(),
        "servicio": SERVICE_AER if service == "aer" else SERVICE_TYM,
        "nombre": to_text(read_cell(row, columns["name"])).strip(),
        "deliveryManager": manager or UNASSIGNED_MANAGER,
        "fte": parse_mpb_hours(read_cell(row, columns["fte"])),
        "ftePorRol": {
            role: parse_mpb_hours(read_cell(row, column_index))
            for role, column_index in ROLE_COLUMNS.items()
        },
        "fechaInicio": parse_mpb_date(read_cell(row, columns["start"])),
        "fechaFin": end_date,
        "budget": budget,
        "burn": burn,
        "clockifyPending": True,
        # El avance de este reporte es consumo / presupuesto.
        "avance": (
            round_half_up(burn / budget * 100, 1)
            if burn is not None and budget > 0
            else None
        ),
        "renewalDias": calculate_renewal_days(end_date, today),
        "etc": None if burn is None else round_half_up(budget - burn, 2),
    }


def calculate_renewal_days(end_date_text: str, today: date) -> int | None:
    """
    Calcula los dias que faltan para la fecha fin.

    Args:
        end_date_text: Fecha fin YYYY-MM-DD.
        today: Fecha local de hoy.

    Returns:
        Dias hasta la fecha fin (negativo si ya paso), o None.
    """
    if not end_date_text:
        return None

    try:
        end_date = date.fromisoformat(end_date_text)
    except ValueError:
        # Fecha imposible en MPB: no se calcula la renovacion.
        return None

    return round_half_up_int((end_date - today).days)
