"""Capacidad instalada del equipo: Bandas/rol + Clockify + Summary.

Personas: roles operativos de Bandas/rol con banda vigente en el mes.
Horas: todo Clockify del mes de esas personas (facturables o no, tambien fines
de semana) salvo el proyecto Comida. Delivery Manager y nombre del proyecto:
inventario Summary, con respaldo de Proyectos/MPB/Historico. La hoja Recursos
ya no interviene.
"""

import calendar
import re
from collections import defaultdict
from datetime import date
from typing import Any

from apps.capacidad.constants import SHEET_BANDS
from apps.capacidad.exceptions import CapacityError
from apps.capacidad.services.capacity_base import (
    find_band_column,
    read_optional_projects,
    read_project_names,
)
from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.capacidad.services.mpb_projects import (
    find_mpb_project,
    load_optional_mpb_projects,
)
from apps.capacidad.services.sheet_table import read_cell, read_sheet_table
from apps.dashboard.services.delivery_managers import load_delivery_managers
from apps.datastore.models import (
    ClockifyMonthSync,
    ClockifyTimeEntry,
    EvaExtraction,
    EvaScopeSnapshot,
)
from apps.portal.services.holidays import count_business_days, mexican_holidays
from core.sheets.protocols import SheetReader
from core.utils.text import to_text

JsonObject = dict[str, Any]

ROLES = frozenset({"dev", "qa", "roc", "arq", "ba", "sm"})
EXCLUDED_BANDS = frozenset({"", "baja", "na"})
LUNCH_PROJECT_ID = "61d5aa2596aafe5141cd7413"
DEFAULT_WORKDAY = 8.0
# Conceptos: (cargable, facturable, afecta capacidad), como la tabla de la hoja.
CONCEPTS: dict[str, tuple[bool, bool, bool]] = {
    "Interno": (True, False, True),
    "Pre-Ventas": (True, True, True),
    "Proyecto": (True, True, True),
    "Voluntary Training": (False, False, True),
    "Onboarding Training": (False, False, False),
    "Mandatory Training": (False, False, False),
    "Sin Asignación": (False, False, True),
    "Incapacidad": (False, False, False),
    "Laboratorio Beecker": (True, False, True),
    "Investigación y Desarrollo": (True, True, True),
    "Vacaciones": (False, False, False),
    "Administrativas": (True, False, True),
    "Dia Feriado": (True, False, True),
    "Inversión": (True, False, True),
}
# Los IDs con la nomenclatura NYB (TYM.NYB.009) son proyectos internos.
INTERNAL_ID = re.compile(r"(?:^|[._\s-])NYB(?:[._\s-]|$)", re.IGNORECASE)
CONCEPT_BY_NAME = {normalize_capacity_text(name): name for name in CONCEPTS}
BAND_HEADERS = [["nombre", "recurso"], ["rol"]]
CLOCKIFY_ID_HEADERS = ["ID Clockify", "Clockify ID", "ID_Clockify"]
CHANGE_SUFFIX = re.compile(r"(?:[_\s|]+(?:CR|S)\d+)+$", re.IGNORECASE)


def base_project_id(project_id: str) -> str:
    """ID sin sufijos de sprint o change request (X_S1, X_CR2, X | CR)."""
    return CHANGE_SUFFIX.sub("", project_id.strip())


def read_team(reader: SheetReader, month: str) -> list[JsonObject]:
    """Personas operativas con banda vigente en el mes."""
    bands = read_sheet_table(reader, SHEET_BANDS, BAND_HEADERS)
    column = find_band_column(bands, month)
    if column.index < 0:
        raise CapacityError(
            f"Bandas/rol no tiene columna de banda para {month}."
        )
    team = []

    for row in bands.rows:
        name = to_text(bands.read_field(row, ["Nombre", "Recurso"]) or "")
        name = name.strip()
        role = to_text(bands.read_field(row, ["ROL", "Rol"]) or "").strip()
        band = (
            to_text(read_cell(row, column.index) or "").strip()
            if column.index >= 0
            else ""
        )
        if (
            not name
            or normalize_capacity_text(role) not in ROLES
            or normalize_capacity_text(band) in EXCLUDED_BANDS
        ):
            continue
        team.append(
            {
                "nombre": name,
                "rol": role,
                "banda": band,
                "clockifyId": to_text(
                    bands.read_field(row, CLOCKIFY_ID_HEADERS) or ""
                ).strip(),
            }
        )

    return team


