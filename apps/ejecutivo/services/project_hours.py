"""Horas de Clockify de un proyecto respetando su nomenclatura."""

import logging
from collections.abc import Callable, Sequence

from apps.ejecutivo.services.ixb_rules import (
    belongs_to_nomenclature,
    project_nomenclature,
)
from core.exceptions import DashboardError
from core.time_entries.models import TimeEntry
from core.utils.cell_types import SheetRow
from core.utils.text import extract_base_id, get_flexible_value, to_text

"""BKD.040.009 - Horas por nomenclatura
Equivale a obtenerHorasClockifyPorProyectoJerarquia(): en proyectos
IXB/RaaS solo cuentan los registros de la nomenclatura del ID (S1, S2,
CR1); en el resto se usan todos los registros del proyecto.
"""

logger = logging.getLogger(__name__)

ProjectEntriesLoader = Callable[[str], list[TimeEntry]]

HIERARCHY_SERVICES = frozenset(
    {"IXB", "IXB Y RAAS", "POC", "RAAS", "RAAS+", "SAAS"},
)


def load_hierarchy_entries(
    project_id: str,
    project_rows: Sequence[SheetRow],
    load_project_entries: ProjectEntriesLoader,
) -> list[TimeEntry]:
    """
    Lee las horas del proyecto y aplica la nomenclatura IXB/RaaS.

    Args:
        project_id: ID interno del proyecto.
        project_rows: Filas de la hoja Proyectos.
        load_project_entries: Descarga los registros de un proyecto.

    Returns:
        Los registros; lista vacia si Clockify no respondio, igual que
        el original.
    """
    try:
        entries = load_project_entries(project_id)
    except DashboardError as error:
        logger.info("Horas de %s no disponibles: %s", project_id, error.detail)
        return []

    nomenclature = hierarchy_nomenclature(project_id, project_rows)

    if not nomenclature:
        return list(entries)

    return [
        entry
        for entry in entries
        if belongs_to_nomenclature(entry, nomenclature)
    ]


def hierarchy_nomenclature(
    project_id: str,
    project_rows: Sequence[SheetRow],
) -> str:
    """
    Obtiene la nomenclatura del ID, como _clockifyNomenclaturaProyecto().

    Args:
        project_id: ID interno del proyecto.
        project_rows: Filas de la hoja Proyectos.

    Returns:
        S1, S2, CR1... o cadena vacia si el proyecto no es IXB/RaaS.
    """
    clean_id = project_id.strip()

    if not clean_id or not is_ixb_raas_project(clean_id, project_rows):
        return ""

    return project_nomenclature(clean_id)


def is_ixb_raas_project(
    project_id: str,
    project_rows: Sequence[SheetRow],
) -> bool:
    """
    Indica si algun proyecto con el mismo ID base es IXB/RaaS/SaaS.

    Args:
        project_id: ID interno del proyecto.
        project_rows: Filas de la hoja Proyectos.

    Returns:
        True si el servicio pertenece al portafolio IXB/RaaS.
    """
    base_id = extract_base_id(project_id)

    for row in project_rows:
        row_id = to_text(row.get("ID_Proyecto") or "").strip()

        if not row_id or extract_base_id(row_id) != base_id:
            continue

        service = (
            to_text(get_flexible_value(row, ["Servicio", "Service"]) or "")
            .upper()
            .strip()
        )

        if service in HIERARCHY_SERVICES:
            return True

    return False
