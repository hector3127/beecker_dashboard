"""Lectura por bloques de la base anual de horas."""

import logging
import math
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from apps.capacidad.constants import MONTH_NAMES
from apps.gse.constants import (
    BASE_COLUMNS,
    BATCH_ERROR_VERSION,
    BATCH_REQUIRED_HEADERS,
    BATCH_SIZE,
    BATCH_VERSION,
    BILLABLE,
    NO_SUFFIX_VARIANT,
    NON_BILLABLE,
    NOT_AVAILABLE,
    ROLE_COLUMN,
    SUFFIX_IN_TEXT,
    TAG_SEPARATOR,
    UNCLASSIFIED,
)
from apps.gse.exceptions import GseError
from apps.gse.services.base_store import find_base_sheet
from apps.gse.services.catalog import (
    Catalog,
    build_categories,
    find_catalog_match,
    load_catalog,
)
from apps.gse.services.cells import (
    SheetValues,
    cell_at,
    format_base_date,
    norm,
    trimmed,
)
from apps.gse.services.month_report import GseContext
from apps.gse.services.roster import (
    Person,
    find_band_column,
    read_roster_sheet,
)
from apps.gse.services.year_base import parse_year
from core.exceptions import DashboardError, describe_error
from core.utils.cell_types import CellValue
from core.utils.js_values import js_number, js_truthy
from core.utils.text import to_text

