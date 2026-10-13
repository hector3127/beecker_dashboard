"""Calculo de T (en tiempo) y C (en costo)."""

from collections.abc import Iterable, Sequence

from apps.portal.schemas import ProjectView, TimeCost
from apps.portal.services.portfolio_summary import select_in_progress

"""BKD.120.020 - T y C
Formula confirmada por el equipo:
- T (en tiempo) = promedio de la desviacion en dias de los proyectos.
- C (en costo) = promedio del avance (% de horas consumidas sobre el
  presupuesto).
Los proyectos sin dato no entran al promedio.
"""

DECIMALS = 1


def average(values: Iterable[float | int | None]) -> float | None:
    """
    Promedio de los valores que existen.

    Args:
        values: Numeros; None se ignora.

    Returns:
        El promedio con un decimal, o None si no hay ningun numero.
    """
    numbers = [float(value) for value in values if value is not None]

    if not numbers:
        return None

    return round(sum(numbers) / len(numbers), DECIMALS)


def build_time_cost(
    deviations: Iterable[float | int | None],
    progresses: Iterable[float | int | None],
) -> TimeCost:
    """
    Arma T y C a partir de las desviaciones y los avances.

    Args:
        deviations: Desviacion en dias de cada proyecto.
        progresses: Avance en porcentaje de cada proyecto.

    Returns:
        T en dias y C en porcentaje.
    """
    return TimeCost(
        time_days=average(deviations),
        cost_percent=average(progresses),
    )


def summarize_time_cost(projects: Sequence[ProjectView]) -> TimeCost:
    """
    T y C de los proyectos en ejecucion del portafolio.

    Args:
        projects: Proyectos (se toman solo los en ejecucion).

    Returns:
        T con los dias de retraso y C con el avance en horas.
    """
    in_progress = select_in_progress(projects)

    return build_time_cost(
        (item.delay_days for item in in_progress),
        (item.progress_percent for item in in_progress),
    )
