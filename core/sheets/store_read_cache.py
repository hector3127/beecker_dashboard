"""Cache de lecturas de Sheets respaldada por la base diaria."""

from collections.abc import Iterable
from typing import Any, Final

from django.apps import apps
from django.db import DatabaseError, transaction
from django.db.models import Manager
from django.utils import timezone

from core.data_cache import bump_revision
from core.exceptions import DashboardError
from core.sheets.read_cache import SheetReadCache, SheetValues

"""BKD.004.009 - Hojas guardadas en la base
Las hojas de entrada del portal se guardan completas en la base cuando
corre sync_datastore y las pantallas las leen de ahi, sin vencimiento: no
consultan Google al navegar, cambiar un filtro o recargar. Una escritura
de la app borra la hoja guardada; la siguiente lectura la pide a Google y
la vuelve a guardar. Si la base no responde se usa la cache normal.
"""

# Hojas que el portal lee y que se guardan en la base (las que no existen
# en el Spreadsheet se omiten). Las grandes de Clockify no entran: las
# horas viven en clockify_time_entry.
STORED_SHEETS: Final[tuple[str, ...]] = (
    "Proyectos",
    "Historico_Proyectos",
    "MPB",
    "ROC",
    "DataRevenue",
    "Recursos",
    "Riesgos",
    "Bandas/rol",
    "Master rates",
    "Banda salarial",
    "Backlog_Proyectos",
    "CatalagoProyectos",
    "Clockify_Vinculos",
    "WorkItems_Avance",
)
SHEET_IDS_NAME: Final[str] = "__sheet_ids__"
MODEL_LABEL: Final[tuple[str, str]] = ("datastore", "SheetSnapshot")

# Una copia por proceso: se vuelve a leer de la base solo si cambio.
_memory: dict[str, tuple[object, object]] = {}


class SnapshotValidationError(DashboardError):
    """La fuente no puede sustituir un encabezado por un error de fórmula."""

    code = "ERR_SHEET_SNAPSHOT"
    expose_detail = True


def validate_snapshot(name: str, rows: object) -> None:
    """Rechaza encabezados corruptos sin interpretar ni cambiar sus datos."""
    errors = (
        "#REF!",
        "#VALUE!",
        "#DIV/0!",
        "#NAME?",
        "#NUM!",
        "#ERROR!",
        "#N/A",
    )
    if isinstance(rows, list) and rows and isinstance(rows[0], list):
        for index, value in enumerate(rows[0], start=1):
            if isinstance(value, str) and value.strip().startswith(errors):
                raise SnapshotValidationError(
                    f"{name}: encabezado {index} contiene un error de fórmula. "
                    "Se conserva el último corte válido; "
                    "revisa la hoja de origen."
                )


def _snapshots() -> Manager[Any]:
    """El modelo, buscado al usarlo para no importar apps desde core."""
    manager: Manager[Any] = apps.get_model(*MODEL_LABEL).objects
    return manager


@transaction.atomic
def save_snapshot(name: str, rows: object) -> None:
    """
    Guarda o reemplaza una hoja en la base.

    Args:
        name: Nombre de la hoja (o SHEET_IDS_NAME).
        rows: Matriz de valores, o el diccionario de IDs de hojas.
    """
    validate_snapshot(name, rows)
    now = timezone.now()
    _snapshots().update_or_create(
        name=name,
        defaults={
            "rows": rows,
            "row_count": len(rows) if isinstance(rows, list) else 0,
            "synced_at": now,
        },
    )
    _memory.pop(name, None)
    bump_revision()


@transaction.atomic
def delete_snapshot(name: str) -> None:
    """Borra una hoja guardada."""
    count, _ = _snapshots().filter(name=name).delete()
    if count:
        bump_revision()
    _memory.pop(name, None)


def read_snapshot(name: str) -> object | None:
    """
    Lee una hoja guardada.

    Args:
        name: Nombre de la hoja (o SHEET_IDS_NAME).

    Returns:
        Los valores, o None si la hoja no esta guardada.
    """
    stamp = (
        _snapshots().filter(name=name).values_list("synced_at", flat=True)
    ).first()
    if stamp is None:
        _memory.pop(name, None)
        return None
    cached = _memory.get(name)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    rows: object = _snapshots().values_list("rows", flat=True).get(name=name)
    _memory[name] = (stamp, rows)
    return rows


class StoredSheetReadCache(SheetReadCache):
    """Entrega de la base las hojas guardadas y de la cache las demas."""

    def __init__(
        self,
        spreadsheet_id: str,
        seconds: int,
        stored: Iterable[str] = STORED_SHEETS,
    ) -> None:
        super().__init__(spreadsheet_id, seconds)
        self._stored = frozenset(stored)

    def get_values(self, sheet_name: str) -> SheetValues | None:
        """Hoja guardada en la base; si no esta, la cache normal."""
        if sheet_name in self._stored:
            try:
                rows = read_snapshot(sheet_name)
            except DatabaseError:
                rows = None
            if isinstance(rows, list):
                # Copia de las filas: los servicios pueden modificarlas.
                return [list(row) for row in rows]
        return super().get_values(sheet_name)

    def set_values(self, sheet_name: str, values: SheetValues) -> None:
        """Guarda la hoja en la base si es de las guardadas."""
        if sheet_name in self._stored:
            try:
                save_snapshot(sheet_name, values)
                return
            except DatabaseError:
                pass
        super().set_values(sheet_name, values)

    def invalidate_values(self, sheet_name: str) -> None:
        """Borra la hoja guardada para que la siguiente lectura la renueve."""
        if sheet_name in self._stored:
            try:
                delete_snapshot(sheet_name)
            except DatabaseError:
                pass
        super().invalidate_values(sheet_name)

    def get_sheet_ids(self) -> dict[str, int] | None:
        """Nombres e IDs de las hojas guardados en la base."""
        try:
            stored = read_snapshot(SHEET_IDS_NAME)
        except DatabaseError:
            stored = None
        if isinstance(stored, dict):
            return {name: int(sheet_id) for name, sheet_id in stored.items()}
        return super().get_sheet_ids()

    def set_sheet_ids(self, sheet_ids: dict[str, int]) -> None:
        """Guarda los nombres e IDs de las hojas en la base."""
        try:
            save_snapshot(SHEET_IDS_NAME, sheet_ids)
        except DatabaseError:
            super().set_sheet_ids(sheet_ids)

    def invalidate_sheet_ids(self) -> None:
        """Borra los nombres de hojas (se creo o elimino una pestana)."""
        try:
            delete_snapshot(SHEET_IDS_NAME)
        except DatabaseError:
            pass
        super().invalidate_sheet_ids()
