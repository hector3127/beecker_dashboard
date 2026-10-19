"""Catalogos de clientes, personas y proyectos con sus alias."""

import logging
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction

from apps.datastore.models import (
    Client,
    ClientAlias,
    ClockifyTimeEntry,
    Person,
    PersonAlias,
    Project,
)
from core.utils.cell_types import CellValue
from core.utils.text import normalize_name, to_text

"""BKD.130.008 - Catalogos con alias
Cada cliente, persona y proyecto se guarda una sola vez. Las hojas lo
escriben distinto (acentos, mayusculas, espacios dobles, «GPO.001_ CR»):
el catalogo agrupa esas variantes por su forma normalizada y guarda cada
una como alias. Una variante se une a otro registro cambiando su alias en
el admin; queda como manual y la sincronizacion la respeta.
Todo se arma con las hojas ya guardadas en la base: no consulta Google.
"""

logger = logging.getLogger(__name__)

Rows = Sequence[Sequence[CellValue]]
EMPTY_VALUES = frozenset({"", "(no value)", "no value", "n/a", "na", "-"})
ID_VARIANT = re.compile(r"[\s_|-]*(?:S\d+|CR\d*|QA\d*)$", re.IGNORECASE)
# Los IDs reales llevan un punto (AMK.008, ROC.AIN.001); «TBD» o
# «Viaticos» son conceptos, no proyectos.
PROJECT_ID = re.compile(r"^[A-Z0-9]+(\.[A-Z0-9]+)+(_[A-Z0-9]+)*$")

# (hoja, indice de columna base 0, encabezado esperado). Si el encabezado
# ya no esta en esa columna se omite y se avisa, en lugar de leer otra.
CLIENT_COLUMNS: tuple[tuple[str, int, str], ...] = (
    ("Proyectos", 2, "Cliente"),
    ("Historico_Proyectos", 1, "Account"),
    ("Historico_Proyectos", 11, "Client"),
    ("MPB", 1, "CLIENTE"),
    ("ROC", 0, "Client"),
    ("DataRevenue", 1, "Cliente"),
    ("Backlog_Proyectos", 0, "Account Name"),
    ("CatalagoProyectos", 7, "Cliente"),
)
PERSON_COLUMNS: tuple[tuple[str, int, str, str], ...] = (
    ("Proyectos", 4, "Scrum_Master", "scrum_master"),
    ("Historico_Proyectos", 0, "Delivery Manager", "delivery_manager"),
    ("Historico_Proyectos", 10, "Delivery Manager", "delivery_manager"),
    ("MPB", 20, "Delivery Manager", "delivery_manager"),
    ("ROC", 10, "Account Manager", "account_manager"),
    ("ROC", 11, "Delivery Manager", "delivery_manager"),
    ("Backlog_Proyectos", 2, "Delivery Manager", "delivery_manager"),
    ("Recursos", 2, "Nombre del recurso", "recurso"),
    ("Bandas/rol", 0, "Nombre", "recurso"),
    ("Banda salarial", 0, "Nombre", "recurso"),
)
# Bandas/rol trae el ID de Clockify de cada persona.
ROSTER_SHEET = "Bandas/rol"
ROSTER_NAME_COLUMN = 0
ROSTER_ID_COLUMN = 2
ROSTER_ID_HEADER = "ID Clockify"


Column = tuple[int, str]


@dataclass(frozen=True)
class ProjectColumns:
    """Columnas de una hoja que describen proyectos: (base 0, encabezado)."""

    sheet: str
    id: Column
    name: Column | None = None
    service: Column | None = None
    client: Column | None = None
    manager: Column | None = None