def read_inventory_projects() -> dict[str, tuple[str, str, str, str]]:
    """ID base -> (DM, nombre, inicio, fin) del ultimo inventario Summary."""
    run = (
        EvaExtraction.objects.filter(
            published=True, metrics__kind="summary_inventory"
        )
        .order_by("-pk")
        .first()
    )
    found: dict[str, tuple[str, str, str, str]] = {}
    if run is None:
        return found

    scopes = EvaScopeSnapshot.objects.filter(
        source__extraction=run
    ).values_list("project_id", "scope", "row")
    for project_id, scope, row in scopes:
        row = row or {}
        fields = row.get("fields") or {}
        manager = str(fields.get("delivery_manager") or "").strip()
        name = str(fields.get("project_name") or "").strip()
        # Fechas del Summary; sin ellas, las de las iteraciones de Azure.
        start = str(row.get("start") or row.get("iteration_start") or "")
        finish = str(row.get("finish") or row.get("iteration_finish") or "")
        key = normalize_capacity_text(base_project_id(project_id))
        # El bloque BASE manda; los demas solo completan lo que falte.
        if key and (scope == "BASE" or key not in found):
            found[key] = (manager, name, start[:10], finish[:10])

    return found


class ProjectInfo:
    """Delivery Manager y nombre de un proyecto con sus respaldos."""

    def __init__(self, reader: SheetReader) -> None:
        """Carga el inventario y los respaldos de Proyectos e Historico."""
        self.inventory = read_inventory_projects()
        self.managers = {
            normalize_capacity_text(project): manager
            for project, manager in load_delivery_managers(reader).items()
        }
        self.names = read_project_names(read_optional_projects(reader))
        self.mpb = load_optional_mpb_projects(reader)[0]

    def lookup(self, project_id: str, clockify_name: str) -> tuple[str, str]:
        """(Delivery Manager, nombre); vacio si no hay uno confirmado."""
        manager = name = ""
        for candidate in (project_id, base_project_id(project_id)):
            key = normalize_capacity_text(candidate)
            inv_manager, inv_name, _, _ = self.inventory.get(key, ("",) * 4)
            manager = manager or inv_manager or self.managers.get(key, "")
            name = name or inv_name or to_text(self.names.get(key) or "")
            mpb = find_mpb_project(self.mpb, candidate)
            if mpb is not None:
                manager = manager or mpb.manager
                name = name or mpb.name
        return manager, name or clockify_name

    def dates(self, project_id: str) -> tuple[bool, str, str]:
        """(existe en Azure o MPB, inicio, fin) del proyecto; ISO o vacio."""
        known, start, finish = False, "", ""
        for candidate in (project_id, base_project_id(project_id)):
            key = normalize_capacity_text(candidate)
            if key in self.inventory:
                known = True
                _, _, inv_start, inv_finish = self.inventory[key]
                start, finish = start or inv_start, finish or inv_finish
            mpb = find_mpb_project(self.mpb, candidate)
            if mpb is not None:
                known = True
                start, finish = start or mpb.start, finish or mpb.finish
        return known, start, finish


def concept_fields(concept: str) -> JsonObject:
    """Concepto con sus tres reglas escritas como en la tabla de la hoja."""
    if concept not in CONCEPTS:
        return {
            "concepto": "",
            "cargabilidad": "",
            "facturable": "",
            "capacidad": "",
        }
    loadable, billable, affects = CONCEPTS[concept]
    return {
        "concepto": concept,
        "cargabilidad": "Cargable" if loadable else "No Cargable",
        "facturable": "Facturable" if billable else "No Facturable",
        "capacidad": "Afecta Capacidad" if affects else "No Afecta Capacidad",
    }


def month_days(month: str) -> list[str]:
    """Todos los dias del mes en ISO."""
    year, number = int(month[:4]), int(month[5:7])
    last = calendar.monthrange(year, number)[1]
    return [date(year, number, day).isoformat() for day in range(1, last + 1)]


def match_person(
    team: list[JsonObject],
) -> tuple[dict[str, JsonObject], dict[str, JsonObject]]:
    """Indices por ID de Clockify y, sin ID, por nombre normalizado."""
    by_id, by_name = {}, {}
    for person in team:
        if person["clockifyId"]:
            by_id[person["clockifyId"]] = person
        else:
            by_name[normalize_capacity_text(person["nombre"])] = person
    return by_id, by_name


