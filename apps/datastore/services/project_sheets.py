"""Carga explícita de copias manuales para la integración de proyectos."""

from collections.abc import Iterable
from typing import Any, Protocol

from django.db import transaction

from core.exceptions import DashboardError
from core.sheets.store_read_cache import (
    SHEET_IDS_NAME,
    save_snapshot,
    validate_snapshot,
)
from core.utils.cell_types import CellValue
from core.utils.text import strip_accents

PROJECT_SHEETS: dict[str, frozenset[str]] = {
    "AER_Acciones": frozenset({"UID", "ID_Proyecto", "Accion"}),
    "IXS_Acciones": frozenset({"UID", "ID_Proyecto", "DatosJSON"}),
    "Comunicados": frozenset(),
    "AER_Contactos": frozenset({"UID", "ID_Proyecto"}),
    "AER_ClienteInfo": frozenset({"UID", "ID_Proyecto"}),
    "AER_ClienteGobierno": frozenset({"UID", "ID_Proyecto"}),
    "AER_ClienteDocs": frozenset({"UID", "ID_Proyecto"}),
    "IXS_Cliente_Contactos": frozenset({"UID", "ID_Proyecto", "DatosJSON"}),
    "IXS_Cliente_Info": frozenset({"UID", "ID_Proyecto", "DatosJSON"}),
    "IXS_Cliente_Gobierno": frozenset({"UID", "ID_Proyecto", "DatosJSON"}),
    "IXS_Cliente_Documentos": frozenset({"UID", "ID_Proyecto", "DatosJSON"}),
    "Pendientes_Minutas": frozenset({"ID_Proyecto", "Estado"}),
}


OPTIONAL_PROJECT_SHEETS: dict[str, frozenset[str]] = {
    "AER_Planeacion": frozenset({"UID", "ID_Proyecto", "Actividad"}),
    "AER_Riesgos": frozenset({"UID", "ID_Proyecto", "Riesgo"}),
    "AER_Vacaciones": frozenset(
        {"UID", "ID_Proyecto", "Recurso", "Inicio", "Fin"}
    ),
    "IXS_Planeacion": frozenset({"UID", "ID_Proyecto", "Tipo", "DatosJSON"}),
}
ALLOWED_PROJECT_SHEETS = PROJECT_SHEETS | OPTIONAL_PROJECT_SHEETS


class ProjectSheetReader(Protocol):
    """Operaciones de lectura utilizadas por la carga acotada."""

    def sheet_exists(self, sheet_name: str) -> bool:
        """Confirma si existe la pestaña en el origen."""
        ...

    def prefetch(self, sheet_names: Iterable[str]) -> None:
        """Precarga el conjunto de hojas seleccionado."""
        ...

    def read_values(self, sheet_name: str) -> list[list[CellValue]]:
        """Lee las matrices originales sin transformarlas."""
        ...

    def sheet_ids(self) -> dict[str, int]:
        """Devuelve el catálogo completo de nombres e IDs de origen."""
        ...


class ProjectSheetError(DashboardError):
    """La carga no puede publicarse y conserva las copias anteriores."""

    code = "ERR_PROJECT_SHEETS"
    expose_detail = True


def selected_sheets(names: Iterable[str]) -> list[str]:
    """Valida el alcance explícito sin aceptar tablas ni hojas ajenas."""
    wanted = list(dict.fromkeys(names))
    if not wanted or any(name not in ALLOWED_PROJECT_SHEETS for name in wanted):
        raise ProjectSheetError(
            "Selecciona al menos una hoja de proyectos admitida."
        )
    return wanted


def validate_project_sheet(name: str, rows: list[list[CellValue]]) -> None:
    """Valida encabezados y estructura sin transformar registros."""
    validate_snapshot(name, rows)
    if not rows or any(not isinstance(row, list) for row in rows):
        raise ProjectSheetError(
            f"{name}: falta una matriz con encabezados válidos."
        )
    header = rows[0]
    if name == "Comunicados":
        required = {0: "uid", 1: "fecha", 2: "titulo", 7: "proyecto"}
        valid = all(
            index < len(header)
            and strip_accents(str(header[index])).strip().casefold() == label
            for index, label in required.items()
        )
    else:
        valid = ALLOWED_PROJECT_SHEETS[name] <= {
            cell for cell in header if isinstance(cell, str)
        }
    if not valid:
        raise ProjectSheetError(
            f"{name}: encabezados incompatibles; se conserva la copia anterior."
        )


def sync_project_sheets(
    repository: ProjectSheetReader, names: Iterable[str]
) -> dict[str, int]:
    """Lee y valida antes de publicar en una transacción; nunca borra hojas."""
    wanted = selected_sheets(names)
    missing = [name for name in wanted if not repository.sheet_exists(name)]
    if missing:
        raise ProjectSheetError(
            "No se descargó el conjunto: faltan hojas de origen: "
            + ", ".join(missing)
        )
    repository.prefetch(wanted)
    values = {name: repository.read_values(name) for name in wanted}
    for name, rows in values.items():
        validate_project_sheet(name, rows)
    ids: dict[str, Any] = repository.sheet_ids()
    if not all(name in ids for name in wanted):
        raise ProjectSheetError(
            "El catálogo de origen no confirma todas las hojas seleccionadas."
        )
    with transaction.atomic():
        for name, rows in values.items():
            save_snapshot(name, rows)
        save_snapshot(SHEET_IDS_NAME, ids)
    return {name: len(rows) - 1 for name, rows in values.items()}
