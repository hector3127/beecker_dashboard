"""Detalle de un Delivery Manager y resumen de suspendidos."""

from collections.abc import Sequence

from apps.dashboard.constants import (
    CATEGORY_PAUSED,
    HEALTH_AT_RISK,
    HEALTH_CRITICAL,
    RISK_HIGH,
)
from apps.portal.constants import (
    NO_RISK_LABEL,
    SHARE_COLORS,
    STATUS_AT_RISK,
    STATUS_CRITICAL,
    STATUS_ON_TIME,
    STATUS_PAUSED,
)
from apps.portal.schemas import (
    ManagerDetail,
    ProjectRow,
    ProjectView,
    ShareRow,
    SuspendedRow,
    SuspendedSummary,
)
from apps.portal.services.portfolio_summary import (
    budget_used_percent,
    build_initials,
    count_health,
    percent_of,
    select_in_progress,
)
from apps.portal.services.slugs import build_slug
from apps.portal.services.time_cost import summarize_time_cost
from core.utils.numbers import round_half_up_int

"""BKD.120.013 - Detalle de Delivery Manager y suspendidos
Arma la pantalla de un Delivery Manager (sus proyectos en ejecucion y
suspendidos, con los que necesitan atencion primero) y el resumen de los
proyectos suspendidos de todo el portafolio.
"""

STATUS_LABELS = {
    STATUS_ON_TIME: "En tiempo",
    STATUS_AT_RISK: "En riesgo",
    STATUS_CRITICAL: "Crítico",
    STATUS_PAUSED: "Suspendido",
}

ROW_CLASSES = {STATUS_CRITICAL: "rs", STATUS_AT_RISK: "ra"}

# Orden de la tabla: criticos, en riesgo, en tiempo y al final suspendidos.
STATUS_ORDER = {
    STATUS_CRITICAL: 0,
    STATUS_AT_RISK: 1,
    STATUS_ON_TIME: 2,
    STATUS_PAUSED: 3,
}

MAX_RISK_NAMES = 2
BUDGET_LIMIT_PERCENT = 100


def find_manager(
    projects: Sequence[ProjectView],
    slug: str,
) -> tuple[str, list[ProjectView]] | None:
    """
    Busca a un Delivery Manager por su slug.

    Args:
        projects: Todos los proyectos.
        slug: Identificador de la URL.

    Returns:
        El nombre y sus proyectos, o None si no existe.
    """
    for name in sorted({item.delivery_manager for item in projects}):
        if build_slug(name) == slug:
            return name, [
                item for item in projects if item.delivery_manager == name
            ]

    return None


def classify_status(project: ProjectView) -> str:
    """
    Clasifica un proyecto para las tablas.

    Args:
        project: Proyecto a clasificar.

    Returns:
        El codigo: g (en tiempo), a (en riesgo), r (critico) o x
        (suspendido).
    """
    if project.status_category == CATEGORY_PAUSED:
        return STATUS_PAUSED

    if project.health == HEALTH_CRITICAL:
        return STATUS_CRITICAL

    if project.health == HEALTH_AT_RISK:
        return STATUS_AT_RISK

    return STATUS_ON_TIME


def build_status_detail(project: ProjectView, status_code: str) -> str:
    """
    Explica en una linea por que un proyecto no va bien.

    Args:
        project: Proyecto a explicar.
        status_code: Codigo de classify_status.

    Returns:
        "Presupuesto usado: 125%", "12 días atrasado" o vacio.
    """
    if status_code not in (STATUS_CRITICAL, STATUS_AT_RISK):
        return ""

    used = budget_used_percent(project)

    if used > BUDGET_LIMIT_PERCENT:
        return f"Presupuesto usado: {used}%"

    if project.delay_days >= 1:
        return f"{project.delay_days} días atrasado"

    return ""


