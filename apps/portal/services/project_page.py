"""Pantalla de un proyecto: presupuesto, avance, riesgos y historial."""

from collections.abc import Mapping
from datetime import date
from typing import Any

from apps.ejecutivo.services.history_stages import STATE_COMPLETED
from apps.portal.constants import (
    PROJECT_BAR_SCALE_PERCENT,
)
from apps.portal.schemas import (
    BarValue,
    ProjectPage,
    ProjectRisk,
    ProjectView,
    TeamRole,
    TimelineEvent,
)
from apps.portal.services.decisions import decision_for
from apps.portal.services.manager_detail import (
    STATUS_LABELS,
    classify_status,
)
from apps.portal.services.portfolio_summary import budget_used_percent
from apps.portal.services.slugs import build_slug
from core.utils.numbers import round_half_up_int

"""BKD.120.017 - Pantalla de proyecto
Junta los datos del portafolio con el dashboard ejecutivo del proyecto
(getDashboardEjecutivoProyecto): tiempo transcurrido, riesgos abiertos,
equipo por rol e historial de hitos. El dinero en USD y el Gross Margin
no existen en Sheets y no se calculan.
"""

BUDGET_LIMIT_PERCENT = 100
OVER_BUDGET_COLOR = "#D6304B"
PROGRESS_COLOR = "#5B2FD6"
ELAPSED_COLOR = "#8A81B8"
NO_ROLE = "Sin rol"
ISO_DATE_LENGTH = 10


def build_project_page(
    project: ProjectView,
    dashboard: Mapping[str, Any],
    today: date,
) -> ProjectPage:
    """
    Arma la pantalla de un proyecto.

    Args:
        project: El proyecto del portafolio.
        dashboard: Resultado de getDashboardEjecutivoProyecto(); puede
            venir vacio cuando no se pudo leer.
        today: Fecha local de hoy.

    Returns:
        La pantalla con sus tarjetas; lo que no se pudo leer queda vacio.
    """
    data = _as_mapping(dashboard.get("proyecto"))
    end_date = _read_date(data.get("fechaFinEstimada"))
    start_date = _read_date(data.get("fechaInicio"))
    avance = _as_mapping(dashboard.get("avance"))
    elapsed = _read_percent(avance.get("pctTiempoTranscurrido"))
    used = budget_used_percent(project)
    status_code = classify_status(project)

    return ProjectPage(
        project_id=project.project_id,
        name=project.name,
        client=project.client,
        delivery_manager=project.delivery_manager,
        client_slug=build_slug(project.client) if project.client else "",
        end_date=_format_date(end_date),
        status_label=STATUS_LABELS[status_code],
        status_code=status_code,
        decision=decision_for(project),
        budget_used=used,
        budget_hours=round_half_up_int(project.budget_hours),
        burn_hours=round_half_up_int(project.burn_hours),
        progress=project.progress_percent,
        etc_hours=round_half_up_int(project.etc_hours),
        bars=_build_bars(used, project.progress_percent, elapsed),
        marker_left=_bar_width(BUDGET_LIMIT_PERCENT),
        summary=_build_summary(
            used,
            project.progress_percent,
            elapsed,
            _days_left(end_date, today),
        ),
        risks=_read_risks(dashboard.get("riesgosCriticos")),
        team=_read_team(dashboard.get("filasRecursosCompleto")),
        events=_read_events(
            dashboard.get("hitos"),
            start_date,
            end_date,
            today,
        ),
    )


def _build_bars(
    used: int,
    progress: int,
    elapsed: int | None,
) -> tuple[BarValue, ...]:
    """Tres barras: presupuesto usado, avance y tiempo transcurrido."""
    bars = [
        BarValue(
            "Presupuesto usado",
            f"{used}%",
            _bar_width(used),
            OVER_BUDGET_COLOR
            if used > BUDGET_LIMIT_PERCENT
            else PROGRESS_COLOR,
        ),
        BarValue(
            "Avance en horas",
            f"{progress}%",
            _bar_width(progress),
            PROGRESS_COLOR,
        ),
    ]

    if elapsed is not None:
        bars.append(
            BarValue(
                "Tiempo transcurrido",
                f"{elapsed}%",
                _bar_width(elapsed),
                ELAPSED_COLOR,
            ),
        )

    return tuple(bars)


def _bar_width(percent: int) -> float:
    """Ancho de la barra en una escala de 0 a 150%."""
    capped = max(0, min(percent, PROJECT_BAR_SCALE_PERCENT))

    return round(capped * 100 / PROJECT_BAR_SCALE_PERCENT, 1)


