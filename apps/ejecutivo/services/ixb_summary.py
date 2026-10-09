"""Resumen ejecutivo IXB/RaaS."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from apps.azure_devops.exceptions import AzureDevOpsRequestError
from apps.azure_devops.services.project_resolver import resolve_azure_project
from apps.ejecutivo.services.azure_stages import (
    AzureStageRange,
    build_stage_range,
    count_work_items,
    empty_work_item_counts,
    infer_sprint,
    list_open_risk_titles,
)
from apps.ejecutivo.services.ixb_rules import (
    calculate_exact_burn,
    find_delivery_manager,
    is_finished_in_history,
    read_project_id,
    read_project_manager,
    resolve_ixb_status,
    select_current_row,
    select_history_rows,
)
from apps.ejecutivo.services.project_milestones import (
    calculate_project_milestones,
)
from core.exceptions import DashboardError
from core.time_entries.models import TimeEntry
from core.utils.cell_types import SheetRow
from core.utils.dates import to_utc_iso
from core.utils.numbers import round_half_up, round_half_up_int, to_number
from core.utils.text import (
    extract_base_id,
    get_flexible_value,
    strip_accents,
    to_text,
)

"""BKD.040.010 - Resumen IXB/RaaS
Equivale a obtenerResumenIXBRaaS(): agrupa los proyectos IXB, RaaS, SaaS
y POC por ID base, toma la nomenclatura vigente, calcula horas con
Clockify y etapas con Azure, y arma los pivotes por Delivery Manager.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

IXB_RAAS_SERVICES = frozenset(
    {"IXB", "IXB Y RAAS", "POC", "RAAS", "RAAS+", "SAAS"},
)
UNASSIGNED_MANAGER = "Sin asignar"
STATUS_PIVOT_KEYS = (
    ("suspend", "Sus"),
    ("deployment", "Dep"),
    ("development", "Dev"),
    ("discovery", "Dis"),
)


class AzureLookup(Protocol):
    """Consultas de Azure DevOps que necesita el resumen."""

    def list_project_names(self) -> list[str]:
        """Lista los Team Projects."""
        ...

    def list_iterations(self, project_name: str) -> list[JsonObject]:
        """Lista las iteraciones de un Team Project."""
        ...

    def list_work_items(self, project_name: str) -> list[JsonObject]:
        """Lista los work items de un Team Project."""
        ...

    def prefetch(
        self,
        project_names: Sequence[str],
        include_iterations: bool,
    ) -> None:
        """Precarga en paralelo varios Team Projects."""
        ...


@dataclass(slots=True)
class IxbSources:
    """Datos de entrada del resumen IXB/RaaS."""

    project_rows: Sequence[SheetRow]
    history_rows: Sequence[SheetRow]
    load_project_entries: Callable[[str], list[TimeEntry]]
    azure: AzureLookup | None


def build_ixb_summary(sources: IxbSources, now: datetime) -> JsonObject:
    """
    Construye la tabla IXB/RaaS y sus pivotes.

    Args:
        sources: Hojas, horas de Clockify y Azure DevOps.
        now: Fecha y hora local actual.

    Returns:
        {"ok", "filas", "pivoteServicio", "pivoteStatus"}.
    """
    azure_projects = list_azure_projects(sources.azure)
    groups = group_by_base(sources.project_rows)
    rows: list[JsonObject] = []

    if sources.azure is not None:
        sources.azure.prefetch(
            [
                resolve_azure_project(base_id, azure_projects)
                for base_id in groups
            ],
            include_iterations=True,
        )

    for base_id, group_rows in groups.items():
        summary_row = build_group_row(
            base_id,
            group_rows,
            sources,
            azure_projects,
            now,
        )

        if summary_row is not None:
            rows.append(summary_row)

    rows.sort(key=lambda row: locale_key(row["deliveryManager"]))

    return {
        "ok": True,
        "filas": rows,
        "pivoteServicio": build_service_pivot(rows),
        "pivoteStatus": build_status_pivot(rows),
    }


def group_by_base(
    project_rows: Sequence[SheetRow],
) -> dict[str, list[SheetRow]]:
    """
    Agrupa los proyectos IXB/RaaS por su ID base.

    Args:
        project_rows: Filas de la hoja Proyectos.

    Returns:
        ID base -> filas del grupo.
    """
    groups: dict[str, list[SheetRow]] = {}

    for row in project_rows:
        service = read_service(row)
        project_id = read_project_id(row)

        if service in IXB_RAAS_SERVICES and project_id:
            groups.setdefault(extract_base_id(project_id), []).append(row)

    return groups


