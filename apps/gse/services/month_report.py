"""Horas de un mes por area, persona y categoria."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from apps.capacidad.constants import MONTH_PATTERN
from apps.gse.constants import (
    BILLABLE,
    KPI_CATEGORIES,
    NO_NAME,
    NO_PROJECT,
    NO_SUFFIX_VARIANT,
    NON_BILLABLE,
    NOT_AVAILABLE,
    ROLE_COLUMN,
    SUFFIX_IN_TEXT,
    UNCLASSIFIED,
)
from apps.gse.exceptions import GseError
from apps.gse.services.base_store import BaseStore, HourRecord
from apps.gse.services.catalog import (
    Catalog,
    CatalogMatch,
    build_categories,
    find_catalog_match,
    load_catalog,
)
from apps.gse.services.cells import cell_at, norm, trimmed
from apps.gse.services.roster import (
    Person,
    RosterSheet,
    find_band_column,
    read_clockify_id,
    read_roster_sheet,
)
from core.exceptions import DashboardError, describe_error
from core.sheets.protocols import SheetReader
from core.utils.text import to_text

"""BKD.100.008 - Horas del mes de GSE
Equivale a gseObtenerMes(): cruza las horas de Clockify (API o base en
Sheets) con Bandas/rol y el catalogo de proyectos.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

SOURCE_SHEET = "sheet"
SOURCE_LABELS = {
    True: "Base Clockify en Sheets",
    False: "API Clockify (registros visibles para la clave)",
}
NOTICE = (
    "Recursos cuenta personas únicas con horas positivas en el mes, "
    "incluyendo BAJA si registraron horas. Área corresponde al ROL "
    "actual."
)
HourLoader = Callable[[str, bool, list[str] | None], list[HourRecord]]


@dataclass(frozen=True, slots=True)
class GseContext:
    """Lo que necesitan las consultas de GSE."""

    reader: SheetReader
    store: BaseStore
    load_api_hours: HourLoader


@dataclass(slots=True)
class PersonTotal:
    """Horas de una persona dentro de su area."""

    name: str
    hours: float
    baja: bool


@dataclass(slots=True)
class AreaTotal:
    """Horas, categorias y personas de un area."""

    area: str
    hours: float = 0.0
    categories: dict[str, float | None] = field(default_factory=dict)
    people: dict[str, PersonTotal] = field(default_factory=dict)

    def to_json(self) -> JsonObject:
        """Area en el formato que espera el frontend."""
        return {
            "area": self.area,
            "recursos": len(self.people),
            "horas": self.hours,
            "categorias": self.categories,
            "personas": [
                {"nombre": item.name, "horas": item.hours, "baja": item.baja}
                for item in self.people.values()
            ],
        }


def get_month(
    context: GseContext,
    request: tuple[object, object, bool, object],
) -> JsonObject:
    """
    Consulta un mes y devuelve el error como dato (gseObtenerMes).

    Args:
        context: Hojas, base y fuente de Clockify.
        request: Mes, fuente ("sheet" o API), forzar y area elegida.

    Returns:
        El resultado del mes o {"ok": False, "mes", "error"}.
    """
    try:
        return build_month(context, request)
    except DashboardError as error:
        logger.warning("GSE mes no disponible: %s", error.detail)

        return {"ok": False, "mes": request[0], "error": describe_error(error)}


def build_month(
    context: GseContext,
    request: tuple[object, object, bool, object],
) -> JsonObject:
    """
    Calcula las horas del mes por area.

    Args:
        context: Hojas, base y fuente de Clockify.
        request: Mes, fuente, forzar y area elegida.

    Returns:
        El resultado con areas, detalle y avisos.

    Raises:
        GseError: Cuando el mes, las hojas o los datos no son validos.
    """
    month_value, source, force, area_value = request

    if not isinstance(month_value, str) or not MONTH_PATTERN.fullmatch(
        month_value,
    ):
        raise GseError("Mes inválido.")

    month = month_value
    selected_area = read_area_argument(area_value)
    sheet = read_roster_sheet(
        context.reader,
        "Bandas/rol requiere Nombre y ROL.",
    )
    band = find_band_column(
        sheet.headers,
        int(month[5:]),
        month[:4],
    )
    catalog = load_catalog(context.reader)
    roster = read_month_roster(sheet, band, selected_area)

    if selected_area and not roster:
        raise GseError("El área seleccionada no tiene personas en Bandas/rol.")

    missing_ids = [
        item.name for item in roster.values() if not item.clockify_id
    ]
    by_id = index_by_clockify_id(roster)
    ids = list(dict.fromkeys(by_id)) if not missing_ids else None
    from_sheet = source == SOURCE_SHEET
    records = (
        context.store.read_sheet_month(month, ids)
        if from_sheet
        else context.load_api_hours(month, force, ids)
    )
    areas = {item.area: AreaTotal(item.area) for item in roster.values()}
    result = accumulate_hours(
        records,
        month,
        (roster, by_id, catalog),
        areas,
        selected_area,
    )

    return build_result(
        (month, from_sheet, band, sheet),
        (areas, missing_ids, catalog),
        result,
    )