"""BKD.100.010 - Lotes de la base de GSE
Equivale a gseObtenerLoteBase(): devuelve las horas del ano en bloques
de 5,000 filas, de las mas recientes a las mas antiguas.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

MILLISECONDS = 1000


@dataclass(slots=True)
class BatchRoster:
    """Personas de Bandas/rol por nombre y por ID de Clockify."""

    headers: list[str]
    by_name: dict[str, Person] = field(default_factory=dict)
    by_id: dict[str, Person] = field(default_factory=dict)
    ambiguous: set[str] = field(default_factory=set)


@dataclass(slots=True)
class BatchCounts:
    """Filas descartadas de un lote."""

    invalid: int = 0
    unmatched: int = 0


def get_batch(
    context: GseContext,
    request: tuple[object, object, object, object],
    clock: Callable[[], float] = time.monotonic,
) -> JsonObject:
    """
    Lee un bloque de la base y devuelve el error como dato.

    Args:
        context: Hojas, base y fuente de Clockify.
        request: Ano, area, posicion del bloque y filas esperadas.
        clock: Reloj en segundos, para medir la duracion.

    Returns:
        El bloque o {"ok": False, "error", "version"}.
    """
    try:
        return load_batch(context, request, clock)
    except DashboardError as error:
        logger.warning("GSE bloque no disponible: %s", error.detail)

        return {
            "ok": False,
            "error": describe_error(error),
            "version": BATCH_ERROR_VERSION,
        }


def load_batch(
    context: GseContext,
    request: tuple[object, object, object, object],
    clock: Callable[[], float],
) -> JsonObject:
    """
    Lee un bloque de la base anual.

    Raises:
        GseError: Cuando los argumentos, la base o Bandas/rol no sirven.
    """
    started = clock()
    year_value, area_value, cursor_value, expected = request
    year = parse_year(year_value)
    cursor = parse_cursor(cursor_value)

    if year is None or cursor is None:
        raise GseError("Año o posición inválidos.")

    selected_area = area_value if isinstance(area_value, str) else ""
    sheet_name = find_base_sheet(context.reader, year)

    if sheet_name is None:
        raise GseError(f"No existe 08.Base Clockify {year}.")

    values = context.reader.read_values(sheet_name)
    last_row = len(values)
    total = max(0, last_row - 1)

    if expected is not None and js_number(expected) != total:
        raise GseError(
            "La base cambió durante la consulta. Pulsa Consultar año para "
            "leerla nuevamente.",
        )

    headers = read_batch_headers(values)
    roster = read_batch_roster(context)
    catalog = load_catalog(context.reader)
    count = min(BATCH_SIZE, max(0, total - cursor))
    rows = read_block(values, last_row - cursor, count)
    counts = BatchCounts()
    records = [
        record
        for index, row in enumerate(rows)
        if (
            record := read_batch_row(
                row,
                (headers, roster, catalog),
                (year, selected_area, last_row - cursor - index),
                counts,
            )
        )
        is not None
    ]

    return {
        "ok": True,
        "version": BATCH_VERSION,
        "bandas": build_bands(roster, year, selected_area)
        if cursor == 0
        else [],
        "records": records,
        "total": total,
        "cursor": cursor + count,
        "done": cursor + count >= total,
        "invalid": counts.invalid,
        "unmatched": counts.unmatched,
        "catalogoAviso": catalog.error,
        "milliseconds": round((clock() - started) * MILLISECONDS),
    }


def parse_cursor(value: object) -> int | None:
    """Posicion del bloque: entero no negativo; None si no es valida."""
    number = js_number(value if js_truthy(value) else 0)

    if number != number or number != int(number) or number < 0:
        return None

    return int(number)


def read_batch_headers(values: SheetValues) -> list[str]:
    """
    Encabezados de las 12 columnas de la base.

    Raises:
        GseError: Cuando falta una columna que se necesita.
    """
    headers = [
        norm(cell_at(values[0], column) if values else None)
        for column in range(BASE_COLUMNS)
    ]

    if not all(name in headers for name in BATCH_REQUIRED_HEADERS):
        raise GseError(
            "La base requiere el formato GSE de 12 columnas mostrado en "
            "tu captura.",
        )

    return headers


def read_batch_roster(context: GseContext) -> BatchRoster:
    """
    Personas por nombre e ID (el nombre repetido en dos areas es ambiguo).

    Raises:
        GseError: Cuando falta Bandas/rol o hay IDs duplicados.
    """
    sheet = read_roster_sheet(
        context.reader,
        "Bandas/rol requiere Nombre y ROL en columna C.",
        require_role_column=True,
    )
    roster = BatchRoster(sheet.headers)
    name_column = sheet.headers.index("nombre")
    id_column = (
        sheet.headers.index("id clockify")
        if "id clockify" in sheet.headers
        else -1
    )

    for row in sheet.data_rows:
        name = trimmed(cell_at(row, name_column))
        area = trimmed(cell_at(row, ROLE_COLUMN))

        if not name or not area:
            continue

        clockify_id = trimmed(cell_at(row, id_column))
        person = Person(name, area, False, clockify_id, "", row)
        key = norm(name)
        register_person(roster, key, person)

    return roster


def register_person(roster: BatchRoster, key: str, person: Person) -> None:
    """
    Agrega una persona al indice por nombre y por ID.

    Raises:
        GseError: Cuando un ID de Clockify pertenece a dos personas.
    """
    known = roster.by_name.get(key)

    if known is None:
        roster.by_name[key] = person
    elif norm(known.area) != norm(person.area):
        roster.ambiguous.add(key)

    if not person.clockify_id:
        return

    owner = roster.by_id.get(person.clockify_id)

    if owner is not None and norm(owner.name) != key:
        raise GseError("ID Clockify duplicado en Bandas/rol.")

    roster.by_id[person.clockify_id] = person


def read_block(
    values: SheetValues,
    end_row: int,
    count: int,
) -> list[list[CellValue]]:
    """Filas del bloque, de la mas reciente a la mas antigua."""
    if not count:
        return []

    block = values[end_row - count : end_row]

    return [
        [cell_at(row, column) for column in range(BASE_COLUMNS)]
        for row in reversed(block)
    ]


def read_batch_row(
    row: list[CellValue],
    sources: tuple[list[str], BatchRoster, Catalog],
    position: tuple[int, str, int],
    counts: BatchCounts,
) -> JsonObject | None:
    """Convierte una fila de la base; None si no cuenta."""
    headers, roster, catalog = sources
    year, selected_area, row_number = position

    def read(name: str) -> CellValue:
        return row[headers.index(name)] if name in headers else None

    day = format_base_date(read("start date"))

    if not day.startswith(f"{year}-"):
        return None

    hours = js_number(read("duration decimal"))

    if not (math.isfinite(hours) and hours >= 0):
        counts.invalid += 1

        return None

    if not hours:
        return None

    person = find_batch_person(
        trimmed(read("user")),
        trimmed(read("id clockify")),
        roster,
    )

    if person is None:
        counts.unmatched += 1

        return None

    if selected_area and norm(person.area) != norm(selected_area):
        return None

    return build_batch_record(
        (person, day, hours),
        (
            trimmed(read("id registro")) or f"row:{row_number}",
            (
                to_text(read("project")) if js_truthy(read("project")) else "",
                to_text(read("task")) if js_truthy(read("task")) else "",
                TAG_SEPARATOR.split(
                    to_text(read("tags")) if js_truthy(read("tags")) else "",
                ),
            ),
        ),
        (roster, catalog),
    )


def find_batch_person(
    user: str,
    user_id: str,
    roster: BatchRoster,
) -> Person | None:
    """Persona por ID de Clockify o por nombre no ambiguo."""
    person = roster.by_id.get(user_id)

    if person is not None:
        return person

    name_key = norm(user)

    if name_key in roster.ambiguous:
        return None

    return roster.by_name.get(name_key)


def build_batch_record(
    row_info: tuple[Person, str, float],
    record_info: tuple[str, tuple[str, str, Sequence[str]]],
    sources: tuple[BatchRoster, Catalog],
) -> JsonObject:
    """Registro del lote con su banda, categorias y clasificacion."""
    person, day, hours = row_info
    record_id, (project_name, task_name, tags) = record_info
    roster, catalog = sources
    match = find_catalog_match(project_name, task_name, catalog)
    suffix = SUFFIX_IN_TEXT.search(task_name)

    if match is not None:
        project = match.project_id
    elif suffix:
        base = NO_SUFFIX_VARIANT.sub("", project_name)
        project = f"{base}_{suffix.group(1).upper()}"
    else:
        project = project_name

    month_text = day[:7]
    band = find_band_column(roster.headers, int(day[5:7]), day[:4])
    band_value = cell_at(person.row, band)
    categories = build_categories((project_name, task_name, tags), catalog)
    entry = match.entry if match else None

    return {
        "id": record_id,
        "mes": month_text,
        "recurso": person.name,
        "area": person.area,
        "banda": text_or_na(band_value) if band >= 0 else NOT_AVAILABLE,
        "baja": band >= 0 and norm(band_value) == "baja",
        "proyecto": project or "Sin proyecto",
        "servicio": (entry.service if entry else "") or NOT_AVAILABLE,
        "horas": hours,
        "categorias": categories,
        "categoria": (
            (entry.operation_name or UNCLASSIFIED)
            if entry
            else " / ".join(
                name
                for name in categories
                if name not in (BILLABLE, NON_BILLABLE)
            )
            or UNCLASSIFIED
        ),
        "tipo": (entry.kind_name or NOT_AVAILABLE) if entry else NOT_AVAILABLE,
    }


def text_or_na(value: CellValue) -> str:
    """Texto como String(x || 'NA')."""
    return to_text(value) if js_truthy(value) else NOT_AVAILABLE


def build_bands(
    roster: BatchRoster,
    year: int,
    selected_area: str,
) -> list[JsonObject]:
    """Banda de cada mes por persona (las ambiguas se omiten)."""
    bands: list[JsonObject] = []

    for key, person in roster.by_name.items():
        if key in roster.ambiguous:
            continue

        if selected_area and norm(person.area) != norm(selected_area):
            continue

        columns = [
            find_band_column(roster.headers, month, str(year))
            for month in range(1, len(MONTH_NAMES) + 1)
        ]
        bands.append(
            {
                "recurso": person.name,
                "bandas": [
                    text_or_na(cell_at(person.row, column))
                    if column >= 0
                    else NOT_AVAILABLE
                    for column in columns
                ],
            },
        )

    return bands
