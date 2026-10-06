"""Etapas, fechas y conteo de work items desde Azure DevOps."""

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from apps.azure_devops.services.project_resolver import normalize_azure_name
from core.utils.dates import to_datetime
from core.utils.text import to_text

"""BKD.040.008 - Etapas de Azure por proyecto
Equivale a _altoNivelRangoAzureProyecto(), _altoNivelConteoWI() y
_altoNivelRiesgos():
- Inicio = inicio mas temprano de Discovery.
- Fin = fin mas tardio de Deployment.
- Las iteraciones se filtran por la nomenclatura del ID (S1, S2, CR).
"""

JsonObject = dict[str, Any]

STAGES = ("Discovery", "Development", "Deployment")
STAGE_PENDING = "Pendiente"

SPRINT_SUFFIX = re.compile(r"_(CR\d*|S\d+)$")
PATH_SPRINT_CODE = re.compile(r"(?:\\|_)(S\d+|CR)(?:\\|_|$)", re.IGNORECASE)

CLOSED_WORK_ITEM_STATES = frozenset(
    {
        "NOT APPLICABLE",
        "CANCELLED",
        "CLOSED",
        "REJECTED",
        "COMPLETED",
        "INACTIVE",
    },
)
CLOSED_RISK_STATES = frozenset({"CLOSED", "RESOLVED", "REMOVED", "DONE"})
RISK_TYPE = "RISK"


@dataclass(slots=True)
class StageIteration:
    """Iteracion de Azure clasificada por etapa."""

    stage: str
    path: str
    start: datetime | None
    finish: datetime | None


@dataclass(slots=True)
class AzureStageRange:
    """Fechas y etapa actual de un proyecto en Azure."""

    azure_project: str = ""
    start: datetime | None = None
    finish: datetime | None = None
    current_stage: str = ""
    closed_stages: dict[str, bool] = field(
        default_factory=lambda: {stage.lower(): False for stage in STAGES},
    )


def infer_sprint(project_id: str) -> str:
    """
    Obtiene la nomenclatura del ID, como _inferirSprintDesdeId().

    Args:
        project_id: ID interno, por ejemplo RAS.001_CR1.

    Returns:
        S#, CR# o S1 si el ID no tiene sufijo.
    """
    match = SPRINT_SUFFIX.search(to_text(project_id).upper())

    return match.group(1) if match else "S1"


def stage_from_path(path: str) -> str:
    """
    Detecta la etapa en el texto de la iteracion.

    Args:
        path: Ruta o nombre de la iteracion.

    Returns:
        Discovery, Development, Deployment o cadena vacia.
    """
    lowered_path = path.lower()

    for stage in STAGES:
        if stage.lower() in lowered_path:
            return stage

    return ""


def path_matches_sprint(path: str, sprint: str) -> bool:
    """
    Indica si la ruta corresponde a la nomenclatura (General_S1, S2, CR).

    Args:
        path: Ruta de la iteracion o del work item.
        sprint: Nomenclatura buscada.

    Returns:
        True si la ruta contiene la nomenclatura.
    """
    normalized_sprint = normalize_azure_name(sprint)

    if not normalized_sprint:
        return True

    pattern = re.compile(
        rf"(?:\\|_|\b){re.escape(normalized_sprint)}(?:\\|_|\b|$)",
        re.IGNORECASE,
    )

    return bool(pattern.search(normalize_azure_name(path)))


def build_stage_range(
    azure_project: str,
    iterations: Sequence[JsonObject],
    sprints: Sequence[str],
    today: date,
) -> AzureStageRange:
    """
    Calcula fechas, etapa actual y etapas cerradas de un proyecto.

    Args:
        azure_project: Team Project de Azure; vacio si no hay.
        iterations: Iteraciones del Team Project.
        sprints: Nomenclaturas de las filas del proyecto.
        today: Fecha local de hoy.

    Returns:
        El rango de etapas del proyecto.
    """
    if not azure_project:
        return AzureStageRange()

    staged = [
        StageIteration(
            stage=stage_from_path(
                to_text(iteration.get("path") or iteration.get("nombre")),
            ),
            path=to_text(iteration.get("path")),
            start=to_datetime(iteration.get("fechaInicio")),
            finish=to_datetime(iteration.get("fechaFin")),
        )
        for iteration in iterations
    ]
    staged = [iteration for iteration in staged if iteration.stage]
    relevant = [
        iteration
        for iteration in staged
        if any(
            path_matches_sprint(iteration.path, sprint) for sprint in sprints
        )
    ] or staged

    discovery_starts = [
        iteration.start
        for iteration in relevant
        if iteration.stage == "Discovery" and iteration.start
    ]
    deployment_ends = [
        iteration.finish
        for iteration in relevant
        if iteration.stage == "Deployment" and iteration.finish
    ]

    return AzureStageRange(
        azure_project=azure_project,
        start=min(discovery_starts) if discovery_starts else None,
        finish=max(deployment_ends) if deployment_ends else None,
        current_stage=find_current_stage(relevant, today) or STAGE_PENDING,
        closed_stages={
            stage.lower(): is_stage_closed(relevant, stage, today)
            for stage in STAGES
        },
    )


