"""Funciones de la vista de Recursos expuestas al frontend por RPC."""

from typing import Any

from django.utils import timezone

from apps.daily.services.ixs_functions import fill_args
from apps.recursos.services import person_detail, summary
from apps.recursos.services.resource_records import (
    Record,
    position_by_person,
    to_records,
)
from core.exceptions import DashboardError, describe_error
from core.rpc.registry import register_rpc
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository
from core.sheets.protocols import SheetReader
from core.time_entries.factory import build_time_entry_provider
from core.utils.cell_types import SheetRow

"""BKD.090.005 - RPC de Recursos
Registra getResumenRecursos, getProyectosConHoras, getPersonasConHoras,
obtenerProyectosAsignadosPersona y getDetallePersona con los mismos
nombres y respuestas que RecursosDetalleService.gs.
"""

JsonObject = dict[str, Any]


def resource_rows(reader: SheetReader) -> list[SheetRow]:
    """Filas de Recursos; vacio si la hoja no existe."""
    if not reader.sheet_exists(sheet_names.SHEET_RESOURCES):
        return []

    return reader.read_as_objects(sheet_names.SHEET_RESOURCES)


def load_records(reader: SheetReader) -> list[Record]:
    """Horas de todo el portafolio (leerRegistrosTiempo)."""
    batch = build_time_entry_provider(reader).load_time_entries()

    return to_records(batch.entries)


@register_rpc("getResumenRecursos")
def get_resources_summary(*args: object) -> JsonObject:
    """Resumen general; si Clockify falla el error llega al frontend."""
    repository = build_sheet_repository()

    return summary.build_summary(
        load_records(repository),
        position_by_person(resource_rows(repository)),
        timezone.localdate(),
    )


@register_rpc("getProyectosConHoras")
def get_projects_with_hours(*args: object) -> list[str]:
    """Proyectos con registros de horas."""
    return summary.projects_with_hours(load_records(build_sheet_repository()))


@register_rpc("getPersonasConHoras")
def get_people_with_hours(*args: object) -> list[str]:
    """Personas con registros de horas."""
    return summary.people_with_hours(load_records(build_sheet_repository()))


@register_rpc("obtenerProyectosAsignadosPersona")
def get_assigned_projects(*args: object) -> JsonObject:
    """Proyectos donde la persona esta asignada en Recursos."""
    (person,) = fill_args(args, 1)

    try:
        rows = build_sheet_repository().read_as_objects(
            sheet_names.SHEET_RESOURCES,
        )
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error), "proyectos": []}

    return person_detail.assigned_projects(person, rows)


@register_rpc("getDetallePersona")
def get_person_detail(*args: object) -> JsonObject:
    """Detalle de horas de una persona agrupado por dia, semana o mes."""
    person, grouping = fill_args(args, 2)

    try:
        repository = build_sheet_repository()
        records = load_records(repository)
        positions = position_by_person(resource_rows(repository))
    except DashboardError as error:
        return person_detail.error_detail(person, describe_error(error))

    return person_detail.person_detail(
        person,
        grouping,
        records,
        positions,
        timezone.localdate(),
    )