# El orden manda: la primera hoja que trae un dato lo fija.
PROJECT_COLUMNS: tuple[ProjectColumns, ...] = (
    ProjectColumns(
        "Proyectos",
        (0, "ID_Proyecto"),
        name=(1, "Nombre"),
        service=(3, "Servicio"),
        client=(2, "Cliente"),
    ),
    ProjectColumns(
        "Historico_Proyectos",
        (2, "Project ID"),
        name=(4, "Project Name"),
        service=(3, "Service"),
        client=(1, "Account"),
        manager=(0, "Delivery Manager"),
    ),
    ProjectColumns(
        "MPB",
        (2, "ID"),
        name=(4, "NOMBRE"),
        service=(5, "SERVICE"),
        client=(1, "CLIENTE"),
        manager=(20, "Delivery Manager"),
    ),
    ProjectColumns(
        "ROC",
        (3, "ROC ID"),
        service=(5, "Service"),
        client=(0, "Client"),
        manager=(11, "Delivery Manager"),
    ),
    ProjectColumns(
        "ROC",
        (4, "BOT ID"),
        service=(5, "Service"),
        client=(0, "Client"),
        manager=(11, "Delivery Manager"),
    ),
    ProjectColumns(
        "DataRevenue",
        (4, "Project ID"),
        service=(3, "Service Type"),
        client=(1, "Cliente"),
    ),
    ProjectColumns(
        "CatalagoProyectos",
        (3, "ID_Proyecto"),
        service=(8, "Sevicio"),
        client=(7, "Cliente"),
    ),
)
PROJECT_FIELDS: tuple[str, ...] = ("name", "service", "client", "manager")


@dataclass
class CatalogResult:
    """Lo que dejo la construccion de los catalogos."""

    clients: int = 0
    persons: int = 0
    projects: int = 0
    skipped_ids: int = 0
    warnings: list[str] = field(default_factory=list)
    merged_clients: list[str] = field(default_factory=list)
    merged_persons: list[str] = field(default_factory=list)


def name_key(value: CellValue) -> str:
    """
    Forma normalizada de un nombre: sin acentos, mayusculas ni espacios dobles.

    Args:
        value: Nombre tal como esta en la hoja.

    Returns:
        La llave, o cadena vacia si el valor esta vacio o es un marcador.
    """
    key = " ".join(normalize_name(value).split())
    return "" if key in EMPTY_VALUES else key


def clean_text(value: CellValue) -> str:
    """Texto sin espacios repetidos; vacio si es un marcador de «sin dato»."""
    text = " ".join(to_text(value).split())
    return "" if text.casefold() in EMPTY_VALUES else text


def project_id(value: CellValue) -> str:
    """ID canonico (mayusculas, sin espacios); vacio si no es un ID."""
    candidate = "".join(to_text(value).split()).upper()
    return candidate if PROJECT_ID.match(candidate) else ""


def base_project_id(internal_id: str) -> str:
    """ID del proyecto base, sin los sufijos _S#, _CR# o _QA#."""
    base = internal_id
    while True:
        stripped = ID_VARIANT.sub("", base)
        if stripped == base or not stripped:
            return base
        base = stripped


def read_column(
    rows: Rows,
    index: int,
    header: str,
    sheet: str,
    warnings: list[str],
) -> list[CellValue] | None:
    """
    Valores de una columna si su encabezado es el esperado.

    Args:
        rows: Filas de la hoja (la primera es el encabezado).
        index: Columna base 0.
        header: Encabezado que debe tener.
        sheet: Nombre de la hoja (para el aviso).
        warnings: Donde se agrega el aviso si el encabezado no coincide.

    Returns:
        Los valores de las filas de datos, o None si no se puede leer.
    """
    if not rows:
        return None
    found = rows[0][index] if index < len(rows[0]) else ""
    if normalize_name(found) != normalize_name(header):
        warnings.append(
            f"{sheet}: la columna {index + 1} ya no es «{header}» "
            f"(ahora «{to_text(found)}»); se omitio."
        )
        return None
    return [row[index] if index < len(row) else "" for row in rows[1:]]


def pick_name(spellings: Counter[str]) -> str:
    """La forma mas usada; en empate, la mas larga y luego la primera."""
    return min(spellings, key=lambda s: (-spellings[s], -len(s), s))