def find_current_stage(
    iterations: Sequence[StageIteration],
    today: date,
) -> str:
    """
    Determina la etapa actual; si hay traslape muestra ambas.

    Args:
        iterations: Iteraciones relevantes.
        today: Fecha local de hoy.

    Returns:
        La etapa actual, la siguiente futura o la ultima pasada.
    """
    active_stages = [
        stage
        for stage in STAGES
        if any(
            iteration.stage == stage
            and iteration.start is not None
            and iteration.finish is not None
            and iteration.start.date() <= today <= iteration.finish.date()
            for iteration in iterations
        )
    ]

    if active_stages:
        return " / ".join(active_stages)

    today_start = datetime(today.year, today.month, today.day)
    future = sorted(
        (
            iteration
            for iteration in iterations
            if iteration.start is not None and iteration.start > today_start
        ),
        key=lambda iteration: iteration.start or today_start,
    )

    if future:
        return future[0].stage

    past = sorted(
        (iteration for iteration in iterations if iteration.finish),
        key=lambda iteration: iteration.finish or today_start,
        reverse=True,
    )

    return past[0].stage if past else ""


def is_stage_closed(
    iterations: Sequence[StageIteration],
    stage: str,
    today: date,
) -> bool:
    """
    Indica si la etapa ya termino (hoy es posterior a su ultimo fin).

    Args:
        iterations: Iteraciones relevantes.
        stage: Etapa a evaluar.
        today: Fecha local de hoy.

    Returns:
        True cuando la etapa esta cerrada.
    """
    stage_ends = [
        iteration.finish
        for iteration in iterations
        if iteration.stage == stage and iteration.finish
    ]

    return bool(stage_ends) and today > max(stage_ends).date()


def empty_work_item_counts() -> JsonObject:
    """
    Crea el conteo vacio de work items.

    Returns:
        Conteos en cero para general y cada etapa.
    """
    return {
        group: {"total": 0, "cerrados": 0, "pendientes": 0}
        for group in ("general", "discovery", "development", "deployment")
    }


def count_work_items(
    work_items: Sequence[JsonObject],
    sprints: Sequence[str],
) -> JsonObject:
    """
    Cuenta work items cerrados y pendientes, en general y por etapa.

    Args:
        work_items: Work items del Team Project.
        sprints: Nomenclaturas de las filas del proyecto.

    Returns:
        El conteo con la forma de _altoNivelConteoWI().
    """
    counts = empty_work_item_counts()

    for work_item in work_items:
        fields = work_item.get("fields") or {}
        path = to_text(fields.get("System.IterationPath"))
        is_closed = (
            normalize_azure_name(to_text(fields.get("System.State")))
            in CLOSED_WORK_ITEM_STATES
        )
        add_to_count(counts["general"], is_closed)

        stage = stage_from_path(path)

        if not stage:
            continue

        # Si la ruta trae S#/CR, se respeta; si no, el work item cuenta
        # como respaldo para la etapa.
        if PATH_SPRINT_CODE.search(path) and not any(
            path_matches_sprint(path, sprint) for sprint in sprints
        ):
            continue

        add_to_count(counts[stage.lower()], is_closed)

    return counts


def add_to_count(group: JsonObject, is_closed: bool) -> None:
    """
    Suma un work item a un grupo del conteo.

    Args:
        group: Grupo con total, cerrados y pendientes.
        is_closed: Indica si el work item esta cerrado.
    """
    group["total"] += 1
    group["cerrados" if is_closed else "pendientes"] += 1


def list_open_risk_titles(work_items: Sequence[JsonObject]) -> list[str]:
    """
    Lista los titulos de riesgos no cerrados, como _altoNivelRiesgos().

    Args:
        work_items: Work items del Team Project.

    Returns:
        Los titulos de los riesgos abiertos.
    """
    titles: list[str] = []

    for work_item in work_items:
        fields = work_item.get("fields") or {}
        work_item_type = normalize_azure_name(
            to_text(fields.get("System.WorkItemType")),
        )
        state = normalize_azure_name(to_text(fields.get("System.State")))
        title = to_text(fields.get("System.Title"))

        if work_item_type == RISK_TYPE and state not in CLOSED_RISK_STATES:
            if title:
                titles.append(title)

    return titles
