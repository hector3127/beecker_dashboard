"""Inicio y fin de un proyecto segun sus iteraciones de Azure DevOps."""

import re
from collections.abc import Sequence
from typing import Any

from apps.capacidad.exceptions import CapacityError
from apps.capacidad.services.capacity_text import normalize_capacity_text
from core.utils.text import to_text

"""BKD.050.008 - Rango de Azure
Equivale a ciRangoAzure_():
- Con Iteration Path se usan ese nodo y sus hijos.
- Sin Iteration Path se usan las iteraciones con la nomenclatura del ID
  (S1 si el ID no tiene sufijo).
- Inicio es la fecha menor y fin la mayor de las iteraciones validas.
"""

JsonObject = dict[str, Any]

PATH_SEPARATOR = "\\"
ID_SUFFIX = re.compile(r"_(S\d+|CR\d*)\Z")
ANY_SPRINT_NAME = re.compile(r"_S\d+\Z", re.IGNORECASE)
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
DEFAULT_SPRINT = "S1"


def resolve_azure_range(
    iterations: Sequence[JsonObject],
    project_id: str,
    iteration_path: str,
) -> tuple[str, str]:
    """
    Calcula el inicio y fin del proyecto con sus iteraciones.

    Args:
        iterations: Iteraciones en lista plana (path, fechaInicio,
            fechaFin), en el orden del arbol.
        project_id: ID interno del proyecto.
        iteration_path: Iteration Path de Recursos; vacio si no hay.

    Returns:
        Inicio y fin en formato YYYY-MM-DD.

    Raises:
        CapacityError: Cuando no hay iteraciones o fechas validas.
    """
    if iteration_path:
        subset = select_iteration_subtree(iterations, iteration_path)
    else:
        subset = select_sprint_iterations(iterations, project_id)

    date_ranges = [
        (
            to_text(iteration.get("fechaInicio") or "")[:10],
            to_text(iteration.get("fechaFin") or "")[:10],
        )
        for iteration in subset
    ]
    valid_ranges = [
        (start, finish)
        for start, finish in date_ranges
        if ISO_DAY.fullmatch(start)
        and ISO_DAY.fullmatch(finish)
        and start <= finish
    ]

    if not valid_ranges:
        raise CapacityError(
            f"Azure no tiene inicio y fin válidos para {project_id}.",
        )

    return (
        min(start for start, _ in valid_ranges),
        max(finish for _, finish in valid_ranges),
    )


def select_iteration_subtree(
    iterations: Sequence[JsonObject],
    iteration_path: str,
) -> list[JsonObject]:
    """
    Toma la iteracion indicada y todas sus hijas.

    Args:
        iterations: Iteraciones en lista plana.
        iteration_path: Ruta escrita en Recursos.

    Returns:
        La iteracion y sus descendientes.

    Raises:
        CapacityError: Cuando la ruta no existe.
    """
    wanted_path = normalize_path(iteration_path)
    target = next(
        (
            iteration
            for iteration in iterations
            if normalize_path(to_text(iteration.get("path"))) == wanted_path
        ),
        None,
    )

    if target is None:
        raise CapacityError(f"Iteration Path no encontrado: {iteration_path}")

    target_path = to_text(target.get("path"))
    child_prefix = f"{target_path}{PATH_SEPARATOR}"

    return [
        iteration
        for iteration in iterations
        if to_text(iteration.get("path")) == target_path
        or to_text(iteration.get("path")).startswith(child_prefix)
    ]


def select_sprint_iterations(
    iterations: Sequence[JsonObject],
    project_id: str,
) -> list[JsonObject]:
    """
    Toma las iteraciones con la nomenclatura del ID (S1, S2, CR).

    Args:
        iterations: Iteraciones en lista plana.
        project_id: ID interno del proyecto.

    Returns:
        Las iteraciones de la nomenclatura; todas si ninguna la tiene y
        el ID no trae sufijo.

    Raises:
        CapacityError: Cuando el sufijo del ID no existe en Azure o el
            proyecto tiene varias etapas con sufijo.
    """
    suffix_match = ID_SUFFIX.search(project_id.upper())
    sprint = suffix_match.group(1) if suffix_match else DEFAULT_SPRINT
    sprint_name = re.compile(rf"(?:^|_){sprint}\Z", re.IGNORECASE)
    tagged = [
        iteration
        for iteration in iterations
        if any(sprint_name.search(name) for name in split_path(iteration))
    ]

    if tagged:
        return tagged

    if suffix_match:
        raise CapacityError(
            f"No se encontraron iteraciones {sprint} para {project_id}.",
        )

    if any(
        ANY_SPRINT_NAME.search(name)
        for iteration in iterations
        for name in split_path(iteration)
    ):
        raise CapacityError(
            "Hay varias etapas con sufijo; especifica el ID _S o Iteration "
            f"Path en Recursos para {project_id}.",
        )

    return list(iterations)


def split_path(iteration: JsonObject) -> list[str]:
    """
    Separa la ruta de la iteracion en los nombres de cada nivel.

    Args:
        iteration: Iteracion en lista plana.

    Returns:
        Los nombres desde la raiz hasta la iteracion.
    """
    return to_text(iteration.get("path")).split(PATH_SEPARATOR)


def normalize_path(path: str) -> str:
    """
    Normaliza una ruta para compararla sin importar los separadores.

    Args:
        path: Ruta de la iteracion.

    Returns:
        La ruta normalizada.
    """
    return normalize_capacity_text(path.replace(PATH_SEPARATOR, " "))
