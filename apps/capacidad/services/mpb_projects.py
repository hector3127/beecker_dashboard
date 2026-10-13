"""Proyectos AER y T&M de la hoja MPB."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from apps.capacidad.constants import MPB_SERVICES, SHEET_MPB
from apps.capacidad.exceptions import CapacityError
from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.capacidad.services.sheet_table import (
    SheetTable,
    read_cell,
    read_sheet_table,
)
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue
from core.utils.dates import to_datetime
from core.utils.text import to_text

"""BKD.050.006 - Proyectos de MPB
Equivale a ciProyectoMPB_(): los proyectos AER/T&M toman inicio, fin,
nombre y Delivery Manager de la hoja MPB.
"""

# Nombres posibles de cada columna de MPB (ya normalizados: "ID_Proyecto"
# queda como "id proyecto").
MPB_ID_ALIASES = ("id", "id proyecto", "id del proyecto", "project id")
MPB_SERVICE_ALIASES = ("service", "servicio")
MPB_START_ALIASES = ("inicio", "fecha inicio", "fecha de inicio", "start")
MPB_END_ALIASES = ("fin", "fecha fin", "fecha de fin", "end")
# Sin encabezado FIN, la fecha fin es la columna I (base 0 = 8), igual que
# en el resumen AER/T&M y en el rango de fechas de Clockify.
MPB_END_FALLBACK_INDEX = 8
MPB_NAME_ALIASES = ("nombre", "nombre proyecto", "nombre del proyecto")
MPB_MANAGER_ALIASES = ("delivery manager", "dm")

ISO_DAY_PREFIX = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
MONTH_DAY_YEAR = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?",
)


@dataclass(frozen=True, slots=True)
class MpbProject:
    """Proyecto de MPB con sus fechas en formato YYYY-MM-DD."""

    project_id: str
    service: str
    start: str
    finish: str
    name: str
    manager: str


def load_mpb_projects(reader: SheetReader) -> dict[str, MpbProject]:
    """
    Lee los proyectos AER/T&M de MPB indexados por ID normalizado.

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        ID normalizado -> proyecto; vacio si no existe la hoja MPB.

    Raises:
        CapacityError: Cuando MPB existe pero no tiene los encabezados.
    """
    if not reader.sheet_exists(SHEET_MPB):
        return {}

    table = read_sheet_table(
        reader,
        SHEET_MPB,
        [
            MPB_ID_ALIASES,
            MPB_SERVICE_ALIASES,
            MPB_START_ALIASES,
        ],
    )
    projects: dict[str, MpbProject] = {}

    for row in table.rows:
        service = normalize_capacity_text(
            table.read_field(row, MPB_SERVICE_ALIASES),
        ).replace(" ", "")

        if service not in MPB_SERVICES:
            continue

        project_id = to_text(
            table.read_field(row, MPB_ID_ALIASES) or ""
        ).strip()

        if not project_id:
            continue

        projects[normalize_capacity_text(project_id)] = MpbProject(
            project_id=project_id,
            service=service,
            start=format_mpb_day(table.read_field(row, MPB_START_ALIASES)),
            finish=format_mpb_day(_read_end(table, row)),
            name=to_text(table.read_field(row, MPB_NAME_ALIASES) or project_id),
            manager=to_text(
                table.read_field(row, MPB_MANAGER_ALIASES) or "",
            ),
        )

    return projects


def _read_end(table: SheetTable, row: Sequence[CellValue]) -> CellValue:
    """Fecha fin: columna FIN, o la columna I si ese encabezado no existe."""
    column = table.find_column(MPB_END_ALIASES)

    return read_cell(row, column if column >= 0 else MPB_END_FALLBACK_INDEX)


def load_optional_mpb_projects(
    reader: SheetReader,
) -> tuple[dict[str, MpbProject], str]:
    """
    Lee MPB sin detener Capacidad instalada si sus encabezados cambiaron.

    MPB solo completa nombre, fechas y Delivery Manager de los proyectos
    AER/T&M; sin ella las asignaciones de Recursos siguen siendo validas.

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        (proyectos, aviso); el aviso queda vacio cuando MPB se leyo bien.
    """
    try:
        return load_mpb_projects(reader), ""
    except CapacityError as error:
        return {}, (
            f"{error.detail} Se muestran las asignaciones sin los datos de "
            "MPB (nombre, fechas y Delivery Manager de AER/T&M)."
        )


def find_mpb_project(
    projects: dict[str, MpbProject],
    project_id: str,
) -> MpbProject | None:
    """
    Busca un proyecto de MPB por su ID.

    Args:
        projects: Proyectos de MPB indexados por ID normalizado.
        project_id: ID del proyecto.

    Returns:
        El proyecto, o None si no es AER/T&M de MPB.
    """
    return projects.get(normalize_capacity_text(project_id))


def format_mpb_day(value: CellValue) -> str:
    """
    Convierte una fecha de MPB a YYYY-MM-DD, como _clockifyFechaYMD().

    Args:
        value: Numero de serie de Sheets (fecha) o texto.

    Returns:
        La fecha YYYY-MM-DD, o cadena vacia si no es una fecha.
    """
    if not value or isinstance(value, bool):
        return ""

    if isinstance(value, int | float):
        moment = to_datetime(value)
        return moment.strftime("%Y-%m-%d") if moment is not None else ""

    text = to_text(value)
    iso_match = ISO_DAY_PREFIX.match(text)

    if iso_match:
        return "-".join(iso_match.groups())

    # new Date("1/15/2026") de JavaScript lee mes/dia/anio.
    month_day_year = MONTH_DAY_YEAR.fullmatch(text.strip())

    if not month_day_year:
        return ""

    month_text, day_text, year_text = month_day_year.groups()

    try:
        return datetime(
            int(year_text),
            int(month_text),
            int(day_text),
        ).strftime("%Y-%m-%d")
    except ValueError:
        # Fecha imposible (mes 13 o 31 de febrero): Invalid Date.
        return ""
