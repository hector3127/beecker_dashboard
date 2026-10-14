"""Costos por ID de DataRevenue usando Clockify y Bandas/rol del mes actual."""

import calendar
import hashlib
import re
from datetime import date

from django.core.cache import cache
from django.utils import timezone

from apps.clockify.provider import build_clockify_loader
from apps.gse.services.roster import find_band_column, read_roster_sheet
from core.sheets.factory import build_sheet_repository
from core.time_entries.resource_rates import normalize_band, read_rate_by_band
from core.utils.dates import to_datetime
from core.utils.text import normalize_name


def project_ids(reader):
    """Lista IDs unicos del ejercicio 2026 sin las filas de totales."""
    result = {}
    for row in reader.read_values("DataRevenue")[1:]:
        if any(
            str(cell).strip().casefold()
            in {"total", "grand total", "total general", "subtotal"}
            for cell in row[:7]
        ):
            continue
        moment = to_datetime(row[6]) if len(row) > 6 else None
        if (
            moment
            and moment.year == 2026
            and len(row) > 4
            and str(row[4] or "").strip()
        ):
            pid = str(row[4]).strip()
            result.setdefault(pid.casefold(), pid)
    return sorted(result.values(), key=str.casefold)


def key(pid):
    """Identifica el costo por proyecto y mes de la banda vigente."""
    return (
        "portal:revenue-cost:2026:v5:"
        + timezone.localdate().strftime("%Y-%m")
        + ":"
        + hashlib.sha256(pid.casefold().encode()).hexdigest()
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


def calculate_project_cost(pid):
    """Calcula horas por tarifa usando el cargador compartido de Clockify."""
    reader = build_sheet_repository()
    ids = project_ids(reader)
    if pid.casefold() not in {value.casefold() for value in ids}:
        raise ValueError("El ID no esta en DataRevenue")
    existing = cache.get(key(pid))
    if existing:
        return {
            k: v
            for k, v in existing.items()
            if k not in {"entries", "entry_months"}
        }
    roster = read_roster_sheet(reader, "No se puede leer Bandas/rol")
    today = timezone.localdate()
    column = find_band_column(roster.headers, today.month, str(today.year))
    if column < 0:
        raise ValueError("Bandas/rol no tiene banda para el mes actual")
    rates = read_rate_by_band(reader.read_values("Master rates"))
    bands = {}
    for row in roster.data_rows:
        if not row:
            continue
        band, band_month = resolve_person_band(
            row, roster.headers, rates, today
        )
        bands[normalize_name(row[0])] = (band, band_month)
    lookup, start, end, month = resolve_cost_scope(pid, ids, today)
    entries = build_clockify_loader(reader).load_project(lookup, (start, end))
    people = {}
    amounts = {}
    entry_months = {}
    missing_hours = 0
    seen = set()
    for entry in entries:
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
        if rate is None or rate <= 0:
            person["missing"] = True
            missing_hours += entry.duration_hours
            continue
        amount = entry.duration_hours * rate
        person["cost"] += amount
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
        "entries": amounts,
        "entry_months": entry_months,
    }
    cache.set(key(pid), result, 86400 if result["complete"] else 300)
    return {
        k: v for k, v in result.items() if k not in {"entries", "entry_months"}
    }


def cost_summary():
    """Suma costos preparados sin duplicar registros entre proyectos."""
    ids = project_ids(build_sheet_repository())
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
