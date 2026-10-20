from core.utils.source_refresh import force_sources
"""Costos por ID de DataRevenue usando Clockify y Bandas/rol del mes actual."""

import calendar
import hashlib
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.clockify.provider import build_clockify_loader
from apps.gse.services.roster import find_band_column, read_roster_sheet
from apps.portal.services.executive_period import bounds, cache_suffix, current
from core.sheets.factory import build_sheet_repository
from core.sheets.project_year import mpb_previous_year_ids
from core.sheets.protocols import SheetReader
from core.time_entries.resource_rates import normalize_band, read_rate_by_band
from core.utils.dates import to_datetime
from core.utils.text import normalize_name


@dataclass(frozen=True)
class CostContext:
    """Fuentes y mapas de tarifas compartidos por la precarga financiera."""

    reader: SheetReader
    ids: list[str]
    allowed_ids: frozenset[str]
    today: date
    rates: dict[str, float]
    bands: dict[str, tuple[Any, str]]


def prepare_cost_context(
    reader: SheetReader | None = None,
    ids: list[str] | None = None,
) -> CostContext:
    """Prepara IDs, bandas y tarifas una vez antes de iniciar los hilos."""
    reader = reader or build_sheet_repository()
    ids = project_ids(reader) if ids is None else ids
    reader.prefetch(
        [
            "Bandas/rol",
            "Master rates",
            "Banda salarial",
            "Proyectos",
            "Historico_Proyectos",
            "Recursos",
            "MPB",
            "Clockify_Vinculos",
        ]
    )
    roster = read_roster_sheet(reader, "No se puede leer Bandas/rol")
    today = timezone.localdate()
    if find_band_column(roster.headers, today.month, str(today.year)) < 0:
        raise ValueError("Bandas/rol no tiene banda para el mes actual")
    rates = read_rate_by_band(reader.read_values("Master rates"))
    bands = {}
    for row in roster.data_rows:
        if row:
            bands[normalize_name(row[0])] = resolve_person_band(
                row,
                roster.headers,
                rates,
                today,
            )
    return CostContext(
        reader,
        ids,
        frozenset(pid.casefold() for pid in ids),
        today,
        rates,
        bands,
    )


def project_ids(reader, account=None):
    """Lista IDs unicos del ejercicio 2026 sin las filas de totales."""
    result = {}
    excluded = (
        mpb_previous_year_ids(reader, bounds()[0].year)
        if bounds()[0].year == bounds()[1].year
        else set()
    )
    for row in reader.read_values("DataRevenue")[1:]:
        if account and (
            len(row) < 2
            or normalize_name(str(row[1] or "")) != normalize_name(account)
        ):
            continue
        if any(
            str(cell).strip().casefold()
            in {"total", "grand total", "total general", "subtotal"}
            for cell in row[:7]
        ):
            continue
        moment = to_datetime(row[6]) if len(row) > 6 else None
        if (
            moment
            and bounds()[0].year <= moment.year <= bounds()[1].year
            and len(row) > 4
            and str(row[4] or "").strip()
        ):
            pid = str(row[4]).strip()
            if pid.casefold() not in excluded:
                result.setdefault(pid.casefold(), pid)
    from apps.portal.services.cost_project_inventory import inventory
    for identity, project in inventory(reader).items():
        if identity in excluded:
            continue
        if account and normalize_name(account) not in {
            normalize_name(name) for name in project["accounts"]
        }:
            continue
        result.setdefault(identity, project["id"])
    return sorted(result.values(), key=str.casefold)


def key(pid):
    """Identifica el costo por proyecto y mes de la banda vigente."""
    return (
        "portal:revenue-cost:2026:v9:"
        + timezone.localdate().strftime("%Y-%m")
        + ":"
        + hashlib.sha256(pid.casefold().encode()).hexdigest()
        + cache_suffix()
    )


def resolve_person_band(row, headers, rates, today):
    """Use current band; for Baja, recover the latest valid monthly band."""
    from apps.gse.services.cells import norm

    normalized_headers = [norm(header) for header in headers]
    current = find_band_column(normalized_headers, today.month, str(today.year))
    value = row[current] if 0 <= current < len(row) else ""
    if str(value).strip().casefold() != "baja":
        return value, headers[current] if 0 <= current < len(headers) else ""
    for month in range(today.month, 0, -1):
        column = find_band_column(normalized_headers, month, str(today.year))
        candidate = row[column] if 0 <= column < len(row) else ""
        rate = rates.get(normalize_band(candidate))
        if (
            str(candidate).strip().casefold() != "baja"
            and rate is not None
            and rate > 0
        ):
            return candidate, headers[column]
    return "", "Sin banda vigente historica"