def read_area_argument(value: object) -> str:
    """Area elegida como texto; vacio si no viene."""
    return value if isinstance(value, str) else ""


def read_month_roster(
    sheet: RosterSheet,
    band: int,
    selected_area: str,
) -> dict[str, Person]:
    """
    Personas de Bandas/rol (una por nombre) del area elegida.

    Args:
        sheet: Hoja Bandas/rol.
        band: Columna de la banda del mes (-1 si no hay).
        selected_area: Area elegida; vacio para todas.

    Returns:
        Personas por nombre normalizado, en el orden de la hoja.
    """
    name_column = sheet.headers.index("nombre")
    roster: dict[str, Person] = {}

    for row in sheet.data_rows:
        name = trimmed(cell_at(row, name_column))
        area = trimmed(cell_at(row, ROLE_COLUMN))

        if not name or not area:
            continue

        if selected_area and norm(area) != norm(selected_area):
            continue

        key = norm(name)

        if key in roster:
            continue

        band_value = cell_at(row, band)
        roster[key] = Person(
            name=name,
            area=area,
            baja=band >= 0 and norm(band_value) == "baja",
            clockify_id=read_clockify_id(sheet.headers, row),
            band=trimmed(band_value) if band >= 0 else NOT_AVAILABLE,
        )

    return roster


def index_by_clockify_id(roster: dict[str, Person]) -> dict[str, Person]:
    """
    Personas por ID de Clockify.

    Raises:
        GseError: Cuando dos personas comparten el mismo ID.
    """
    by_id: dict[str, Person] = {}

    for person in roster.values():
        if not person.clockify_id:
            continue

        if person.clockify_id in by_id:
            raise GseError(
                f"ID Clockify repetido en Bandas/rol: {person.name}",
            )

        by_id[person.clockify_id] = person

    return by_id


@dataclass(slots=True)
class MonthTotals:
    """Acumulados del mes antes de armar la respuesta."""

    detail: dict[tuple[str, str, str, str], JsonObject] = field(
        default_factory=dict,
    )
    unmatched: dict[str, None] = field(default_factory=dict)
    missing_projects: dict[str, None] = field(default_factory=dict)
    has_hours: bool = False


def accumulate_hours(
    records: Sequence[HourRecord],
    month: str,
    sources: tuple[dict[str, Person], dict[str, Person], Catalog],
    areas: dict[str, AreaTotal],
    selected_area: str,
) -> MonthTotals:
    """
    Suma las horas del mes por area, persona, categoria y detalle.

    Args:
        records: Registros de horas.
        month: Mes YYYY-MM.
        sources: Personas por nombre, por ID y catalogo.
        areas: Totales por area, que se actualizan.
        selected_area: Area elegida; vacio para todas.

    Returns:
        Detalle, personas sin area y proyectos sin catalogo.
    """
    roster, by_id, catalog = sources
    totals = MonthTotals()

    for record in records:
        if not record.day.startswith(month) or not record.hours > 0:
            continue

        totals.has_hours = True
        person = match_person(record, roster, by_id)

        if person is None:
            if not selected_area:
                totals.unmatched[record.resource or NO_NAME] = None

            continue

        add_record(record, person, (catalog, areas[person.area]), totals)

    return totals


def match_person(
    record: HourRecord,
    roster: dict[str, Person],
    by_id: dict[str, Person],
) -> Person | None:
    """Persona del registro por ID de Clockify o, si no, por nombre."""
    name_key = norm(record.resource)

    if not record.user_id:
        return roster.get(name_key)

    person = by_id.get(record.user_id)

    if person is not None:
        return person

    if not by_id:
        return roster.get(name_key)

    return next(
        (
            item
            for item in roster.values()
            if not item.clockify_id and norm(item.name) == name_key
        ),
        None,
    )


