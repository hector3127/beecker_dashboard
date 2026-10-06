"""Acceso compartido a las hojas propias de la vista IXS."""

import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.exceptions import DashboardError, describe_error
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.cell_types import CellValue
from core.utils.dates import to_local_naive, to_utc_iso
from core.utils.js_values import js_or_text
from core.utils.locks import script_lock

"""BKD.070.015 - Hojas de la vista IXS
Contexto (lector, escritor, reloj y generador de UID), candado de
escritura como ixsCALock_() y conversiones con las reglas de JavaScript
que usan las funciones ixs* y beeCom* de DailyPanelService.gs.
"""

JsonObject = dict[str, Any]

LOCK_TIMEOUT_SECONDS = 20
MAX_PROJECT_ID_LENGTH = 100


class IxsError(DashboardError):
    """Error de la vista IXS con el mensaje del original."""

    code = "ERR_IXS"
    expose_detail = True


@dataclass(slots=True)
class IxsStore:
    """Hojas de la vista IXS con el reloj y los UID inyectables."""

    reader: SheetReader
    writer: SheetWriter
    now: datetime
    new_uid: Callable[[], str] = field(default=lambda: str(uuid.uuid4()))

    def values(self, sheet_name: str) -> list[list[CellValue]]:
        """
        Valores de la hoja (vacio si no existe).

        Args:
            sheet_name: Nombre de la hoja.

        Returns:
            Las filas, incluida la de encabezados.
        """
        if not self.reader.sheet_exists(sheet_name):
            return []

        return [list(row) for row in self.reader.read_values(sheet_name)]

    def iso_now(self) -> str:
        """Fecha actual como new Date().toISOString()."""
        return to_utc_iso(self.now)

    def local_now(self) -> datetime:
        """Fecha actual en la zona horaria del script."""
        return to_local_naive(self.now) if self.now.tzinfo else self.now


def write_lock() -> AbstractContextManager[None]:
    """Candado de escritura como lock.waitLock(20000)."""
    return script_lock(LOCK_TIMEOUT_SECONDS)


def cell(row: list[CellValue], index: int) -> CellValue:
    """Celda de la fila; vacia si la fila es mas corta."""
    return row[index] if 0 <= index < len(row) else ""


def project_id(value: object) -> str:
    """
    Valida el ID del proyecto, como ixsCAId_().

    Args:
        value: ID recibido.

    Returns:
        El ID sin espacios externos.

    Raises:
        IxsError: Si esta vacio o tiene mas de 100 caracteres.
    """
    text = js_or_text(value).strip()

    if not text or len(text) > MAX_PROJECT_ID_LENGTH:
        raise IxsError("ID de proyecto inválido.")

    return text


def run_safely(action: Callable[[], JsonObject]) -> JsonObject:
    """
    Ejecuta la accion y convierte el error al formato del original.

    Args:
        action: Funcion a ejecutar.

    Returns:
        La respuesta, o {"ok": False, "error"}.
    """
    try:
        return action()
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}