def build_group_row(
    base_id: str,
    group_rows: list[SheetRow],
    sources: IxbSources,
    azure_projects: list[str],
    now: datetime,
) -> JsonObject | None:
    """
    Construye la fila de un proyecto base.

    Args:
        base_id: ID base del grupo.
        group_rows: Filas de Proyectos del grupo.
        sources: Datos de entrada.
        azure_projects: Team Projects de Azure.
        now: Fecha y hora local actual.

    Returns:
        La fila, o None si el proyecto ya termino.
    """
    representative = select_current_row(group_rows, base_id)
    reference_id = read_project_id(representative) or base_id
    reference_rows = [
        row for row in group_rows if read_project_id(row) == reference_id
    ]

    if is_finished_in_history(
        sources.history_rows,
        reference_id,
        base_id,
        now.date(),
    ):
        return None

    budget = sum(to_number(row.get("Budget_Hrs")) for row in reference_rows)
    burn = load_burn(sources, reference_id)
    sprints = list(
        dict.fromkeys(
            infer_sprint(read_project_id(row)) for row in reference_rows
        ),
    ) or ["S1"]
    azure_project = resolve_azure_project(base_id, azure_projects)
    stage_range = load_stage_range(sources.azure, azure_project, sprints, now)
    work_items = load_work_items(sources.azure, azure_project)
    milestones = calculate_project_milestones(
        sources.history_rows,
        reference_id or base_id,
        now,
    )

    return {
        "deliveryManager": (
            find_delivery_manager(sources.history_rows, reference_rows, base_id)
            or read_project_manager(representative)
        ),
        "idProyecto": reference_id,
        "idReferencia": reference_id,
        "idProyectoBase": base_id,
        "servicio": read_service(representative),
        "cliente": to_text(
            get_flexible_value(representative, ["Cliente", "Account"]),
        ),
        "nombre": to_text(representative.get("Nombre")) or base_id,
        "status": resolve_ixb_status(
            stage_range.current_stage,
            stage_range.finish,
            select_history_rows(
                sources.history_rows,
                reference_id,
                base_id,
                allow_base=True,
            ),
            milestones,
            now,
        ),
        "proyectoAzure": stage_range.azure_project,
        "fechaInicio": to_iso_or_none(stage_range.start),
        "fechaFin": to_iso_or_none(stage_range.finish),
        "desviacionDias": days_until(stage_range.finish, now),
        "budget": round_half_up(budget, 2),
        "burn": round_half_up(burn, 2),
        "etc": round_half_up(budget - burn, 2),
        "desviacionHoras": round_half_up(budget - burn, 2),
        "avance": (
            round_half_up_int(burn / budget * 1000) / 10 if budget else 0
        ),
        "wi": (
            count_work_items(work_items, sprints)
            if work_items
            else empty_work_item_counts()
        ),
        "etapas": {
            stage: {"cerrada": is_closed}
            for stage, is_closed in stage_range.closed_stages.items()
        },
        "riesgos": list_open_risk_titles(work_items),
    }


def load_burn(sources: IxbSources, project_id: str) -> float:
    """
    Calcula las horas facturables de la nomenclatura vigente.

    Args:
        sources: Datos de entrada.
        project_id: ID de la nomenclatura vigente.

    Returns:
        Las horas; 0 si Clockify no respondio, igual que el original.
    """
    try:
        entries = sources.load_project_entries(project_id)
    except DashboardError as error:
        logger.warning(
            "Burn IXB/RaaS en 0 para %s: %s",
            project_id,
            error.detail,
        )
        return 0.0

    return calculate_exact_burn(entries, project_id)


def list_azure_projects(azure: AzureLookup | None) -> list[str]:
    """
    Lista los Team Projects; sin Azure configurado regresa vacio.

    Args:
        azure: Acceso a Azure DevOps, si esta configurado.

    Returns:
        Los nombres de los Team Projects.
    """
    if azure is None:
        return []

    try:
        return azure.list_project_names()
    except AzureDevOpsRequestError as error:
        logger.warning("No se listaron proyectos de Azure: %s", error.detail)
        return []


