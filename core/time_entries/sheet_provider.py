"""Lectura de registros de tiempo desde la hoja Registros_Tiempo."""

from core.sheets import sheet_names
from core.sheets.protocols import SheetReader
from core.time_entries.models import TimeEntry, TimeEntryBatch
from core.utils.cell_types import SheetRow
from core.utils.dates import to_datetime
from core.utils.numbers import to_number
from core.utils.text import get_flexible_value, normalize_name, to_text

"""BKD.005.003 - Horas desde Google Sheets
Lee la hoja Registros_Tiempo, la fuente que usaba el sistema antes de
conectarse a Clockify.
"""

BILLABLE_VALUES = frozenset({"yes", "si", "true", "1", "fact"})


class SheetTimeEntryProvider:
    """Fuente de horas basada en la hoja Registros_Tiempo."""

    def __init__(self, reader: SheetReader) -> None:
        self._reader = reader

    def load_time_entries(self) -> TimeEntryBatch:
        """
        Lee todos los registros de la hoja.

        Returns:
            Los registros convertidos a TimeEntry.
        """
        rows = self._reader.read_as_objects(sheet_names.SHEET_TIME_ENTRIES)

        return TimeEntryBatch(
            entries=tuple(build_time_entry(row) for row in rows),
        )


def build_time_entry(row: SheetRow) -> TimeEntry:
    """
    Convierte una fila de Registros_Tiempo en TimeEntry.

    Args:
        row: Fila de la hoja.

    Returns:
        El registro de tiempo equivalente.
    """
    billable_text = normalize_name(get_flexible_value(row, ["Billable"]))

    return TimeEntry(
        entry_id=to_text(get_flexible_value(row, ["ID_Registro"])),
        project_id=to_text(get_flexible_value(row, ["Proyecto"])),
        resource_name=to_text(get_flexible_value(row, ["Recurso"])),
        entry_date=to_datetime(get_flexible_value(row, ["Fecha"])),
        duration_hours=to_number(
            get_flexible_value(row, ["Duracion_Hrs", "Duracion"]),
        ),
        is_billable=billable_text in BILLABLE_VALUES,
        costing_rate=to_number(
            get_flexible_value(row, ["Costing_Rate", "Costing Rate"]),
        ),
        description=to_text(get_flexible_value(row, ["Descripcion"])),
    )
