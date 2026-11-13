"""Desglose de consulta de Facturabilidad, sin modificar cierres."""

from collections import defaultdict
from datetime import date
from typing import Any

from apps.capacidad.services.capacity_text import normalize_capacity_text
from apps.datastore.models import ClockifyMonthSync, FacturabilityClose
from apps.gse.constants import BILLABLE
from apps.portal.services.facturability import (
    normalize_service,
    person_month_hours,
    role_key,
)
from apps.portal.services.facturability_loader import read_gse_month


def audit_month(month: str, roles: frozenset[str]) -> dict[str, Any]:
    """Lee el detalle local y separa los ajustes aprobados."""
    day = date.fromisoformat(f"{month}-01")
    sync = ClockifyMonthSync.objects.filter(month=day).first()
    if sync is None:
        return {
            "ok": False,
            "error": "Este mes no tiene descarga de Clockify guardada.",
        }
    gse = read_gse_month(month, from_store=True)
    if not gse.get("ok"):
        return {
            "ok": False,
            "error": gse.get("error") or "Fuente no disponible.",
        }
    result = summarize(gse, roles)
    close = (
        FacturabilityClose.objects.filter(month=day, view="general")
        .order_by("-revision")
        .first()
    )
    result.update(
        ok=True,
        month=month,
        synced_at=sync.synced_at.isoformat(),
        published_source=close.source if close else None,
        published_revision=close.revision if close else None,
        published_summary=close.metrics if close else None,
    )
    return result


def summarize(gse: dict[str, Any], roles: frozenset[str]) -> dict[str, Any]:
    """Agrupa las horas ya clasificadas por GSE; no recalcula indicadores."""
    people: dict[str, dict[str, Any]] = {}
    roster = gse.get("plantilla") or []
    for person in roster:
        role = str(person.get("rol") or "Sin rol")
        if role_key(role) not in roles:
            continue
        name = str(person.get("nombre") or "")
        people[normalize_capacity_text(name)] = {
            "name": name,
            "role": role,
            "estimated": person.get(
                "capacidad_horas",
                person_month_hours(gse["mes"]) if gse.get("mes") else None,
            ),
            "registered": 0.0,
            "adjustment": 0.0,
            "services": defaultdict(float),
            "billable_services": defaultdict(float),
        }
    projects: dict[tuple[str, str, str, str], float] = defaultdict(float)
    for item in gse.get("detalle") or []:
        if normalize_capacity_text(item.get("proyecto")) == "comida":
            continue
        role = str(item.get("area") or "Sin rol")
        if role_key(role) not in roles:
            continue
        name = str(item.get("recurso") or "Sin nombre")
        key = normalize_capacity_text(name)
        person = people.setdefault(
            key,
            {
                "name": name,
                "role": role,
                "estimated": None,
                "registered": 0.0,
                "adjustment": 0.0,
                "services": defaultdict(float),
                "billable_services": defaultdict(float),
            },
        )
        project = str(item.get("proyecto") or "Sin proyecto")
        service = (
            normalize_service(item.get("servicio")) or "Sin servicio asignado"
        )
        if service in {"NA", "NODISPONIBLE"}:
            service = "Sin servicio asignado"
        hours = float(item.get("horas") or 0)
        adjustment = project == "Ajuste aprobado de octubre"
        kind = "Ajuste aprobado" if adjustment else "Horas registradas"
        projects[(key, project, service, kind)] += hours
        if adjustment:
            person["adjustment"] += hours
        else:
            person["registered"] += hours
            person["services"][service] += hours
            if BILLABLE in (item.get("categorias") or []):
                person["billable_services"][service] += hours
    return {
        "people": sorted(people.values(), key=lambda row: row["name"]),
        "warnings": gse.get("avisos") or [],
        "unmatched": gse.get("sinArea") or [],
        "projects": [
            {
                "name": people[key]["name"],
                "role": people[key]["role"],
                "project": project,
                "service": service,
                "kind": kind,
                "hours": hours,
            }
            for (key, project, service, kind), hours in sorted(projects.items())
        ],
    }
