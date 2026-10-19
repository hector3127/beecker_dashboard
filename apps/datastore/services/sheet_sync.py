"""Guarda en la base las hojas de entrada del portal."""

import logging
from collections.abc import Iterable

from django.db import transaction

from core.sheets.repository import GoogleSheetRepository
from core.sheets.store_read_cache import (
    SHEET_IDS_NAME,
    STORED_SHEETS,
    delete_snapshot,
    save_snapshot,
)

"""BKD.130.007 - Sincronizacion de hojas
Lee de Google, en una sola llamada, las hojas de STORED_SHEETS y las
guarda todas en una transaccion: las pantallas ven el conjunto anterior
hasta que termina y despues el nuevo, nunca una mezcla.
"""

logger = logging.getLogger(__name__)


def sync_sheets(
    repository: GoogleSheetRepository,
    names: Iterable[str] = STORED_SHEETS,
) -> list[str]:
    """
    Guarda las hojas en la base.

    Args:
        repository: Repositorio que lee siempre de Google (sin la base).
        names: Hojas a guardar.

    Returns:
        Las hojas guardadas. Las que no existen en el Spreadsheet se omiten
        y su copia anterior se borra.
    """
    wanted = list(dict.fromkeys(names))
    present = [name for name in wanted if repository.sheet_exists(name)]
    repository.prefetch(present)
    values = {name: repository.read_values(name) for name in present}
    sheet_ids = repository.sheet_ids()
    with transaction.atomic():
        for name, rows in values.items():
            save_snapshot(name, rows)
        for name in wanted:
            if name not in values:
                delete_snapshot(name)
                logger.warning("La hoja %s no existe; no se guardo.", name)
        save_snapshot(SHEET_IDS_NAME, sheet_ids)
    return present
