"""Lectura forzada de las hojas que usa GSE."""

from typing import Any

from apps.gse.constants import CONTROL_SHEET, SHEET_ROSTER
from apps.gse.services.base_store import base_sheet_title

"""BKD.100.016 - Lectura forzada de GSE
Apoya al boton Actualizar sin cache: descarta las lecturas guardadas de
Bandas/rol, CatalagoProyectos, GSE_Base_Control y la base del ano para
que la siguiente consulta las vuelva a pedir a Google Sheets.
"""

CATALOG_SHEET = "CatalagoProyectos"


def refresh_sheet_reads(reader: Any, year: object) -> None:
    """
    Fuerza a leer de nuevo las hojas que usa GSE.

    Args:
        reader: Repositorio de Sheets de la peticion.
        year: Ano de la base; si no es valido solo se renuevan las demas.
    """
    wanted = {SHEET_ROSTER, CATALOG_SHEET, CONTROL_SHEET}

    if isinstance(year, int | str) and str(year).strip():
        wanted.add(base_sheet_title(str(year).strip()))

    reader.forget_reads(
        [name for name in reader.list_sheet_names() if name.strip() in wanted],
    )
