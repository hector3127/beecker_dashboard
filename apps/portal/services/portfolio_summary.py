"""Resumenes del portafolio para Operativa (funciones puras)."""

import math
from collections.abc import Sequence

from apps.dashboard.constants import (
    CATEGORY_ACTIVE,
    CATEGORY_PAUSED,
    HEALTH_AT_RISK,
    HEALTH_CRITICAL,
    HEALTH_ON_TIME,
    RISK_HIGH,
)
from apps.portal.constants import (
    COLOR_AT_RISK,
    COLOR_DONUT_CRITICAL,
    COLOR_ON_TIME,
    DONUT_RADIUS,
    NO_DELIVERY_MANAGER,
)
from apps.portal.schemas import (
    DeliveryManagerSummary,
    DonutSegment,
    HealthCount,
    HoursSummary,
    PortfolioSummary,
    ProjectView,
)
from apps.portal.services.slugs import build_slug
from core.utils.numbers import round_half_up_int

"""BKD.120.005 - Resumen del portafolio
Cuenta proyectos en ejecucion, suspendidos y por salud, y los agrupa por
Delivery Manager. Salud = proyectos en tiempo entre proyectos en
ejecucion; los suspendidos no se cuentan.
"""


def count_health(projects: Sequence[ProjectView]) -> HealthCount:
    """
    Cuenta proyectos por salud.

    Args:
        projects: Proyectos a contar.

    Returns:
        Conteo de en tiempo, en riesgo y criticos.
    """
    return HealthCount(
        on_time=sum(1 for item in projects if item.health == HEALTH_ON_TIME),
        at_risk=sum(1 for item in projects if item.health == HEALTH_AT_RISK),
        critical=sum(1 for item in projects if item.health == HEALTH_CRITICAL),
    )


def percent_of(part: int, total: int) -> int:
    """
    Calcula un porcentaje entero.

    Args:
        part: Cantidad parcial.
        total: Cantidad total.

    Returns:
        El porcentaje redondeado; 0 cuando el total es cero.
    """
    if total <= 0:
        return 0

    return round_half_up_int(part * 100 / total)


def select_in_progress(
    projects: Sequence[ProjectView],
) -> list[ProjectView]:
    """
    Filtra los proyectos en ejecucion.

    Args:
        projects: Todos los proyectos.

    Returns:
        Los proyectos con categoria Activo.
    """
    return [
        item for item in projects if item.status_category == CATEGORY_ACTIVE
    ]


def summarize_portfolio(projects: Sequence[ProjectView]) -> PortfolioSummary:
    """
    Calcula los totales de las tarjetas de Operativa.

    Args:
        projects: Todos los proyectos.

    Returns:
        Proyectos en ejecucion, suspendidos y salud general.
    """
    in_progress = select_in_progress(projects)
    health = count_health(in_progress)
    paused = sum(
        1 for item in projects if item.status_category == CATEGORY_PAUSED
    )

    return PortfolioSummary(
        in_progress=len(in_progress),
        paused=paused,
        health=health,
        on_time_percent=percent_of(health.on_time, len(in_progress)),
    )


def build_initials(name: str) -> str:
    """
    Arma las iniciales de un nombre para el circulo de la tarjeta.

    Args:
        name: Nombre completo o de pila.

    Returns:
        Hasta dos letras en mayusculas.
    """
    words = [word for word in name.split() if word]

    if not words:
        return "?"

    if len(words) == 1:
        return words[0][:2].upper()

    return (words[0][0] + words[1][0]).upper()


def summarize_delivery_managers(
    projects: Sequence[ProjectView],
) -> list[DeliveryManagerSummary]:
    """
    Agrupa el portafolio por Delivery Manager.

    Args:
        projects: Todos los proyectos.

    Returns:
        Un resumen por Delivery Manager, el de mas proyectos primero y
        "Sin Delivery Manager" siempre al final.
    """
    names = {item.delivery_manager for item in projects}
    summaries = [
        _summarize_manager(
            name,
            [item for item in projects if item.delivery_manager == name],
        )
        for name in names
    ]

    return sorted(
        summaries,
        key=lambda item: (
            item.name == NO_DELIVERY_MANAGER,
            -item.in_progress,
            item.name,
        ),
    )


def _summarize_manager(
    name: str,
    projects: Sequence[ProjectView],
) -> DeliveryManagerSummary:
    """Resume los proyectos de un solo Delivery Manager."""
    from apps.portal.services.time_cost import (
        summarize_time_cost,  # noqa: PLC0415
    )

    in_progress = select_in_progress(projects)
    health = count_health(in_progress)
    total = health.total

    return DeliveryManagerSummary(
        name=name,
        slug=build_slug(name),
        initials=build_initials(name),
        in_progress=len(in_progress),
        paused=sum(
            1 for item in projects if item.status_category == CATEGORY_PAUSED
        ),
        health=health,
        high_risk=sum(
            1 for item in in_progress if item.risk_level == RISK_HIGH
        ),
        on_time_width=_width(health.on_time, total),
        at_risk_width=_width(health.at_risk, total),
        critical_width=_width(health.critical, total),
        time_cost=summarize_time_cost(in_progress),
        project_ids=tuple(sorted({item.project_id for item in in_progress})),
    )


def _width(part: int, total: int) -> float:
    """Ancho porcentual de un tramo de la barra, con un decimal."""
    if total <= 0:
        return 0.0

    return round(part * 100 / total, 1)


def build_donut_segments(health: HealthCount) -> list[DonutSegment]:
    """
    Calcula los arcos de la dona de salud.

    Args:
        health: Conteo de proyectos por salud.

    Returns:
        Tres segmentos (en tiempo, en riesgo, criticos) con su trazo.
    """
    circumference = 2 * math.pi * DONUT_RADIUS
    total = health.total
    definitions = (
        ("En tiempo", health.on_time, COLOR_ON_TIME),
        ("En riesgo", health.at_risk, COLOR_AT_RISK),
        ("Críticos", health.critical, COLOR_DONUT_CRITICAL),
    )
    segments: list[DonutSegment] = []
    consumed = 0.0

    for label, count, color in definitions:
        dash = circumference * count / total if total else 0.0
        segments.append(
            DonutSegment(
                label=label,
                count=count,
                percent=percent_of(count, total),
                color=color,
                dash=round(dash, 1),
                gap=round(circumference - dash, 1),
                offset=round(-consumed, 1),
            ),
        )
        consumed += dash

    return segments


def summarize_hours(projects: Sequence[ProjectView]) -> HoursSummary:
    """
    Suma las horas de los proyectos en ejecucion.

    Args:
        projects: Todos los proyectos.

    Returns:
        Horas planeadas, usadas, por terminar y el avance en horas.
    """
    in_progress = select_in_progress(projects)
    budget = sum(item.budget_hours for item in in_progress)
    burn = sum(item.burn_hours for item in in_progress)
    etc = sum(item.etc_hours for item in in_progress)
    progress = round_half_up_int(burn * 100 / budget) if budget > 0 else 0

    return HoursSummary(
        budget_hours=round_half_up_int(budget),
        burn_hours=round_half_up_int(burn),
        etc_hours=round_half_up_int(etc),
        progress_percent=progress,
    )


def budget_used_percent(project: ProjectView) -> int:
    """
    Calcula el porcentaje del presupuesto en horas que ya se uso.

    Args:
        project: Proyecto a evaluar.

    Returns:
        El porcentaje usado; 0 cuando no hay presupuesto.
    """
    if project.budget_hours <= 0:
        return 0

    return round_half_up_int(project.burn_hours * 100 / project.budget_hours)
