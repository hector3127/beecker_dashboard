"""Seleccion de la fuente de registros de tiempo segun settings."""

from django.conf import settings

from core.exceptions import ConfigurationError
from core.sheets.protocols import SheetReader
from core.time_entries.protocols import TimeEntryProvider
from core.time_entries.sheet_provider import SheetTimeEntryProvider

"""BKD.005.004 - Fabrica de fuentes de horas
Elige la fuente configurada en TIME_ENTRY_SOURCE.
"""

SOURCE_SHEET = "sheet"

SOURCE_CLOCKIFY = "clockify"


def build_time_entry_provider(reader: SheetReader) -> TimeEntryProvider:
    """
    Crea la fuente de horas configurada.

    Args:
        reader: Repositorio de Sheets de la peticion actual.

    Returns:
        La fuente de registros de tiempo.

    Raises:
        ConfigurationError: Cuando el valor configurado no existe.
    """
    source = settings.TIME_ENTRY_SOURCE

    if source == SOURCE_SHEET:
        return SheetTimeEntryProvider(reader)

    if source == SOURCE_CLOCKIFY:
        # Se importa aqui para que core no dependa de la app al cargar.
        from apps.clockify.provider import ClockifyTimeEntryProvider

        return ClockifyTimeEntryProvider(reader)

    raise ConfigurationError(
        f"TIME_ENTRY_SOURCE={source} no es valido; usa sheet o clockify.",
    )
