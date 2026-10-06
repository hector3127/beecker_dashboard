"""Horas consumidas en Clockify de los proyectos AER/T&M."""

from collections.abc import Callable, Sequence
from datetime import date
from typing import Any

from apps.ejecutivo.constants import CONSUMPTION_BATCH_SIZE
from apps.ejecutivo.services.mpb_values import normalize_mpb
from core.exceptions import DashboardError
from core.time_entries.models import TimeEntry
from core.utils.numbers import round_half_up

"""BKD.040.004 - Consumo AER/T&M
Equivale a obtenerConsumosResumenAERTYMMPB(): para cada proyecto suma
todas las horas registradas en Clockify desde INICIO de MPB hasta hoy.
Se atienden dos proyectos por llamada.
"""

JsonObject = dict[str, Any]

ProjectLoader = Callable[[str, tuple[date, date]], list[TimeEntry]]


def build_consumption_items(
    requested_ids: Sequence[object],
    summary_rows: Sequence[JsonObject],
    load_project_entries: ProjectLoader,
    today: date,
) -> list[JsonObject]:
    """
    Calcula las horas consumidas de hasta dos proyectos.

    Args:
        requested_ids: IDs que pide el panel.
        summary_rows: Filas del resumen AER/T&M vigente.
        load_project_entries: Lee los registros de un proyecto y rango.
        today: Fecha local de hoy.

    Returns:
        Un elemento por ID con burn o con el error.
    """
    rows_by_id = {normalize_mpb(row["idProyecto"]): row for row in summary_rows}

    return [
        build_consumption_item(
            str(requested_id),
            rows_by_id,
            load_project_entries,
            today,
        )
        for requested_id in list(requested_ids)[:CONSUMPTION_BATCH_SIZE]
    ]


def build_consumption_item(
    requested_id: str,
    rows_by_id: dict[str, JsonObject],
    load_project_entries: ProjectLoader,
    today: date,
) -> JsonObject:
    """
    Calcula las horas de un proyecto.

    Args:
        requested_id: ID que pide el panel.
        rows_by_id: Filas del resumen por ID normalizado.
        load_project_entries: Lee los registros de un proyecto y rango.
        today: Fecha local de hoy.

    Returns:
        {"id", "burn"} o {"id", "error"}.
    """
    summary_row = rows_by_id.get(normalize_mpb(requested_id))

    if summary_row is None:
        return {"id": requested_id, "error": "Proyecto no vigente en MPB"}

    project_id = summary_row["idProyecto"]

    if not summary_row["fechaInicio"]:
        return {"id": project_id, "error": "No hay fecha INICIO en MPB"}

    try:
        start_date = date.fromisoformat(summary_row["fechaInicio"])
    except ValueError:
        return {
            "id": project_id,
            "error": "La fecha INICIO de MPB no es valida",
        }

    try:
        entries = load_project_entries(project_id, (start_date, today))
    except DashboardError as error:
        return {"id": project_id, "error": error.detail}

    total_hours = sum(
        entry.duration_hours
        for entry in entries
        if entry.entry_date is not None
        and start_date <= entry.entry_date.date() <= today
    )

    return {"id": project_id, "burn": round_half_up(total_hours, 2)}
