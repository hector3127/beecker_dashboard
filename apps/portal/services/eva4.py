"""Servicios de automatizacion, renovaciones y procesos de la hoja ROC."""

from collections import Counter
from datetime import date
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.gse.services.cells import norm
from apps.portal.services.eva4_hours import (
    apply_limits,
    enrich_hours,
    resolve_month,
    task_key,
)
from apps.portal.services.eva4_index import load_hour_index, use_store
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.utils.dates import to_datetime

# Validacion del rediseno (DESIGN-IS-2026-10-20/05-plan.md, fase 6).
# Hasta esta fecha se puede ver la pantalla anterior con ?vista=anterior.
# Para retirarla: borrar ANTERIOR_HASTA, anterior_disponible(), la plantilla
# eva4_anterior.html, el parametro en views.eva4 y las pruebas test_anterior_*.
ANTERIOR_HASTA = date(2026, 11, 3)

# Primer mes con horas de Clockify en la base: limite inferior del selector.
FIRST_MONTH = date(2024, 8, 1)
MONTH_NAMES = (
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
)

SERVICES = ("SAAS", "RAAS", "ROC", "T M", "GARANTIA")
# norm() convierte «T&M» en «T M»; se vuelve a escribir al mostrarlo.
LABELS = {
    "SAAS": "SaaS",
    "RAAS": "RaaS",
    "T M": "T&M",
    "GARANTIA": "Garantía",
}
FIELDS = {
    "manager": ("Delivery Manager",),
    "country": ("Country",),
    "client": ("Client", "Cliente"),
    "project_id": ("ROC ID", "ID Project", "ID_Project"),
    "bot_id": ("BOT ID",),
    "service": ("Service",),
    "process": ("Process Name",),
    "status": ("Status ROC", "Status"),
    "start": ("Start",),
    "finish": ("Finish",),
    "average_limit": ("Tope Mensual", "Average Limit"),
    "invested_hours": ("Horas Reales", "Invested Hours"),
    "hours_balance": ("Hours Balance",),
    "package_limit": ("Hours Package Limit",),
    "package_available": ("Available Hours Package", "Hours Consumed"),
    "risk": ("Risk",),
    "account_manager": ("Account Manager", "AM"),
}


def anterior_disponible() -> bool:
    """Indica si la pantalla anterior sigue disponible para comparar."""
    return timezone.localdate() <= ANTERIOR_HASTA


def month_picker(selected: str | None, today: date) -> dict[str, Any]:
    """
    Datos del selector de mes: mes elegido, anos, nombres y limites.

    Args:
        selected: Mes AAAA-MM de la peticion; si falta o no es valido se usa
            el mes actual.
        today: Fecha local de hoy.

    Returns:
        El mes elegido, los anos y meses a mostrar y los limites AAAA-MM.
    """
    last = today.replace(day=1)
    try:
        chosen = resolve_month(selected, today)
    except ValueError:
        chosen = last
    return {
        "value": chosen.strftime("%Y-%m"),
        "year": chosen.year,
        "month": chosen.month,
        "years": list(
            range(
                min(FIRST_MONTH.year, chosen.year),
                max(last.year, chosen.year) + 1,
            )
        ),
        "months": [
            {"num": number, "name": name}
            for number, name in enumerate(MONTH_NAMES, start=1)
        ],
        "min": FIRST_MONTH.strftime("%Y-%m"),
        "max": last.strftime("%Y-%m"),
    }


def snapshot_key(month: str | None = None) -> str:
    """Identifica el corte diario, compartido por detalle y Operativa."""
    day = timezone.localdate()
    return (
        "portal:eva4:snapshot:v7:"
        + day.isoformat()
        + ":"
        + resolve_month(month, day).strftime("%Y-%m")
    )


def cached_eva4(month: str | None = None) -> dict[str, Any]:
    """Obtiene el ultimo corte sin consultar Sheets."""
    return cache.get(snapshot_key(month)) or {"available": False}


