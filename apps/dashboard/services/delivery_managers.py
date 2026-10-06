"""Delivery Manager de cada proyecto segun Historico_Proyectos."""

import logging

from core.exceptions import SheetNotFoundError
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader
from core.utils.text import get_flexible_value, to_text

"""BKD.010.015 - Delivery Managers
Equivale a _mapaDeliveryManagerPorProyecto(): toma el primer Delivery
Manager registrado para cada proyecto.
"""

logger = logging.getLogger(__name__)

PROJECT_ID_COLUMNS = ("Project ID", "ID_Proyecto")

DELIVERY_MANAGER_COLUMNS = ("Delivery Manager", "Delivery Manag", "DM")


def load_delivery_managers(reader: SheetReader) -> dict[str, str]:
    """
    Lee el Delivery Manager de cada proyecto.

    Args:
        reader: Repositorio de lectura de Sheets.

    Returns:
        ID de proyecto -> Delivery Manager; vacio si no hay historico.
    """
    try:
        history_rows = reader.read_as_objects(
            sheet_names.SHEET_PROJECTS_HISTORY,
        )
    except SheetNotFoundError:
        logger.info("No existe Historico_Proyectos; se omiten los DM.")
        return {}

    manager_by_project: dict[str, str] = {}

    for history_row in history_rows:
        project_id = to_text(
            get_flexible_value(history_row, PROJECT_ID_COLUMNS),
        )
        delivery_manager = to_text(
            get_flexible_value(history_row, DELIVERY_MANAGER_COLUMNS),
        )

        if (
            project_id
            and delivery_manager
            and project_id not in manager_by_project
        ):
            manager_by_project[project_id] = delivery_manager

    return manager_by_project