def collect_names(
    columns: Iterable[tuple[str, int, str]],
    sheets: Mapping[str, Rows],
    warnings: list[str],
) -> dict[str, Counter[str]]:
    """
    Agrupa por llave normalizada todas las formas de escribir un nombre.

    Args:
        columns: (hoja, columna, encabezado) a leer.
        sheets: Filas de cada hoja.
        warnings: Avisos de columnas que cambiaron.

    Returns:
        llave -> cuantas veces aparece cada forma de escribirlo, con la
        hoja de origen en el texto («Hoja: nombre»).
    """
    grouped: dict[str, Counter[str]] = defaultdict(Counter)
    for sheet, index, header in columns:
        values = read_column(
            sheets.get(sheet, []), index, header, sheet, warnings
        )
        for value in values or []:
            key = name_key(value)
            if key:
                grouped[key][clean_text(value)] += 1
    return grouped


def build_clients(
    sheets: Mapping[str, Rows],
    result: CatalogResult,
) -> dict[str, Client]:
    """
    Crea o actualiza los clientes y sus alias.

    Args:
        sheets: Filas de cada hoja guardada.
        result: Donde se acumulan los avisos.

    Returns:
        llave normalizada -> cliente.
    """
    grouped = collect_names(
        [(s, i, h) for s, i, h in CLIENT_COLUMNS], sheets, result.warnings
    )
    manual = {a.key: a for a in ClientAlias.objects.filter(manual=True)}
    by_key: dict[str, Client] = {}
    for key, spellings in grouped.items():
        if key in manual:
            client = manual[key].client
        else:
            client, _ = Client.objects.get_or_create(
                key=key, defaults={"name": pick_name(spellings)}
            )
            if client.name != pick_name(spellings):
                client.name = pick_name(spellings)
                client.save(update_fields=["name"])
        by_key[key] = client
        if key not in manual:
            ClientAlias.objects.update_or_create(
                key=key,
                defaults={"client": client, "spellings": sorted(spellings)},
            )
        else:
            ClientAlias.objects.filter(key=key).update(
                spellings=sorted(spellings)
            )
        if len(spellings) > 1:
            result.merged_clients.append(" = ".join(sorted(spellings)))
    ClientAlias.objects.exclude(key__in=grouped).filter(manual=False).delete()
    Client.objects.filter(aliases__isnull=True).delete()
    return by_key


def build_persons(
    sheets: Mapping[str, Rows],
    result: CatalogResult,
) -> dict[str, Person]:
    """
    Crea o actualiza las personas, con su ID de Clockify y sus alias.

    Args:
        sheets: Filas de cada hoja guardada.
        result: Donde se acumulan los avisos.

    Returns:
        llave normalizada -> persona.
    """
    grouped = collect_names(
        [(s, i, h) for s, i, h, _ in PERSON_COLUMNS], sheets, result.warnings
    )
    roles: dict[str, set[str]] = defaultdict(set)
    for sheet, index, header, role in PERSON_COLUMNS:
        for value in (
            read_column(sheets.get(sheet, []), index, header, sheet, []) or []
        ):
            if name_key(value):
                roles[name_key(value)].add(role)
    clockify_ids = roster_clockify_ids(sheets, result.warnings)
    for user_id, user_name in clockify_users():
        key = name_key(user_name)
        if key:
            grouped[key][clean_text(user_name)] += 1
            roles[key].add("usuario_clockify")
            clockify_ids.setdefault(key, user_id)

    manual = {a.key: a for a in PersonAlias.objects.filter(manual=True)}
    by_key: dict[str, Person] = {}
    for key, spellings in grouped.items():
        if key in manual:
            person = manual[key].person
        else:
            person, _ = Person.objects.get_or_create(
                key=key, defaults={"name": pick_name(spellings)}
            )
            person.name = pick_name(spellings)
        person.roles = sorted(set(person.roles) | roles[key])
        if clockify_ids.get(key):
            person.clockify_user_id = clockify_ids[key]
        person.save()
        by_key[key] = person
        if key not in manual:
            PersonAlias.objects.update_or_create(
                key=key,
                defaults={"person": person, "spellings": sorted(spellings)},
            )
        else:
            PersonAlias.objects.filter(key=key).update(
                spellings=sorted(spellings)
            )
        if len(spellings) > 1:
            result.merged_persons.append(" = ".join(sorted(spellings)))
    PersonAlias.objects.exclude(key__in=grouped).filter(manual=False).delete()
    Person.objects.filter(aliases__isnull=True).delete()
    return by_key