def add_record(
    record: HourRecord,
    person: Person,
    target: tuple[Catalog, AreaTotal],
    totals: MonthTotals,
) -> None:
    """Suma un registro al detalle, al area y a las categorias."""
    catalog, area = target
    match = find_catalog_match(record.project, record.task, catalog)

    if not catalog.error and match is None:
        totals.missing_projects[record.project or NO_PROJECT] = None

    project = build_project_name(record, match)
    categories = build_categories(
        (record.project, record.task, record.tags),
        catalog,
    )
    category, kind = classify(match, categories)
    key = (norm(person.name), norm(project), category, kind)

    if key not in totals.detail:
        totals.detail[key] = {
            "recurso": person.name,
            "area": person.area,
            "banda": person.band or NOT_AVAILABLE,
            "categoria": category,
            "tipo": kind,
            "proyecto": project,
            "servicio": (match.entry.service if match else "") or NOT_AVAILABLE,
            "horas": 0.0,
        }

    totals.detail[key]["horas"] += record.hours
    area.hours += record.hours
    person_key = norm(person.name)

    if person_key not in area.people:
        area.people[person_key] = PersonTotal(person.name, 0.0, person.baja)

    area.people[person_key].hours += record.hours

    for name in categories:
        area.categories[name] = (area.categories.get(name) or 0) + record.hours


def build_project_name(
    record: HourRecord,
    match: CatalogMatch | None,
) -> str:
    """ID de proyecto con su variante (S1, CR1...) cuando se conoce."""
    if match is not None:
        return match.project_id

    suffix = SUFFIX_IN_TEXT.search(record.task)

    if suffix:
        base = NO_SUFFIX_VARIANT.sub("", record.project)

        return f"{base}_{suffix.group(1).upper()}"

    return record.project or NO_PROJECT


def classify(
    match: CatalogMatch | None,
    categories: list[str],
) -> tuple[str, str]:
    """Categoria y tipo del registro, de la ficha o de las reglas."""
    if match is not None:
        return (
            match.entry.operation_name or UNCLASSIFIED,
            match.entry.kind_name or NOT_AVAILABLE,
        )

    names = [
        item for item in categories if item not in (BILLABLE, NON_BILLABLE)
    ]

    return " / ".join(names) or UNCLASSIFIED, NOT_AVAILABLE


def build_result(
    month_info: tuple[str, bool, int, RosterSheet],
    totals_info: tuple[dict[str, AreaTotal], list[str], Catalog],
    totals: MonthTotals,
) -> JsonObject:
    """
    Arma la respuesta del mes.

    Raises:
        GseError: Cuando hay horas pero ninguna coincide con las personas.
    """
    month, from_sheet, band, sheet = month_info
    areas, missing_ids, catalog = totals_info

    if totals.has_hours and not any(item.hours > 0 for item in areas.values()):
        raise GseError(
            "La base tiene horas, pero no coinciden con las personas del "
            "área en Bandas/rol. Revisa ID Clockify y nombres; no se "
            "mostraron ceros como resultado válido.",
        )

    for item in areas.values():
        close_area(item, catalog)

    header_row = sheet.rows[sheet.header_index]

    return {
        "ok": True,
        "mes": month,
        "idsPendientes": missing_ids,
        "filtradoPorIDs": not from_sheet and not missing_ids,
        "detalle": list(totals.detail.values()),
        "catalogoAviso": catalog.error,
        "sinCatalogo": list(totals.missing_projects),
        "areas": [item.to_json() for item in areas.values()],
        "sinArea": list(totals.unmatched),
        "banda": to_text(cell_at(header_row, band)) if band >= 0 else None,
        "source": SOURCE_LABELS[from_sheet],
        "aviso": NOTICE,
    }


def close_area(area: AreaTotal, catalog: Catalog) -> None:
    """Pone los KPI sin catalogo en null y suma Administrativo Operaciones."""
    if catalog.error:
        for name in KPI_CATEGORIES:
            area.categories[name] = None

    area.categories["Administrativo Operaciones"] = (
        area.categories.get("Inversión Operaciones") or 0
    ) + (area.categories.get("Inversión Comercial") or 0)
