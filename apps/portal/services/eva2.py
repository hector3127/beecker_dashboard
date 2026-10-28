"""Pantalla EVA 2: proyectos IXB y RaaS con avance en Azure DevOps."""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from apps.portal.constants import (
    EVA2_SERVICE_LABELS,
    EVA2_SERVICE_ORDER,
    EVA2_STAGE_KEYS,
    EVA2_STATUS_COLUMNS,
    EVA2_STATUS_WORDS,
    PROGRESS_ALERT_PERCENT,
)
from apps.portal.schemas import (
    Eva2Project,
    Eva2Row,
    Eva2View,
    StageCount,
)
from apps.portal.services.eva1 import format_short_date
from apps.portal.services.time_cost import build_time_cost

"""BKD.120.016 - EVA 2
Toma el resumen IXB/RaaS que ya calcula apps/ejecutivo (hoja Proyectos,
historico, Clockify y Azure DevOps, solo lectura) y arma los pivotes por
Delivery Manager y la tabla de proyectos con sus tareas por etapa.
"""

JsonObject = Mapping[str, Any]

UNASSIGNED = "Sin asignar"


def service_label(service: str) -> str:
    """
    Escribe un servicio como lo muestra el diseno.

    Args:
        service: Servicio en mayusculas, por ejemplo RAAS.

    Returns:
        El nombre para mostrar, por ejemplo RaaS.
    """
    return EVA2_SERVICE_LABELS.get(service, service)


def status_code(status: str) -> str:
    """
    Clasifica el estatus de un proyecto.

    Args:
        status: Estatus del historico (Discovery, Suspendido, etc.).

    Returns:
        sus, dis, dev, dep o vacio si no se reconoce.
    """
    lowered = status.lower()

    return next(
        (code for word, code in EVA2_STATUS_WORDS if word in lowered),
        "",
    )


def _stage_count(
    work_items: Mapping[str, Any],
    stages: Mapping[str, Any],
    key: str,
) -> StageCount:
    """Conteo de tareas de una etapa; en rojo si ya cerro y hay pendientes."""
    counts = work_items.get(key) or {}
    stage = stages.get(key) or {}
    pending = int(counts.get("pendientes") or 0)

    return StageCount(
        total=int(counts.get("total") or 0),
        closed=int(counts.get("cerrados") or 0),
        pending=pending,
        alert=bool(stage.get("cerrada")) and pending > 0,
    )


def build_eva2_project(row: JsonObject) -> Eva2Project:
    """
    Convierte una fila del resumen IXB/RaaS.

    Args:
        row: Fila con las llaves de obtenerResumenIXBRaaS.

    Returns:
        El proyecto con las alertas ya calculadas.
    """
    status = str(row.get("status") or "")
    work_items = row.get("wi") or {}
    stages = row.get("etapas") or {}
    progress = float(row.get("avance") or 0)

    return Eva2Project(
        manager=str(row.get("deliveryManager") or UNASSIGNED),
        project_id=str(row.get("idProyecto", "")),
        service=service_label(str(row.get("servicio", ""))),
        name=str(row.get("nombre", "")),
        status=status,
        status_code=status_code(status),
        start=format_short_date(str(row.get("fechaInicio") or "")[:10]),
        end=format_short_date(str(row.get("fechaFin") or "")[:10]),
        deviation_days=row.get("desviacionDias"),
        budget=float(row.get("budget") or 0),
        burn=float(row.get("burn") or 0),
        etc=float(row.get("etc") or 0),
        progress=progress,
        progress_bad=progress > PROGRESS_ALERT_PERCENT,
        stages=tuple(
            _stage_count(work_items, stages, key) for key in EVA2_STAGE_KEYS
        ),
        risks=len(row.get("riesgos") or []),
        risk_titles=tuple(str(title) for title in row.get("riesgos") or []),
        client=str(row.get("cliente") or row.get("account") or ""),
        budget_pending=bool(row.get("budget_pending")),
        hours_pending=bool(row.get("hours_pending")),
        azure_pending=bool(row.get("azure_pending")),
        hours_deviation=row.get("hoursDeviation"),
        progress_pending=bool(row.get("progress_pending")),
    )


def _service_columns(projects: Sequence[Eva2Project]) -> tuple[str, ...]:
    """Servicios presentes: primero IXB y RaaS, luego los demas."""
    present = {item.service for item in projects}
    preferred = [service_label(key) for key in EVA2_SERVICE_ORDER]
    extra = sorted(present - set(preferred))

    return tuple([*preferred, *extra])


def _pivot_rows(
    projects: Sequence[Eva2Project],
    columns: Sequence[str],
    column_of: Callable[[Eva2Project], str],
) -> tuple[tuple[Eva2Row, ...], Eva2Row]:
    """Cuenta proyectos por Delivery Manager y columna, con totales."""
    managers = sorted({item.manager for item in projects})
    rows = tuple(
        _count_row(
            name,
            [item for item in projects if item.manager == name],
            columns,
            column_of,
        )
        for name in managers
    )

    return rows, _count_row("Total", projects, columns, column_of)


def _count_row(
    name: str,
    projects: Sequence[Eva2Project],
    columns: Sequence[str],
    column_of: Callable[[Eva2Project], str],
) -> Eva2Row:
    """Una fila de pivote: cuantos proyectos caen en cada columna."""
    return Eva2Row(
        name=name,
        counts=tuple(
            sum(1 for item in projects if column_of(item) == column)
            for column in columns
        ),
        total=len(projects),
    )


def build_eva2_view(rows: Sequence[JsonObject]) -> Eva2View:
    """
    Arma la pantalla EVA 2.

    Args:
        rows: Filas del resumen IXB/RaaS.

    Returns:
        Totales, pivotes por Delivery Manager y tabla de proyectos.
    """
    projects = tuple(
        sorted(
            (build_eva2_project(row) for row in rows),
            key=lambda item: (item.manager.casefold(), item.project_id),
        ),
    )
    services = _service_columns(projects)
    service_rows, service_totals = _pivot_rows(
        projects,
        services,
        lambda item: item.service,
    )
    status_codes = tuple(code for code, _ in EVA2_STATUS_COLUMNS)
    status_rows, status_totals = _pivot_rows(
        projects,
        status_codes,
        lambda item: item.status_code,
    )
    suspended = [item for item in projects if item.status_code == "sus"]

    return Eva2View(
        total_projects=len(projects),
        suspended_count=len(suspended),
        suspended_note=" · ".join(
            f"{item.project_id} · {item.name}" for item in suspended
        ),
        services=services,
        service_rows=service_rows,
        service_totals=service_totals,
        status_rows=status_rows,
        status_totals=status_totals,
        projects=projects,
        time_cost=build_time_cost(
            (item.deviation_days for item in projects),
            (item.progress for item in projects),
        ),
    )