def load_stage_range(
    azure: AzureLookup | None,
    azure_project: str,
    sprints: list[str],
    now: datetime,
) -> AzureStageRange:
    """
    Calcula las etapas de Azure del proyecto.

    Args:
        azure: Acceso a Azure DevOps.
        azure_project: Team Project del proyecto.
        sprints: Nomenclaturas del proyecto.
        now: Fecha y hora local actual.

    Returns:
        El rango de etapas; vacio si no hay Team Project.
    """
    if azure is None or not azure_project:
        return AzureStageRange()

    try:
        iterations = azure.list_iterations(azure_project)
    except AzureDevOpsRequestError as error:
        logger.warning(
            "Iteraciones omitidas de %s: %s",
            azure_project,
            error.detail,
        )
        iterations = []

    return build_stage_range(azure_project, iterations, sprints, now.date())


def load_work_items(
    azure: AzureLookup | None,
    azure_project: str,
) -> list[JsonObject]:
    """
    Lee los work items del proyecto.

    Args:
        azure: Acceso a Azure DevOps.
        azure_project: Team Project del proyecto.

    Returns:
        Los work items; vacio si no hay Team Project o falla Azure.
    """
    if azure is None or not azure_project:
        return []

    try:
        return azure.list_work_items(azure_project)
    except AzureDevOpsRequestError as error:
        logger.warning(
            "Work items omitidos de %s: %s",
            azure_project,
            error.detail,
        )
        return []


def build_service_pivot(rows: Sequence[JsonObject]) -> list[JsonObject]:
    """
    Cuenta proyectos por Delivery Manager y servicio.

    Args:
        rows: Filas del resumen.

    Returns:
        Una fila por Delivery Manager.
    """
    pivot: dict[str, JsonObject] = {}

    for row in rows:
        manager = row["deliveryManager"] or UNASSIGNED_MANAGER
        entry = pivot.setdefault(
            manager,
            {"deliveryManager": manager, "total": 0},
        )
        entry[row["servicio"]] = entry.get(row["servicio"], 0) + 1
        entry["total"] += 1

    return sorted(
        pivot.values(),
        key=lambda entry: locale_key(entry["deliveryManager"]),
    )


def build_status_pivot(rows: Sequence[JsonObject]) -> list[JsonObject]:
    """
    Cuenta proyectos por Delivery Manager y etapa.

    Args:
        rows: Filas del resumen.

    Returns:
        Una fila por Delivery Manager con Sus, Dis, Dev y Dep.
    """
    pivot: dict[str, JsonObject] = {}

    for row in rows:
        manager = row["deliveryManager"] or UNASSIGNED_MANAGER
        entry = pivot.setdefault(
            manager,
            {
                "deliveryManager": manager,
                "Sus": 0,
                "Dis": 0,
                "Dev": 0,
                "Dep": 0,
                "total": 0,
            },
        )
        status = str(row["status"] or "").lower()
        pivot_key = next(
            (key for word, key in STATUS_PIVOT_KEYS if word in status),
            None,
        )

        if pivot_key is not None:
            entry[pivot_key] += 1

        entry["total"] += 1

    return sorted(
        pivot.values(),
        key=lambda entry: locale_key(entry["deliveryManager"]),
    )


def read_service(row: SheetRow) -> str:
    """
    Lee el servicio en mayusculas.

    Args:
        row: Fila de Proyectos.

    Returns:
        El servicio, por ejemplo IXB o RAAS.
    """
    return (
        to_text(get_flexible_value(row, ["Servicio", "Service"]))
        .upper()
        .strip()
    )


def to_iso_or_none(moment: datetime | None) -> str | None:
    """
    Convierte una fecha a ISO UTC.

    Args:
        moment: Fecha local o None.

    Returns:
        La fecha ISO, o None.
    """
    return to_utc_iso(moment) if moment is not None else None


def days_until(moment: datetime | None, now: datetime) -> int | None:
    """
    Dias que faltan para una fecha, como _diasHastaFecha().

    Args:
        moment: Fecha objetivo.
        now: Fecha y hora local actual.

    Returns:
        Dias (negativo si ya paso), o None si no hay fecha.
    """
    if moment is None:
        return None

    return (moment.date() - now.date()).days


def locale_key(text: str) -> tuple[str, str]:
    """
    Llave de orden parecida a localeCompare: sin acentos ni mayusculas.

    Args:
        text: Texto a ordenar.

    Returns:
        La llave de orden.
    """
    return strip_accents(text or "").lower(), text or ""
