"""Contrato de las fuentes de registros de tiempo."""

from typing import Protocol

from core.time_entries.models import TimeEntryBatch

"""BKD.005.002 - Contrato de fuentes de horas
Permite cambiar entre Clockify y la hoja Registros_Tiempo sin tocar
los calculos del dashboard.
"""


class TimeEntryProvider(Protocol):
    """Fuente de registros de tiempo para todo el portafolio."""

    def load_time_entries(self) -> TimeEntryBatch:
        """Regresa todos los registros de tiempo disponibles."""
        ...