def build_eva4(values: list[list[Any]], today: date) -> dict[str, Any]:
    """Construye tres tablas conservando las cifras y fechas de ROC."""
    header = next(
        (
            i
            for i, row in enumerate(values[:20])
            if "client" in [norm(c) for c in row]
            and "status roc" in [norm(c) for c in row]
        ),
        None,
    )
    if header is None:
        raise ValueError("ROC no tiene encabezados Client y Status ROC.")
    headers = [norm(cell) for cell in values[header]]
    columns = {
        field: next(
            (
                headers.index(norm(alias))
                for alias in aliases
                if norm(alias) in headers
            ),
            -1,
        )
        for field, aliases in FIELDS.items()
    }
    clients: dict[str, dict[str, Any]] = {}
    processes = []
    renewals: dict[tuple[Any, ...], dict[str, Any]] = {}
    service_totals: Counter[str] = Counter()
    statuses: Counter[str] = Counter()
    for row in values[header + 1 :]:
        item: dict[str, Any] = {
            field: row[col] if 0 <= col < len(row) else ""
            for field, col in columns.items()
        }
        status = norm(item["status"])
        if status not in {"activo", "active", "suspendido", "suspended"}:
            continue
        client = str(item["client"]).strip()
        if not client or norm(client) in {"total", "grand total"}:
            continue
        item["client"] = client
        item["status_code"] = (
            "active" if status in {"activo", "active"} else "suspended"
        )
        service = norm(item["service"]).upper()
        item["service"] = LABELS.get(service, service)
        for field in ("start", "finish"):
            moment = to_datetime(item[field])
            item[field] = moment.date() if moment else None
        processes.append(item)
        group = clients.setdefault(
            client,
            {
                "name": client,
                "services": Counter(),
                "active": 0,
                "suspended": 0,
                "total": 0,
            },
        )
        group["services"][service] += 1
        group[item["status_code"]] += 1
        group["total"] += 1
        service_totals[service] += 1
        statuses[item["status_code"]] += 1
        if item["finish"] is not None and item["project_id"]:
            due = (item["finish"] - today).days
            if due <= 90:
                identity = tuple(
                    item[field]
                    for field in (
                        "project_id",
                        "country",
                        "finish",
                        "manager",
                        "account_manager",
                    )
                )
                renewals[identity] = {
                    **item,
                    "due": due,
                    "urgency": "critical"
                    if due <= 30
                    else "warning"
                    if due <= 60
                    else "ok",
                }
    services = [*SERVICES, *sorted(set(service_totals) - set(SERVICES))]
    summary = sorted(
        clients.values(), key=lambda c: (-c["total"], c["name"].casefold())
    )
    for group in summary:
        group["counts"] = [group["services"][name] for name in services]
        del group["services"]
    missing = [
        FIELDS[name][0]
        for name in (
            "average_limit",
            "invested_hours",
            "hours_balance",
            "package_limit",
            "package_available",
        )
        if columns[name] < 0
    ]
    return {
        "available": True,
        "error": "",
        "loaded_at": timezone.localtime(),
        "services": [LABELS.get(name, name) for name in services],
        "clients": summary,
        "service_totals": [service_totals[name] for name in services],
        "total": len(processes),
        "active": statuses["active"],
        "suspended": statuses["suspended"],
        "processes": processes,
        "renewals": sorted(
            renewals.values(), key=lambda r: (r["due"], str(r["project_id"]))
        ),
        "renewal_count": len(renewals),
        "missing_columns": missing,
    }


def clockify_project_map(
    reader: Any, report: dict[str, Any], year: int
) -> dict[str, str]:
    """
    ROC ID -> nombre del proyecto de Clockify cuando no se llaman igual.

    Usa la misma resolucion que el resto del portal: primero el vinculo manual
    de la hoja Clockify_Vinculos, luego el nombre exacto y, al final, un unico
    nombre que contenga el ID. Sin la base de datos de horas no hay IDs de
    Clockify que enlazar y se usa el ROC ID tal cual.

    Args:
        reader: Repositorio de Sheets.
        report: Resultado de build_eva4.
        year: Ano de las horas.

    Returns:
        task_key(ROC ID) -> task_key(nombre del proyecto en Clockify).
    """
    if not use_store(year):
        return {}
    from apps.clockify.services.project_matcher import (
        resolve_clockify_project,
    )
    from apps.clockify.services.time_entry_loader import load_project_links
    from apps.datastore.services.stored_base import clockify_projects

    try:
        links = load_project_links(reader)
    except DashboardError:
        links = {}
    projects = clockify_projects(year)
    mapping: dict[str, str] = {}
    for roc_id in {str(p["project_id"]).strip() for p in report["processes"]}:
        if not roc_id:
            continue
        found = resolve_clockify_project(roc_id, projects, links)
        if found is not None:
            mapping[task_key(roc_id)] = task_key(found.name)
    return mapping


def load_eva4(month: str | None = None) -> dict[str, Any]:
    """Actualiza el corte desde Sheets y conserva el anterior si falla."""
    try:
        selected_month = resolve_month(month, timezone.localdate())
    except ValueError as error:
        return {"available": False, "error": str(error)}
    key = snapshot_key(month)
    previous = cached_eva4(month)
    if previous["available"] and cache.get(key + ":fresh"):
        return previous
    try:
        reader = build_sheet_repository()
        result = build_eva4(reader.read_values("ROC"), timezone.localdate())
        source = f"08.Base Clockify {selected_month.year}"
        candidates = (
            "EVA-04 Report",
            f"ROC | Desgloce por Bot {selected_month.year}",
        )
        limits = [name for name in candidates if reader.sheet_exists(name)]
        reader.prefetch(limits)
        for name in limits:
            apply_limits(result, reader.read_values(name))
        index = load_hour_index(reader, selected_month.year)
        enrich_hours(
            result,
            [],
            selected_month,
            index=index,
            project_map=clockify_project_map(
                reader, result, selected_month.year
            ),
        )
        result["hours_source"] = source
        result["hours_origin"] = (
            "database" if use_store(selected_month.year) else "sheet"
        )
        result["current_month"] = timezone.localdate().strftime("%Y-%m")
        result["missing_columns"] = []
        result["limit_sources"] = ", ".join(["ROC", *limits])
    except (DashboardError, ValueError) as error:
        return {**previous, "error": str(error)}
    cache.set(key, result, 86400)
    cache.set(key + ":fresh", True, 300)
    return result
