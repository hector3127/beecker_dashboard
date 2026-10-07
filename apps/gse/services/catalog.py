"""Catalogo de proyectos y categorias de las horas de GSE."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from apps.gse.constants import (
    BILLABLE,
    CATALOG_ID_COLUMN,
    CATALOG_OPERATION_COLUMN,
    CATALOG_SERVICE_COLUMN,
    CATALOG_SHEET_KEYS,
    CATALOG_TYPE_COLUMN,
    NO_SUFFIX_VARIANT,
    NON_BILLABLE,
    OPERATION_RULES,
    OWN_SUFFIX,
    SUFFIX_IN_TEXT,
    TEXT_RULES,
)
from apps.gse.exceptions import GseError
from apps.gse.services.cells import cell_at, norm, trimmed
from core.exceptions import DashboardError, describe_error
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue
from core.utils.text import to_text

"""BKD.100.005 - Catalogo de GSE
Equivale a gseCatalogo_(), gseFichaCatalogo_() y gseCategorias_():
clasifica cada registro con la ficha de CatalagoProyectos.
"""


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """Ficha de un proyecto en el catalogo."""

    operation: str
    kind: str
    operation_name: str
    kind_name: str
    service: str


@dataclass(slots=True)
class Catalog:
    """Fichas por ID normalizado; error si el catalogo no se pudo leer."""

    entries: dict[str, CatalogEntry] = field(default_factory=dict)
    error: str = ""


@dataclass(frozen=True, slots=True)
class CatalogMatch:
    """ID de la variante encontrada y su ficha."""

    project_id: str
    entry: CatalogEntry


def load_catalog(reader: SheetReader) -> Catalog:
    """
    Lee el catalogo; si falla, devuelve uno vacio con el motivo.

    Args:
        reader: Repositorio de Sheets.

    Returns:
        El catalogo; con error cuando la hoja falta o se contradice.
    """
    try:
        return Catalog(entries=read_catalog_entries(reader))
    except DashboardError as error:
        return Catalog(error=describe_error(error))


def read_catalog_entries(reader: SheetReader) -> dict[str, CatalogEntry]:
    """
    Lee las fichas de la hoja CatalagoProyectos.

    Args:
        reader: Repositorio de Sheets.

    Returns:
        Fichas por ID normalizado.

    Raises:
        GseError: Cuando falta la hoja o dos filas se contradicen.
    """
    sheet_name = find_catalog_sheet(reader)

    if sheet_name is None:
        raise GseError("No se encontró CatalagoProyectos.")

    entries: dict[str, CatalogEntry] = {}

    for row_number, row in enumerate(reader.read_values(sheet_name)[1:], 2):
        key = norm(cell_at(row, CATALOG_ID_COLUMN))

        if not key:
            continue

        entry = build_entry(row)
        previous = entries.get(key)

        if previous is not None:
            entry = merge_entry(previous, entry, row, row_number)

        entries[key] = entry

    return entries


def find_catalog_sheet(reader: SheetReader) -> str | None:
    """Nombre de la hoja del catalogo (con o sin la errata original)."""
    for name in reader.list_sheet_names():
        if norm(name).replace(" ", "") in CATALOG_SHEET_KEYS:
            return name

    return None


def build_entry(row: Sequence[CellValue]) -> CatalogEntry:
    """Ficha de una fila: B operacion, C tipo, I servicio."""
    operation = cell_at(row, CATALOG_OPERATION_COLUMN)
    kind = cell_at(row, CATALOG_TYPE_COLUMN)

    return CatalogEntry(
        operation=norm(operation),
        kind=norm(kind),
        operation_name=trimmed(operation),
        kind_name=trimmed(kind),
        service=trimmed(cell_at(row, CATALOG_SERVICE_COLUMN)),
    )


def merge_entry(
    previous: CatalogEntry,
    entry: CatalogEntry,
    row: Sequence[CellValue],
    row_number: int,
) -> CatalogEntry:
    """
    Combina dos filas del mismo ID.

    Raises:
        GseError: Cuando la operacion o el tipo no coinciden.
    """
    if previous.operation != entry.operation or previous.kind != entry.kind:
        raise GseError(
            "Clasificación contradictoria en catálogo para "
            f"{to_text(cell_at(row, CATALOG_ID_COLUMN))} "
            f"(fila {row_number}).",
        )

    if entry.service:
        return entry

    return CatalogEntry(
        operation=entry.operation,
        kind=entry.kind,
        operation_name=entry.operation_name,
        kind_name=entry.kind_name,
        service=previous.service,
    )


def find_catalog_match(
    project_name: str,
    task_name: str,
    catalog: Catalog,
) -> CatalogMatch | None:
    """
    Busca la ficha del registro por su proyecto y el sufijo del task.

    Args:
        project_name: Proyecto del registro.
        task_name: Task del registro.
        catalog: Catalogo de proyectos.

    Returns:
        La variante (S1, CR1...) o el proyecto base con su ficha; None
        si no esta en el catalogo.

    Raises:
        GseError: Cuando el task trae sufijos distintos.
    """
    project = project_name.strip()
    task = task_name
    base = NO_SUFFIX_VARIANT.sub("", project)
    suffixes = list(
        dict.fromkeys(
            match.group(1).upper() for match in SUFFIX_IN_TEXT.finditer(task)
        ),
    )

    if len(suffixes) > 1:
        raise GseError(
            f"Task con sufijos contradictorios: {task} ({project}).",
        )

    own_suffix = OWN_SUFFIX.search(project)
    suffix = suffixes[0] if suffixes else ""

    if not suffix and own_suffix:
        suffix = own_suffix.group(1).upper()

    if suffix:
        variant = f"{base}_{suffix}"
        entry = catalog.entries.get(norm(variant))

        if entry is not None:
            return CatalogMatch(variant, entry)

    entry = catalog.entries.get(norm(base))

    return CatalogMatch(base, entry) if entry is not None else None


def build_categories(
    record: tuple[str, str, Sequence[str]],
    catalog: Catalog,
) -> list[str]:
    """
    Categorias del registro, en el orden del original.

    Args:
        record: Proyecto, task y tags del registro.
        catalog: Catalogo de proyectos.

    Returns:
        Las categorias que aplican (puede traer varias).
    """
    project_name, task_name, raw_tags = record
    project = norm(project_name)
    task = norm(task_name)
    tags = norm(" ".join(raw_tags))
    match = find_catalog_match(project_name, task_name, catalog)
    entry = match.entry if match else None
    result: list[str] = []

    if entry is not None and entry.kind == "facturable":
        result.append(BILLABLE)

    if "000" in project_name:
        result.append(NON_BILLABLE)

    for label, aliases in TEXT_RULES:
        if any(
            project == alias or task == alias or f" {alias} " in f" {tags} "
            for alias in aliases
        ):
            result.append(label)

    if project == "administrative activities":
        result.append("Administrativas")

    operation = entry.operation if entry is not None else None

    for label, aliases in OPERATION_RULES:
        if operation in aliases:
            result.append(label)

    return result