def _build_summary(
    used: int,
    progress: int,
    elapsed: int | None,
    days_left: int | None,
) -> str:
    """Frase que compara lo gastado, lo avanzado y el tiempo."""
    gap = used - progress

    if gap > 0:
        text = f"Lo gastado va {gap} puntos por encima del trabajo avanzado."
    elif gap < 0:
        text = f"El trabajo avanzado va {-gap} puntos por encima de lo gastado."
    else:
        text = "Lo gastado y el trabajo avanzado van parejos."

    if elapsed is not None and days_left is not None:
        if days_left >= 0:
            text += (
                f" Con {elapsed}% del tiempo transcurrido, quedan "
                f"{days_left} días para la fecha de entrega."
            )
        else:
            text += (
                f" Con {elapsed}% del tiempo transcurrido, la fecha de "
                f"entrega pasó hace {-days_left} días."
            )

    return text


def _days_left(end_date: date | None, today: date) -> int | None:
    """Dias que faltan para la fecha estimada (negativo si ya paso)."""
    if end_date is None:
        return None

    return (end_date - today).days


def _read_risks(raw: object) -> tuple[ProjectRisk, ...]:
    """Riesgos abiertos del dashboard."""
    if not isinstance(raw, list):
        return ()

    return tuple(
        ProjectRisk(
            description=_text(item.get("descripcion")),
            impact=_text(item.get("impacto")),
            probability=_text(item.get("probabilidad")),
        )
        for item in raw
        if isinstance(item, dict)
    )


def _read_team(raw: object) -> tuple[TeamRole, ...]:
    """Personas y horas reales por rol, de mayor a menor."""
    if not isinstance(raw, list):
        return ()

    people: dict[str, set[str]] = {}
    hours: dict[str, float] = {}

    for item in raw:
        if not isinstance(item, dict):
            continue

        role = _text(item.get("posicion")) or NO_ROLE
        people.setdefault(role, set()).add(_text(item.get("nombre")))
        value = item.get("horasReales")
        hours[role] = hours.get(role, 0.0) + (
            float(value) if isinstance(value, int | float) else 0.0
        )

    return tuple(
        TeamRole(role, len(people[role]), round_half_up_int(hours[role]))
        for role in sorted(hours, key=lambda name: (-hours[name], name))
    )


def _read_events(
    raw: object,
    start_date: date | None,
    end_date: date | None,
    today: date,
) -> tuple[TimelineEvent, ...]:
    """Historial: hitos, inicio y fecha estimada, del mas nuevo al viejo."""
    dated: list[tuple[date, TimelineEvent]] = []

    if start_date is not None:
        dated.append(
            (
                start_date,
                TimelineEvent(
                    _format_date(start_date),
                    "Inicio del proyecto",
                    "Fecha de inicio registrada en la hoja Proyectos.",
                    True,
                ),
            ),
        )

    if end_date is not None:
        dated.append(
            (
                end_date,
                TimelineEvent(
                    _format_date(end_date),
                    "Fecha estimada de entrega",
                    "Fin estimado según la hoja Proyectos.",
                    end_date <= today,
                ),
            ),
        )

    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            event = _read_milestone(item)

            if event is not None:
                dated.append(event)

    dated.sort(key=lambda pair: pair[0], reverse=True)

    return tuple(event for _, event in dated)


def _read_milestone(
    item: Mapping[str, Any],
) -> tuple[date, TimelineEvent] | None:
    """Convierte un hito del dashboard en un evento con fecha."""
    plan_end = _read_date(item.get("fechaFinPlan"))
    real_end = _read_date(item.get("fechaFinReal"))
    moment = (
        real_end
        or plan_end
        or _read_date(item.get("fechaInicioReal"))
        or _read_date(item.get("fechaInicioPlan"))
    )

    if moment is None:
        return None

    state = _text(item.get("estado"))
    parts = [state] if state else []

    if plan_end is not None:
        parts.append(f"Fin planeado: {_format_date(plan_end)}")

    return (
        moment,
        TimelineEvent(
            _format_date(moment),
            _text(item.get("nombre")) or "Hito",
            ". ".join(parts),
            state.lower() == STATE_COMPLETED.lower(),
        ),
    )


def _read_date(value: object) -> date | None:
    """Fecha de un texto ISO (solo los primeros 10 caracteres)."""
    if not isinstance(value, str):
        return None

    try:
        return date.fromisoformat(value[:ISO_DATE_LENGTH])
    except ValueError:
        return None


def _format_date(value: date | None) -> str:
    """dd/mm/aaaa, o vacio cuando no hay fecha."""
    return value.strftime("%d/%m/%Y") if value is not None else ""


def _read_percent(value: object) -> int | None:
    """Porcentaje entero, o None si no es numerico."""
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None

    return round_half_up_int(value)


def _as_mapping(value: object) -> Mapping[str, Any]:
    """El valor si es un diccionario; si no, uno vacio."""
    return value if isinstance(value, dict) else {}


def _text(value: object) -> str:
    """Texto sin espacios; vacio cuando no hay valor."""
    return "" if value is None else str(value).strip()
