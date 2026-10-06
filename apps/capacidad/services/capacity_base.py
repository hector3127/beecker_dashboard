"""Asignaciones del mes desde Recursos y Bandas/rol."""

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

from apps.capacidad.constants import (
    DEFAULT_RESOURCE_TYPE,
    INACTIVE_STATES,
    MONTH_NAMES,
    MONTH_PATTERN,
    NO_BAND,
    PROJECT_CONCEPT,
    SOURCES,
    UNASSIGNED_CONCEPT,
)
from apps.capacidad.exceptions import CapacityError
from apps.capacidad.services.capacity_text import (
    find_concept_rule,
    normalize_capacity_text,
    parse_capacity_number,
)
from apps.capacidad.services.mpb_projects import (
    MpbProject,
    find_mpb_project,
)
from apps.capacidad.services.sheet_table import SheetTable, read_cell
from core.exceptions import SheetsError
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue
from core.utils.text import to_text

"""BKD.050.007 - Base de Capacidad instalada
Equivale a capacidadInstaladaBase(mes):
- La banda sale de la columna del mes en Bandas/rol (o de Banda fija).
- Los recursos con banda "Baja" se excluyen.
- Cada asignacion de Recursos es una fila; los recursos vigentes sin
  asignacion aparecen como "Sin Asignacion".
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]


@dataclass(slots=True)
class CapacitySources:
    """Hojas ya leidas que necesita la base de capacidad."""

    bands: SheetTable
    resources: SheetTable
    projects: list[dict[str, CellValue]]
    delivery_managers: Mapping[str, str]
    mpb_projects: dict[str, MpbProject]


@dataclass(slots=True)
class BandColumn:
    """Columna de banda elegida para el mes."""

    index: int
    month_name: str


def parse_month(month: object, today: date) -> str:
    """
    Valida el mes solicitado; vacio significa el mes actual.

    Args:
        month: Mes enviado por el frontend (YYYY-MM).
        today: Fecha local de hoy.

    Returns:
        El mes en formato YYYY-MM.

    Raises:
        CapacityError: Cuando el mes no tiene el formato YYYY-MM.
    """
    month_text = to_argument_text(month) or today.strftime("%Y-%m")

    if not MONTH_PATTERN.fullmatch(month_text):
        raise CapacityError("Selecciona un mes válido.")

    return month_text


def to_argument_text(month: object) -> str:
    """
    Convierte un argumento del frontend a texto como String(x || '').

    Args:
        month: Valor recibido del frontend.

    Returns:
        El texto, o cadena vacia si el valor es falso.
    """
    if not month:
        return ""

    if isinstance(month, str | int | float | bool):
        return to_text(month)

    return str(month)


def build_capacity_base(
    sources: CapacitySources,
    month: str,
    current_month: str,
) -> JsonObject:
    """
    Construye las asignaciones del mes.

    Args:
        sources: Hojas ya leidas.
        month: Mes solicitado (YYYY-MM).
        current_month: Mes actual (YYYY-MM).

    Returns:
        El mismo objeto que regresaba capacidadInstaladaBase().
    """
    band_column = find_band_column(sources.bands, month)
    people = read_people(sources.bands, band_column.index)
    rows = build_assignment_rows(sources, people)
    assigned_names = {normalize_capacity_text(row["recurso"]) for row in rows}

    for person in people.values():
        if (
            not person["baja"]
            and person["vigente"]
            and normalize_capacity_text(person["nombre"]) not in assigned_names
        ):
            rows.append(build_unassigned_row(person))

    year_text = month[:4]
    band_notice = (
        f"Bandas/rol no tiene columna para {band_column.month_name} "
        f"{year_text}. Banda aparece como NA; el resumen usa solo los "
        "recursos asignados."
        if band_column.index < 0
        else ""
    )

    return {
        "ok": True,
        "mes": month,
        "actual": current_month,
        "filas": rows,
        "personas": [
            person
            for person in people.values()
            if not person["baja"] and person["vigente"]
        ],
        "bandasAviso": band_notice,
        "bandaColumna": (
            to_text(sources.bands.headers[band_column.index])
            if band_column.index >= 0
            else ""
        ),
        "fuentes": list(SOURCES),
    }


def find_band_column(bands: SheetTable, month: str) -> BandColumn:
    """
    Elige la columna de banda: la del mes, la del nombre del mes o Banda.

    Args:
        bands: Tabla de Bandas/rol.
        month: Mes solicitado (YYYY-MM).

    Returns:
        La columna elegida (indice -1 si no hay ninguna).
    """
    month_name = MONTH_NAMES[int(month[5:]) - 1]
    month_with_year = f"{month_name} {month[:4]}"
    normalized_month = normalize_capacity_text(month)
    headers = [normalize_capacity_text(header) for header in bands.headers]
    candidates = (
        [month_with_year, normalized_month],
        [month_name],
        ["banda", "banda salarial"],
    )

    for accepted_headers in candidates:
        for column_index, header in enumerate(headers):
            if header in accepted_headers:
                return BandColumn(column_index, month_name)

    return BandColumn(-1, month_name)


def read_people(bands: SheetTable, band_index: int) -> dict[str, JsonObject]:
    """
    Lee las personas de Bandas/rol con su banda del mes.

    Args:
        bands: Tabla de Bandas/rol.
        band_index: Columna de banda, o -1 si no hay.

    Returns:
        Nombre normalizado -> persona.
    """
    people: dict[str, JsonObject] = {}

    for row in bands.rows:
        name = to_text(bands.read_field(row, ["Nombre", "Recurso"]) or "")
        name = name.strip()

        if not name:
            continue

        band = (
            to_text(read_cell(row, band_index) or "").strip()
            if band_index >= 0
            else ""
        )
        normalized_band = normalize_capacity_text(band)
        people[normalize_capacity_text(name)] = {
            "nombre": name,
            "banda": band or NO_BAND,
            "rol": to_text(bands.read_field(row, ["ROL", "Rol"]) or "").strip(),
            "baja": normalized_band == "baja",
            "vigente": bool(band) and normalized_band != "na",
            "tipo": to_text(
                bands.read_field(
                    row,
                    ["Tipo recurso", "Tipo de recurso", "Tipo"],
                )
                or DEFAULT_RESOURCE_TYPE,
            ),
        }

    return people


def build_assignment_rows(
    sources: CapacitySources,
    people: Mapping[str, JsonObject],
) -> list[JsonObject]:
    """
    Convierte cada asignacion de Recursos en una fila, sin repetir.

    Args:
        sources: Hojas ya leidas.
        people: Personas de Bandas/rol.

    Returns:
        Las filas de asignacion.
    """
    resources = sources.resources
    project_names = read_project_names(sources.projects)
    managers = {
        normalize_capacity_text(project_id): manager
        for project_id, manager in sources.delivery_managers.items()
    }
    rows: list[JsonObject] = []
    seen_assignments: set[str] = set()

    for row_offset, row in enumerate(resources.rows):
        name = to_text(
            resources.read_field(
                row,
                [
                    "Nombre del recurso",
                    "Nombre_del_recurso",
                    "Recurso",
                    "Nombre",
                ],
            )
            or "",
        ).strip()

        if not name:
            continue

        project_id = to_text(
            resources.read_field(
                row,
                ["Proyecto", "ID Proyecto", "ID_Proyecto", "Project ID"],
            )
            or "",
        ).strip()
        normalized_name = normalize_capacity_text(name)
        normalized_id = normalize_capacity_text(project_id)
        person = people.get(normalized_name) or {
            "nombre": name,
            "banda": NO_BAND,
            "rol": "",
            "tipo": DEFAULT_RESOURCE_TYPE,
        }

        if person.get("baja"):
            continue

        assignment_key = f"{normalized_name}|{normalized_id}"

        if assignment_key in seen_assignments:
            continue

        seen_assignments.add(assignment_key)
        concept = to_text(
            resources.read_field(row, ["Conceptos", "Concepto"])
            or (PROJECT_CONCEPT if project_id else UNASSIGNED_CONCEPT),
        ).strip()
        resource_type = to_text(
            resources.read_field(row, ["Tipo recurso", "Tipo de recurso"])
            or person["tipo"],
        )
        mpb_project = find_mpb_project(sources.mpb_projects, project_id)
        sheet_row_number = resources.header_index + row_offset + 2
        rows.append(
            {
                "uid": f"R{sheet_row_number}",
                "recurso": name,
                "banda": person["banda"],
                "rol": person["rol"],
                "concepto": concept,
                "tipo": resource_type,
                "regla": find_concept_rule(concept, resource_type),
                "tecnologia": person["rol"] or NO_BAND,
                "manager": (
                    mpb_project.manager
                    if mpb_project
                    else to_text(managers.get(normalized_id) or "")
                ),
                "idProyecto": project_id,
                "proyecto": (
                    mpb_project.name
                    if mpb_project
                    else to_text(
                        resources.read_field(
                            row,
                            ["Nombre Proyecto", "Nombre del proyecto"],
                        )
                        or project_names.get(normalized_id)
                        or project_id,
                    )
                ),
                "iteration": to_text(
                    resources.read_field(
                        row,
                        ["Iteration Path", "Iteracion", "Iteración"],
                    )
                    or "",
                ),
                "horasDiarias": parse_capacity_number(
                    resources.read_field(
                        row,
                        ["Horas diarias", "Horas por día", "Horas_dia"],
                    ),
                ),
                "horasEstimadas": parse_capacity_number(
                    resources.read_field(
                        row,
                        [
                            "Horas Estimadas",
                            "Horas_Estimadas",
                            "HorasEstimadas",
                        ],
                    ),
                ),
                "activo": normalize_capacity_text(
                    resources.read_field(
                        row,
                        ["Estado recurso", "Estado", "Activo"],
                    ),
                )
                not in INACTIVE_STATES,
            },
        )

    return rows


def read_project_names(
    projects: list[dict[str, CellValue]],
) -> dict[str, CellValue]:
    """
    Lee el nombre de cada proyecto de la hoja Proyectos.

    Args:
        projects: Filas de Proyectos como diccionarios.

    Returns:
        ID normalizado -> nombre del proyecto (puede ser vacio).
    """
    names: dict[str, CellValue] = {}

    for project in projects:
        project_id = to_text(
            project.get("ID_Proyecto") or project.get("Project ID") or "",
        ).strip()

        if project_id:
            names[normalize_capacity_text(project_id)] = (
                project.get("Nombre_Proyecto")
                or project.get("Nombre")
                or project.get("Project Name")
                or ""
            )

    return names


def build_unassigned_row(person: Mapping[str, Any]) -> JsonObject:
    """
    Crea la fila de un recurso vigente sin asignaciones.

    Args:
        person: Persona de Bandas/rol.

    Returns:
        La fila "Sin asignacion".
    """
    return {
        "uid": f"SIN-{normalize_capacity_text(person['nombre'])}",
        "recurso": person["nombre"],
        "banda": person["banda"],
        "rol": person["rol"],
        "concepto": UNASSIGNED_CONCEPT,
        "tipo": person["tipo"],
        "regla": find_concept_rule(UNASSIGNED_CONCEPT, person["tipo"]),
        "idProyecto": "",
        "proyecto": "Sin asignación",
        "tecnologia": person["rol"] or NO_BAND,
        "manager": "",
        "iteration": "",
        "horasDiarias": 0,
        "horasEstimadas": 0,
        "activo": True,
    }


def read_optional_projects(reader: SheetReader) -> list[dict[str, CellValue]]:
    """
    Lee la hoja Proyectos; si falla, la base sigue sin sus nombres.

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        Las filas de Proyectos, o lista vacia si no se pudieron leer.
    """
    try:
        return reader.read_as_objects(sheet_names.SHEET_PROJECTS)
    except SheetsError as error:
        logger.info("Capacidad: metadatos de proyectos: %s", error.detail)
        return []
