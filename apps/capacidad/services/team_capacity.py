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
    ClockifyTimeEntry,
    EvaExtraction,
    EvaScopeSnapshot,
)
from apps.portal.services.holidays import count_business_days
from core.sheets.protocols import SheetReader
from core.utils.text import to_text

JsonObject = dict[str, Any]

ROLES = frozenset({"dev", "qa", "roc", "arq", "ba", "sm"})
EXCLUDED_BANDS = frozenset({"", "baja", "na"})
LUNCH_PROJECT_ID = "61d5aa2596aafe5141cd7413"
DEFAULT_WORKDAY = 8.0
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


def read_inventory_projects() -> dict[str, tuple[str, str]]:
    """ID base -> (Delivery Manager, nombre) del ultimo inventario Summary."""
    run = (
        EvaExtraction.objects.filter(
            published=True, metrics__kind="summary_inventory"
        )
        .order_by("-pk")
        .first()
    )
    found: dict[str, tuple[str, str]] = {}
    if run is None:
        return found

    scopes = EvaScopeSnapshot.objects.filter(
        source__extraction=run
    ).values_list("project_id", "scope", "row")
    for project_id, scope, row in scopes:
        fields = (row or {}).get("fields") or {}
        manager = str(fields.get("delivery_manager") or "").strip()
        name = str(fields.get("project_name") or "").strip()
        key = normalize_capacity_text(base_project_id(project_id))
        # El bloque BASE manda; los demas solo completan lo que falte.
        if key and (scope == "BASE" or key not in found):
            found[key] = (manager, name)

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
            inv_manager, inv_name = self.inventory.get(key, ("", ""))
            manager = manager or inv_manager or self.managers.get(key, "")
            name = name or inv_name or to_text(self.names.get(key) or "")
            mpb = find_mpb_project(self.mpb, candidate)
            if mpb is not None:
                manager = manager or mpb.manager
                name = name or mpb.name
        return manager, name or clockify_name


def month_days(month: str) -> list[str]:
    """Todos los dias del mes en ISO (los fines de semana tambien suman)."""
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
    team = read_team(reader, month)
    by_id, by_name = match_person(team)
    info = ProjectInfo(reader)
    first = date(int(month[:4]), int(month[5:7]), 1)
    entries = ClockifyTimeEntry.objects.filter(month=first).exclude(
        project_id=LUNCH_PROJECT_ID
    )

    cells: dict[tuple[str, str], JsonObject] = {}
    totals: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    names: dict[str, str] = {}
    for entry in entries.values(
        "user_id",
        "user_name",
        "project_id",
        "project_name",
        "entry_date",
        "duration_seconds",
        "billable",
    ):
        person = by_id.get(entry["user_id"]) or by_name.get(
            normalize_capacity_text(entry["user_name"])
        )
        if person is None or entry["entry_date"] is None:
            continue
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
        cell["daily"][entry["entry_date"].isoformat()] += hours
        cell["facturables" if entry["billable"] else "noFacturables"] += hours
        totals[person["nombre"]][0 if entry["billable"] else 1] += hours

    team_by_name = {p["nombre"]: p for p in team}
    rows = []
    for (person_name, project_key), cell in sorted(cells.items()):
        person = team_by_name[person_name]
        project_name = names[project_key]
        manager, name = info.lookup(project_name, project_name)
        rows.append(
            {
                **{
                    k: person[k]
                    for k in ("nombre", "clockifyId", "rol", "banda")
                },
                "dm": manager,
                "idProyecto": project_name,
                "proyecto": name,
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
                "sobreJornada": total > days * workday,
            }
        )
        if total == 0:
            rows.append(
                {
                    **{
                        k: person[k]
                        for k in ("nombre", "clockifyId", "rol", "banda")
                    },
                    "dm": "",
                    "idProyecto": "",
                    "proyecto": "",
                    "facturables": 0.0,
                    "noFacturables": 0.0,
                    "total": 0.0,
                    "daily": {},
                }
            )

    registered = sum(p["total"] for p in people)
    base = len(team) * days * workday
    return {
        "ok": True,
        "mes": month,
        "dias": month_days(month),
        "diasHabiles": days,
        "jornada": workday,
        "personas": people,
        "filas": rows,
        "resumen": {
            "personas": len(team),
            "conHoras": sum(1 for p in people if p["total"] > 0),
            "sobreJornada": sum(1 for p in people if p["sobreJornada"]),
            "base": round(base, 2),
            "registradas": round(registered, 2),
            "facturables": round(sum(p["facturables"] for p in people), 2),
            "saldo": round(base - registered, 2),
            "utilizacion": round(registered / base * 100, 2) if base else None,
        },
    }