def build_project_row(project: ProjectView) -> ProjectRow:
    """
    Convierte un proyecto en un renglon de la tabla.

    Args:
        project: Proyecto a mostrar.

    Returns:
        El renglon con estado, avance, ETC y riesgo.
    """
    status_code = classify_status(project)

    return ProjectRow(
        project_id=project.project_id,
        name=project.name,
        client=project.client,
        status_label=STATUS_LABELS[status_code],
        status_code=status_code,
        detail=build_status_detail(project, status_code),
        progress_percent=project.progress_percent,
        etc_hours=round_half_up_int(project.etc_hours),
        risk_label=project.risk_level or NO_RISK_LABEL,
        row_class=ROW_CLASSES.get(status_code, ""),
        client_slug=build_slug(project.client) if project.client else "",
    )


def build_manager_detail(
    name: str,
    projects: Sequence[ProjectView],
) -> ManagerDetail:
    """
    Arma el detalle de un Delivery Manager.

    Args:
        name: Nombre del Delivery Manager.
        projects: Proyectos asignados a esa persona.

    Returns:
        Totales, tabla de proyectos y reparto por estado.
    """
    in_progress = select_in_progress(projects)
    paused = [
        item for item in projects if item.status_category == CATEGORY_PAUSED
    ]
    listed = sorted(
        [*in_progress, *paused],
        key=lambda item: (
            STATUS_ORDER[classify_status(item)],
            -item.delay_days,
            item.name,
        ),
    )
    health = count_health(in_progress)
    high_risk = [item for item in in_progress if item.risk_level == RISK_HIGH]

    return ManagerDetail(
        name=name,
        initials=build_initials(name),
        total=len(listed),
        in_progress=len(in_progress),
        paused=len(paused),
        health=health,
        high_risk=len(high_risk),
        high_risk_note=_describe_risks(high_risk),
        rows=tuple(build_project_row(item) for item in listed),
        shares=build_shares(health.on_time, health.at_risk, health.critical),
        time_cost=summarize_time_cost(in_progress),
    )


def _describe_risks(projects: Sequence[ProjectView]) -> str:
    """Texto "En A y B" con los proyectos de riesgo alto."""
    if not projects:
        return "Sin riesgos altos abiertos"

    names = [item.name for item in projects[:MAX_RISK_NAMES]]
    extra = len(projects) - len(names)
    text = " y ".join(names)

    if extra > 0:
        text = f"{text} y {extra} más"

    return f"En {text}"


def build_shares(
    on_time: int, at_risk: int, critical: int
) -> tuple[ShareRow, ...]:
    """Reparto de proyectos en ejecucion por estado."""
    total = on_time + at_risk + critical
    definitions = (
        (STATUS_ON_TIME, on_time),
        (STATUS_AT_RISK, at_risk),
        (STATUS_CRITICAL, critical),
    )

    return tuple(
        ShareRow(
            label=STATUS_LABELS[code],
            status_code=code,
            color=SHARE_COLORS[code],
            count=count,
            percent=percent_of(count, total),
        )
        for code, count in definitions
    )


def summarize_suspended(projects: Sequence[ProjectView]) -> SuspendedSummary:
    """
    Resume los proyectos suspendidos de todo el portafolio.

    Args:
        projects: Todos los proyectos.

    Returns:
        Conteo total y por Delivery Manager, horas pendientes y detalle.
    """
    paused = sorted(
        (item for item in projects if item.status_category == CATEGORY_PAUSED),
        key=lambda item: (item.delivery_manager, item.name),
    )
    managers = {item.delivery_manager for item in projects}
    by_manager = sorted(
        (
            (
                name,
                sum(1 for item in paused if item.delivery_manager == name),
            )
            for name in managers
        ),
        key=lambda pair: (-pair[1], pair[0]),
    )

    return SuspendedSummary(
        count=len(paused),
        by_manager=tuple(by_manager),
        etc_hours=round_half_up_int(sum(item.etc_hours for item in paused)),
        rows=tuple(
            SuspendedRow(
                project_id=item.project_id,
                name=item.name,
                client=item.client,
                delivery_manager=item.delivery_manager,
                progress_percent=item.progress_percent,
                etc_hours=round_half_up_int(item.etc_hours),
                client_slug=build_slug(item.client) if item.client else "",
            )
            for item in paused
        ),
    )