def resolve_cost_scope(pid, ids, today):
    """ROC base.MM is a month; unsuffixed base is January only with variants."""
    match = re.fullmatch(
        r"(ROC\.[A-Z0-9]+\.\d{3})(?:\.(0[1-9]|1[0-2]))?",
        pid.strip(),
        re.IGNORECASE,
    )
    lookup = pid.strip()
    month = None
    if match:
        base, suffix = match.groups()
        lookup = base
        if suffix:
            month = int(suffix)
        elif any(
            re.fullmatch(
                re.escape(base) + r"\.(0[1-9]|1[0-2])",
                candidate.strip(),
                re.IGNORECASE,
            )
            for candidate in ids
        ):
            month = 1
    if month:
        start = date(2026, month, 1)
        end = date(2026, month, calendar.monthrange(2026, month)[1])
        if start <= today <= end:
            end = today
    else:
        start, end = date(2026, 1, 1), min(today, date(2026, 12, 31))
    return lookup, start, end, month


def calculate_project_cost(pid, context=None):
    """Calcula horas por tarifa usando el cargador compartido de Clockify."""
    existing = cache.get(key(pid))
    if not force_sources.get() and existing and existing.get("financial_grouping_version") == 2 and "sprints" in existing and all("people" in group for group in existing["sprints"]):
        return {
            k: v
            for k, v in existing.items()
            if k not in {"entries", "entry_months"}
        }
    reader = context.reader if context else build_sheet_repository()
    ids = context.ids if context else project_ids(reader)
    allowed = context.allowed_ids if context else {p.casefold() for p in ids}
    if pid.casefold() not in allowed:
        raise ValueError("El ID no pertenece al inventario financiero del periodo")
    context = context or prepare_cost_context(reader, ids)
    today, rates, bands = context.today, context.rates, context.bands
    lookup, start, end, month = resolve_cost_scope(pid, ids, today)
    if current():
        selected_start, selected_end = bounds()
        year = selected_start.year
        start = date(year, month, 1) if month else date(year, 1, 1)
        end = (
            date(year, month, calendar.monthrange(year, month)[1])
            if month
            else selected_end
        )
        if month and selected_start.year != selected_end.year:
            start, end = selected_start, selected_end
        start, end = max(start, selected_start), min(end, selected_end, today)
    loader = build_clockify_loader(reader)
    entries = loader.load_project(lookup, (start, end)) if start <= end else []
    from apps.portal.services.project_task_scope import scope_entries
    entries = scope_entries(pid, ids, entries, loader, lookup)
    # A CR absent from DataRevenue belongs to its pure ID; the loader normally
    # excludes CR records from the base, so load these children explicitly.
    from apps.portal.services.project_task_scope import financial_variant
    registered = {str(r[4]).strip().casefold() for r in reader.read_values("DataRevenue")[1:] if len(r) > 4}
    aliases = set()
    if reader.sheet_exists("Historico_Proyectos"):
        for row in reader.read_values("Historico_Proyectos")[1:]:
            child = str(row[2] or "").strip() if len(row) > 2 else ""
            parsed = financial_variant(child)
            if parsed and parsed[0] == pid.strip().casefold() and parsed[1].startswith("CR") and child.casefold() not in registered:
                aliases.add(child)
    entries = list(entries)
    for child in sorted(aliases):
        entries.extend(loader.load_project(child, (start, end)))
    # Resolve names for the audit even when the base ID includes all sprints.
    task_details_complete = True
    if any(e.task_id and not e.task_name for e in entries):
        from dataclasses import replace
        from core.exceptions import DashboardError
        try:
            project = loader.find_clockify_project(lookup)
            names = {str(t.get("id")): str(t.get("name") or "") for t in loader.load_project_tasks(project.project_id)} if project else {}
            entries = [replace(e, task_name=names.get(e.task_id, "")) if e.task_id and not e.task_name else e for e in entries]
        except (DashboardError, ValueError):
            task_details_complete = False
    from apps.portal.services.project_task_scope import task_tokens, variant
    base = variant(pid)[0].upper() if variant(pid) else pid
    sprint_groups = {}
    people = {}
    amounts = {}
    entry_months = {}
    missing_hours = 0
    seen = set()
    for entry in entries:
        if current() and (
            entry.entry_date is None
            or not start <= entry.entry_date.date() <= end
        ):
            continue
        if current() and month and entry.entry_date.month != month:
            continue
        if not entry.entry_id or entry.entry_id in seen:
            continue
        seen.add(entry.entry_id)
        band, band_month = bands.get(
            normalize_name(entry.resource_name), ("", "")
        )
        rate = rates.get(normalize_band(band)) if band else None
        person_key = normalize_name(entry.resource_name)
        person = people.setdefault(
            person_key,
            {
                "name": entry.resource_name,
                "band": str(band),
                "rate": rate,
                "band_month": band_month,
                "hours": 0,
                "cost": 0,
                "missing": False,
            },
        )
        person["hours"] += entry.duration_hours
        tokens = sorted(task_tokens(entry.task_name))
        label = " / ".join(tokens) if tokens else ("Tarea sin identificar" if entry.task_id and not entry.task_name else "Sin sprint")
        if label == "Tarea sin identificar":
            task_details_complete = False
        group = sprint_groups.setdefault(label, {"label":label,"project_id":base+"_"+tokens[0] if len(tokens)==1 else pid,"hours":0,"cost":0,"missing_hours":0,"tasks":set(),"people":{}})
        group["hours"] += entry.duration_hours
        group_person = group["people"].setdefault(person_key, {"name": entry.resource_name, "band": str(band), "rate": rate, "band_month": band_month, "hours": 0, "cost": 0, "missing": False})
        group_person["hours"] += entry.duration_hours
        if entry.task_name:
            group["tasks"].add(entry.task_name)
        if rate is None or rate <= 0:
            person["missing"] = True
            missing_hours += entry.duration_hours
            group["missing_hours"] += entry.duration_hours
            group_person["missing"] = True
            continue
        amount = entry.duration_hours * rate
        person["cost"] += amount
        group["cost"] += amount
        group_person["cost"] += amount
        amounts[entry.entry_id] = amount
        if entry.entry_date is not None:
            entry_months[entry.entry_id] = entry.entry_date.strftime("%Y-%m")
    result = {
        "id": pid,
        "clockify_id": lookup,
        "scope_start": start.isoformat(),
        "scope_end": end.isoformat(),
        "scope_month": month,
        "cost": round(sum(amounts.values()), 2),
        "hours": round(sum(p["hours"] for p in people.values()), 2),
        "missing_hours": round(missing_hours, 2),
        "complete": missing_hours == 0,
        "people": list(people.values()),
        "financial_grouping_version": 2,
        "sprints": [{**g,"hours":round(g["hours"],2),"cost":round(g["cost"],2),"missing_hours":round(g["missing_hours"],2),"tasks":sorted(g["tasks"]),"people":[{**person,"hours":round(person["hours"],2),"cost":round(person["cost"],2)} for person in g["people"].values()],"complete":g["missing_hours"]==0} for g in sorted(sprint_groups.values(),key=lambda g:g["label"])],
        "task_details_complete":task_details_complete,
        "included_ids":sorted({g["project_id"] for g in sprint_groups.values()}),
        "entries": amounts,
        "entry_months": entry_months,
    }
    cache.set(key(pid), result, 86400 if result["complete"] else 300)
    return {
        k: v for k, v in result.items() if k not in {"entries", "entry_months"}
    }


def cost_summary(ids=None, account=None):
    """Suma costos preparados sin duplicar registros entre proyectos."""
    ids = project_ids(build_sheet_repository(), account) if ids is None else ids
    entries = {}
    projects = []
    pending = 0
    complete = True
    for pid in ids:
        result = cache.get(key(pid))
        if result:
            entries.update(result["entries"])
            complete = complete and result["complete"]
            projects.append(
                {
                    "id": pid,
                    "cost": result["cost"],
                    "hours": result["hours"],
                    "complete": result["complete"],
                    "missing_hours": result.get("missing_hours", 0),
                    "missing_people": [p["name"] for p in result.get("people", []) if p.get("missing")],
                }
            )
        else:
            pending += 1
            projects.append(
                {
                    "id": pid,
                    "cost": None,
                    "hours": None,
                    "complete": False,
                    "error": cache.get(key(pid) + ":error"),
                }
            )
    return {
        "projects": projects,
        "cost": round(sum(entries.values()), 2),
        "pending": pending,
        "complete": pending == 0 and complete,
        "band_month": timezone.localdate().strftime("%Y-%m"),
        "deduplicated_entries": len(entries),
    }
