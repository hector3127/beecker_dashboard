"""Estructuras de datos de los registros de tiempo."""

from dataclasses import dataclass, field
from datetime import datetime

"""BKD.005.001 - Registros de tiempo
Representa una entrada de horas con el mismo contenido que regresaba
leerRegistrosTiempo() en RecursosDetalleService.gs.
"""


@dataclass(frozen=True, slots=True)
class TimeEntry:
    """Una entrada de horas registrada por un recurso."""

    entry_id: str
    project_id: str
    resource_name: str
    entry_date: datetime | None
    duration_hours: float
    is_billable: bool
    costing_rate: float
    description: str = ""
    # Tags y tarea de Clockify: definen la nomenclatura S#/CR# del registro.
    tags: tuple[str, ...] = ()
    task_name: str = ""
    task_id: str = ""
    # Inicio y fin reales en hora local (fechaInicioCompleta y
    # fechaFinCompleta de Clockify); None cuando la fuente no los trae.
    started_at: datetime | None = None
    ended_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class TimeEntryBatch:
    """Conjunto de registros y su procedencia."""

    entries: tuple[TimeEntry, ...]

    # Equivale a la bandera _clockifyRespaldo: los datos vienen del
    # ultimo corte completo porque la consulta en linea fallo.
    is_backup: bool = False
    backup_date: str = ""
    backup_error: str = ""
    warnings: tuple[str, ...] = field(default_factory=tuple)
