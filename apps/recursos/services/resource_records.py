"""Registros de horas con el formato de leerRegistrosTiempo()."""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from core.time_entries.models import TimeEntry
from core.utils.text import get_flexible_value, normalize_name, to_text

"""BKD.090.002 - Registros de Recursos
Convierte los TimeEntry a los campos que usa RecursosDetalleService.gs
(proyecto, recurso, fecha, duracion, billable, inicio y fin) y arma el
mapa de posiciones de la hoja Recursos.
"""

NAME_KEYS = ["Nombre del recurso", "Nombre_del_recurso", "Recurso", "Nombre"]
POSITION_KEYS = ["Posicion", "Posición", "Rol"]
WORK_START_HOUR = 8
WORK_END_HOUR = 18


@dataclass(frozen=True, slots=True)
class Record:
    """Registro de horas de una persona en un proyecto."""

    project: str
    resource: str
    day: str
    description: str
    hours: float
    billable: bool
    started_at: datetime | None
    ended_at: datetime | None

    @property
    def outside_schedule(self) -> bool:
        """Inicio antes de las 8:00 o desde las 18:00 (hora local)."""
        if self.started_at is None:
            return False

        hour = self.started_at.hour

        return hour < WORK_START_HOUR or hour >= WORK_END_HOUR


def day_text(moment: date | None) -> str:
    """YYYY-MM-DD o vacio."""
    return moment.strftime("%Y-%m-%d") if moment else ""


def to_records(entries: Iterable[TimeEntry]) -> list[Record]:
    """Convierte los TimeEntry en el orden recibido."""
    return [
        Record(
            project=entry.project_id,
            resource=entry.resource_name,
            day=day_text(entry.entry_date),
            description=entry.description,
            hours=entry.duration_hours,
            billable=entry.is_billable,
            started_at=entry.started_at,
            ended_at=entry.ended_at,
        )
        for entry in entries
    ]


def position_by_person(rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    """
    Posicion de cada persona en Recursos (_mapaRolPorPersonaGlobal).

    Si una persona aparece varias veces se queda la primera fila.
    """
    positions: dict[str, str] = {}

    for row in rows:
        name = get_flexible_value(row, NAME_KEYS)

        if not name:
            continue

        key = normalize_name(name)

        if not positions.get(key):
            positions[key] = to_text(get_flexible_value(row, POSITION_KEYS))

    return positions


def role_category(role: object) -> str:
    """Categoria del rol (categoriaPorRol)."""
    text = str(role or "").lower()

    if any(word in text for word in ("developer", "ml engineer", "arquitecto")):
        return "Desarrollo"

    if any(word in text for word in ("tester", "code review", "qa")):
        return "Testing"

    if any(word in text for word in ("business analy", "analista")):
        return "Análisis"

    if any(word in text for word in ("scrum master", "pm", "project")):
        return "Soporte"

    return "Otros"