def build_team_capacity(
    reader: SheetReader, month: str, workday: float = DEFAULT_WORKDAY
) -> JsonObject:
    """Matriz persona x proyecto del mes, resumen por persona e indicadores."""
    sync = ClockifyMonthSync.objects.filter(
        month=date.fromisoformat(month + "-01")
    ).first()
    if sync is None:
        raise CapacityError("El mes de Clockify no está sincronizado.")
    from apps.portal.services.capacity_roster import operations_roster

    team = [
        {
            "nombre": person["name"],
            "rol": person["role"],
            "banda": person["band"],
            "clockifyId": person["clockify_id"],
            "capacidadHoras": person["capacity_hours"] * workday / DEFAULT_WORKDAY,
        }
        for person in operations_roster(month, reader)
        if month >= "2026-11" or normalize_capacity_text(person["name"]) != "diego ovadid acevedo cruz"
    ]
    october_november_roles = {
        **dict.fromkeys(("Adolfo Cesar Vidal Espino|Andres Zayas Jimenez|Antonio Roman Madrid|Carlos Ignacio Evert Sanchez Orihuela|Daniel Leon Pineda|David Ismael Morales Sandoval|Diana Laura Gutierrez Alvarez|Diego Ovadid Acevedo Cruz|Francisco Miguel Rodriguez Herrera|Gerson Garcia Bustos|Hector Santiago Garcia|Heidy Cabieles Martinez|Hugo Bahena Ocampo|Irene Abigail Lucero Hernandez|Jhoan Ahumada Rivera|Johan Ortiz Hernandez|Jonatan Ortiz Maldonado|Jorge Andres Barrios Popoca|Kenhya Madrigal Lara|Magda Perla Gonzalez Saenz|Miguel Angel Velazquez Reyes|Nicolas Alejandro Espitia Delgado|Samuel Sobrevilla Bustamante|Shanikdheyra Cruz Manjarrez Velazquez|Sheila Guadalupe Campos Pantaleon|Enrique Yael Badillo Gutierrez|Vanessa Bravo Padilla").lower().split("|"), "Dev"),
        **dict.fromkeys("jesus abraham garcia jimenez|samantha vanessa silva rojas|sofia katherin jojoa unigarro|yohane yran martinez shiraishi".split("|"), "QA"),
        **dict.fromkeys("dante emanuel galicia martinez|luis alberto lopez moran|talin edmundo barreiro hernandez|victor santiago ruiz".split("|"), "Arq"),
        **dict.fromkeys("angel maximiliano arenas muniz|jesus guadalupe flores navarrete|wendy geraldine cruz marroquin".split("|"), "BA"),
        **dict.fromkeys("christian javier samano leon|joshua daniel nicho escobar".split("|"), "SM"),
    }
    if month in {"2026-10", "2026-11"}:
        team = [
            {**person, "rol": october_november_roles[key]}
            for person in team
            if (key := normalize_capacity_text(person["nombre"])) in october_november_roles
            and (month == "2026-11" or key != "heidy cabieles martinez")
        ]
    by_id, by_name = match_person(team)
    from apps.gse.services.catalog import find_catalog_match, load_catalog

    catalog = load_catalog(reader)
    info = ProjectInfo(reader)
    first = date(int(month[:4]), int(month[5:7]), 1)
    entries = ClockifyTimeEntry.objects.filter(
        month=first, entry_date__week_day__range=(2, 6)
    ).exclude(entry_date__in=mexican_holidays(first.year)).exclude(
        project_id=LUNCH_PROJECT_ID
    )

    detail = defaultdict(int)
    count = 0
    cells: dict[tuple[str, str], JsonObject] = {}
    totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    names: dict[str, str] = {}
    for entry in entries.values(
        "user_id",
        "user_name",
        "project_id",
        "project_name",
        "entry_date",
        "task_name",
        "duration_seconds",
        "billable",
    ):
        person = by_id.get(entry["user_id"]) or by_name.get(
            normalize_capacity_text(entry["user_name"])
        )
        if person is None:
            continue
        project = entry["project_name"]
        match = find_catalog_match(project, entry["task_name"], catalog)
        service = match.entry.service if match else ""
        prefix = project.split(".", 1)[0].upper()
        if prefix in {"AER", "TYM", "IXB", "RAAS", "SAAS", "ROC"}:
            service = prefix
        if normalize_capacity_text(person["rol"]) not in {"p", "r"}:
            detail[(person["nombre"], project, service or "Otros", entry["billable"])] += entry["duration_seconds"]
        count += 1
        hours = entry["duration_seconds"] / 3600
        key = (person["nombre"], entry["project_id"])
        names[entry["project_id"]] = entry["project_name"]
        cell = cells.setdefault(
            key,
            {
                "daily": defaultdict(float),
                "facturables": 0.0,
                "noFacturables": 0.0,
            },
        )
        if entry["entry_date"] is not None:
            cell["daily"][entry["entry_date"].isoformat()] += hours
        cell["facturables" if entry["billable"] else "noFacturables"] += hours
        totals[person["nombre"]][0 if entry["billable"] else 1] += hours

    exclude_without_hours = {
        "luis enrique garcia rivera", "heidy cabieles martinez",
        "claudia ximena mazon vera", "lidio gonzalez gabriel",
    }
    team = [
        person for person in team
        if normalize_capacity_text(person["nombre"]) not in exclude_without_hours
        or sum(totals.get(person["nombre"], ())) > 0
    ]
    team_by_name = {p["nombre"]: p for p in team}
    rows = []
    for (person_name, project_key), cell in sorted(cells.items()):
        if person_name not in team_by_name:
            continue
        person = team_by_name[person_name]
        project_name = names[project_key]
        manager, name = info.lookup(project_name, project_name)
        known, start, finish = info.dates(project_name)
        # Proyectos: los IDs de Azure/MPB; lo demas, por su nombre en Clockify.
        concept = (
            "Interno"
            if INTERNAL_ID.search(project_name)
            else "Proyecto"
            if known
            else CONCEPT_BY_NAME.get(normalize_capacity_text(project_name), "")
        )
        dated = sorted(cell["daily"])
        rows.append(
            {
                **{
                    k: person[k]
                    for k in ("nombre", "clockifyId", "rol", "banda")
                },
                **concept_fields(concept),
                "dm": manager,
                "idProyecto": project_name,
                "proyecto": name,
                # Sin fecha de proyecto: primer y ultimo registro de la fila.
                "inicio": start or (dated[0] if dated else ""),
                "fin": finish or (dated[-1] if dated else ""),
                "facturables": round(cell["facturables"], 4),
                "noFacturables": round(cell["noFacturables"], 4),
                "total": round(cell["facturables"] + cell["noFacturables"], 4),
                "daily": {d: round(h, 4) for d, h in cell["daily"].items()},
            }
        )

    days = count_business_days(month)
    people = []
    for person in team:
        billable, other = totals.get(person["nombre"], [0.0, 0.0])
        total = billable + other
        people.append(
            {
                **person,
                "facturables": round(billable, 4),
                "noFacturables": round(other, 4),
                "total": round(total, 4),
                "sobreJornada": total > person["capacidadHoras"],
            }
        )
        if total == 0:
            rows.append(
                {
                    **{
                        k: person[k]
                        for k in ("nombre", "clockifyId", "rol", "banda")
                    },
                    **concept_fields(""),
                    "dm": "",
                    "idProyecto": "",
                    "proyecto": "",
                    "inicio": "",
                    "fin": "",
                    "facturables": 0.0,
                    "noFacturables": 0.0,
                    "total": 0.0,
                    "daily": {},
                }
            )

    registered = sum(p["total"] for p in people)
    base = sum(person["capacidadHoras"] for person in team)
    return {
        "ok": True,
        "mes": month,
        "dias": month_days(month),
        "diasHabiles": days,
        "jornada": workday,
        "clockify_month": {
            "available": True,
            "month": month,
            "consumed": round(registered, 2),
            "billable": round(sum(p["facturables"] for p in people), 2),
            "entries": count,
            "people": sum(1 for p in people if p["total"] > 0),
            "synced_at": sync.synced_at.isoformat(),
        },
        "personas": people,
        "filas": rows,
        "detalleMensual": [
            {"persona": name, "proyecto": project, "servicio": service, "facturable": billable, "horas": round(seconds / 3600, 2)}
            for (name, project, service, billable), seconds in sorted(detail.items())
        ],
        "resumen": {
            "personas": sum(person["capacidadHoras"] > 0 for person in team),
            "conHoras": sum(1 for p in people if p["total"] > 0),
            "sobreJornada": sum(1 for p in people if p["sobreJornada"]),
            "base": round(base, 2),
            "registradas": round(registered, 2),
            "facturables": round(sum(p["facturables"] for p in people), 2),
            "saldo": round(base - registered, 2),
            "utilizacion": round(registered / base * 100, 2) if base else None,
        },
    }
