"""Pantalla EVA 1: proyectos AER y T&M vigentes en MPB."""

from collections.abc import Mapping, Sequence
from typing import Any

from apps.ejecutivo.constants import ROLE_COLUMNS
from apps.portal.constants import (
    EVA1_SERVICES,
    PROGRESS_ALERT_PERCENT,
    RENEWAL_ALERT_DAYS,
)
from apps.portal.schemas import Eva1View, EvaManagerRow, EvaProject
from apps.portal.services.time_cost import average

"""BKD.120.014 - EVA 1
Toma el resumen AER/T&M que ya calcula apps/ejecutivo (hoja MPB, solo
lectura) y arma los totales por Delivery Manager, el reparto de personas
por rol y la tabla de proyectos ordenada por dias para renovar.
"""

JsonObject = Mapping[str, Any]


def format_short_date(iso_date: object) -> str:
    """
    Convierte YYYY-MM-DD en dd/mm/aa.

    Args:
        iso_date: Fecha de MPB como texto ISO, o vacio.

    Returns:
        La fecha corta, o vacio si no se puede leer.
    """
    parts = str(iso_date or "").split("-")

    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        return ""

    year, month, day = parts

    return f"{day}/{month}/{year[-2:]}"


def build_eva_project(row: JsonObject) -> EvaProject:
    """
    Convierte una fila del resumen AER/T&M.

    Args:
        row: Fila con las llaves de obtenerResumenAERTYMMPB.

    Returns:
        El proyecto con las alertas en rojo ya calculadas.
    """
    etc = row.get("etc")
    progress = row.get("avance")
    renewal = row.get("renewalDias")

    return EvaProject(
        manager=str(row.get("deliveryManager", "")),
        client=str(row.get("cliente", "")),
        project_id=str(row.get("idProyecto", "")),
        service=str(row.get("servicio", "")),
        fte=float(row.get("fte") or 0),
        role_fte={
            role: float((row.get("ftePorRol") or {}).get(role) or 0)
            for role in ROLE_COLUMNS
        },
        name=str(row.get("nombre", "")),
        start=format_short_date(row.get("fechaInicio")),
        end=format_short_date(row.get("fechaFin")),
        budget=float(row.get("budget") or 0),
        burn=row.get("burn"),
        etc=etc,
        progress=progress,
        renewal_days=renewal,
        etc_bad=etc is not None and etc <= 0,
        progress_bad=progress is not None and progress > PROGRESS_ALERT_PERCENT,
        renewal_bad=renewal is not None and renewal < RENEWAL_ALERT_DAYS,
    )


def build_eva1_view(rows: Sequence[JsonObject]) -> Eva1View:
    """
    Arma la pantalla EVA 1.

    Args:
        rows: Filas del resumen AER/T&M.

    Returns:
        Totales, pivote por Delivery Manager y tabla de proyectos.
    """
    projects = sorted(
        (build_eva_project(row) for row in rows),
        key=lambda item: (
            item.renewal_days is None,
            item.renewal_days if item.renewal_days is not None else 0,
            item.manager,
            item.name,
        ),
    )
    roles = tuple(ROLE_COLUMNS)
    managers = tuple(
        _build_manager_row(
            name, [p for p in projects if p.manager == name], roles
        )
        for name in sorted({item.manager for item in projects})
    )

    return Eva1View(
        total_projects=len(projects),
        total_fte=sum(item.fte for item in projects),
        services=EVA1_SERVICES,
        roles=roles,
        managers=managers,
        totals=_build_manager_row("Total", projects, roles),
        projects=tuple(projects),
        cost_percent=average(item.progress for item in projects),
    )


def _build_manager_row(
    name: str,
    projects: Sequence[EvaProject],
    roles: Sequence[str],
) -> EvaManagerRow:
    """Cuenta proyectos por servicio y suma las personas por rol."""
    return EvaManagerRow(
        name=name,
        services=tuple(
            sum(1 for item in projects if item.service == service)
            for service in EVA1_SERVICES
        ),
        roles=tuple(
            sum(item.role_fte.get(role, 0.0) for item in projects)
            for role in roles
        ),
        total_fte=sum(item.fte for item in projects),
    )