def roster_clockify_ids(
    sheets: Mapping[str, Rows],
    warnings: list[str],
) -> dict[str, str]:
    """ID de Clockify de cada persona de Bandas/rol, por llave de nombre."""
    names = read_column(
        sheets.get(ROSTER_SHEET, []),
        ROSTER_NAME_COLUMN,
        "Nombre",
        ROSTER_SHEET,
        warnings,
    )
    ids = read_column(
        sheets.get(ROSTER_SHEET, []),
        ROSTER_ID_COLUMN,
        ROSTER_ID_HEADER,
        ROSTER_SHEET,
        warnings,
    )
    if names is None or ids is None:
        return {}
    return {
        name_key(name): clean_text(user_id)
        for name, user_id in zip(names, ids, strict=False)
        if name_key(name) and clean_text(user_id)
    }


def clockify_users() -> list[tuple[str, str]]:
    """Usuarios distintos que registraron horas: (ID de Clockify, nombre)."""
    return list(
        ClockifyTimeEntry.objects.exclude(user_id="")
        .values_list("user_id", "user_name")
        .distinct()
    )


def build_projects(
    sheets: Mapping[str, Rows],
    clients: Mapping[str, Client],
    persons: Mapping[str, Person],
    result: CatalogResult,
) -> int:
    """
    Crea o actualiza los proyectos con cliente y Delivery Manager.

    Args:
        sheets: Filas de cada hoja guardada.
        clients: Clientes por llave normalizada.
        persons: Personas por llave normalizada.
        result: Donde se acumulan los avisos.

    Returns:
        Cuantos proyectos hay en el catalogo.
    """
    found: dict[str, dict[str, Any]] = {}
    skipped: set[str] = set()
    for spec in PROJECT_COLUMNS:
        rows = sheets.get(spec.sheet, [])
        ids = read_column(rows, *spec.id, spec.sheet, result.warnings)
        if ids is None:
            continue
        columns: dict[str, list[CellValue]] = {}
        for field_name in PROJECT_FIELDS:
            wanted: Column | None = getattr(spec, field_name)
            columns[field_name] = (
                read_column(rows, *wanted, spec.sheet, result.warnings)
                if wanted
                else None
            ) or [""] * len(ids)
        for position, raw in enumerate(ids):
            internal_id = project_id(raw)
            if not internal_id:
                if clean_text(raw):
                    skipped.add(clean_text(raw))
                continue
            entry = found.setdefault(
                internal_id,
                {
                    "sources": set(),
                    "spellings": set(),
                    **dict.fromkeys(PROJECT_FIELDS, ""),
                },
            )
            entry["sources"].add(spec.sheet)
            entry["spellings"].add(to_text(raw).strip())
            for field_name in PROJECT_FIELDS:
                value = clean_text(columns[field_name][position])
                if value and not entry[field_name]:
                    entry[field_name] = value
    result.skipped_ids = len(skipped)
    for internal_id, entry in found.items():
        Project.objects.update_or_create(
            internal_id=internal_id,
            defaults={
                "base_id": base_project_id(internal_id),
                "name": entry["name"],
                "service": entry["service"],
                "client": clients.get(name_key(entry["client"])),
                "delivery_manager": persons.get(name_key(entry["manager"])),
                "sources": sorted(entry["sources"]),
                "spellings": sorted(entry["spellings"]),
            },
        )
    Project.objects.exclude(internal_id__in=found).delete()
    return len(found)


def build_catalogs(sheets: Mapping[str, Rows]) -> CatalogResult:
    """
    Reconstruye los catalogos a partir de las hojas guardadas.

    Args:
        sheets: Filas de cada hoja (nombre -> matriz con encabezado).

    Returns:
        Los conteos y avisos de la construccion.
    """
    result = CatalogResult()
    with transaction.atomic():
        clients = build_clients(sheets, result)
        persons = build_persons(sheets, result)
        result.projects = build_projects(sheets, clients, persons, result)
    result.clients = Client.objects.count()
    result.persons = Person.objects.count()
    return result
