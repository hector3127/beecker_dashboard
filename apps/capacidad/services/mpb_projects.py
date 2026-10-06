"""Proyectos AER y T&M de la hoja MPB."""

import re
from dataclasses import dataclass
from datetime import datetime

from apps.capacidad.constants import MPB_SERVICES, SHEET_MPB
from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.capacidad.services.sheet_table import read_sheet_table
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue
from core.utils.dates import to_datetime
from core.utils.text import to_text

"""BKD.050.006 - Proyectos de MPB
Equivale a ciProyectoMPB_(): los proyectos AER/T&M toman inicio, fin,
nombre y Delivery Manager de la hoja MPB.
"""

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
        [["id"], ["service"], ["inicio"], ["fin"]],
    )
    projects: dict[str, MpbProject] = {}

    for row in table.rows:
        service = normalize_capacity_text(
            table.read_field(row, ["SERVICE"]),
        ).replace(" ", "")

        if service not in MPB_SERVICES:
            continue

        project_id = to_text(table.read_field(row, ["ID"]) or "").strip()

        if not project_id:
            continue

        projects[normalize_capacity_text(project_id)] = MpbProject(
            project_id=project_id,
            service=service,
            start=format_mpb_day(table.read_field(row, ["INICIO"])),
            finish=format_mpb_day(table.read_field(row, ["FIN"])),
            name=to_text(table.read_field(row, ["NOMBRE"]) or project_id),
            manager=to_text(
                table.read_field(row, ["Delivery Manager", "DM"]) or "",
            ),
        )

    return projects


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
