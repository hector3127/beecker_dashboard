"""Relacion entre el proyecto de Azure del Daily y la hoja Proyectos."""

import re
from collections.abc import Sequence
from typing import Any

from core.utils.cell_types import SheetRow
from core.utils.text import extract_base_id, strip_accents, to_text

"""BKD.070.009 - Proyectos del Daily
Equivale a resolverIdProyectoDesdeAzure() y listarSprintsProyecto().
"""

JsonObject = dict[str, Any]

CLOSED_STATES = ("Cerrado", "Cancelado")
TOKEN_PATTERN = re.compile(r"\d+|\D")


def resolve_internal_project(
    azure_project: object,
    project_rows: Sequence[SheetRow],
) -> str | None:
    """
    Busca el ID interno del proyecto de Azure.

    Primero el ID exacto; despues el mismo ID base, prefiriendo uno que
    no este Cerrado ni Cancelado.

    Args:
        azure_project: Nombre del Team Project.
        project_rows: Filas de la hoja Proyectos.

    Returns:
        El ID interno, o None.
    """
    name = str(azure_project).strip() if azure_project else ""

    if not name:
        return None

    exact = next(
        (row for row in project_rows if row.get("ID_Proyecto") == name),
        None,
    )

    if exact is not None:
        return to_text(exact.get("ID_Proyecto"))

    base_id = extract_base_id(name)
    candidates = [
        row
        for row in project_rows
        if extract_base_id(to_text(row.get("ID_Proyecto"))) == base_id
    ]

    if not candidates:
        return None

    active = next(
        (row for row in candidates if row.get("Estado") not in CLOSED_STATES),
        candidates[0],
    )

    return to_text(active.get("ID_Proyecto"))


def natural_key(text: str) -> list[tuple[int, Any]]:
    """
    Orden como localeCompare('es', {numeric: true, sensitivity: 'base'}).

    Args:
        text: ID del proyecto.

    Returns:
        La llave: signos < numeros < letras, sin mayusculas ni acentos.
    """
    key: list[tuple[int, Any]] = []

    for token in TOKEN_PATTERN.findall(strip_accents(text).lower()):
        if token.isdigit():
            key.append((1, int(token)))
        elif token.isalpha():
            key.append((2, token))
        else:
            key.append((0, token))

    return key


def list_project_sprints(
    azure_project: object,
    project_rows: Sequence[SheetRow],
) -> JsonObject:
    """
    IDs internos que comparten el ID base del proyecto de Azure.

    Args:
        azure_project: Nombre del Team Project.
        project_rows: Filas de la hoja Proyectos.

    Returns:
        {"ok": True, "sprints": [...]}.
    """
    name = str(azure_project).strip() if azure_project else ""

    if not name:
        return {"ok": True, "sprints": []}

    base_id = extract_base_id(name)
    sprints = [
        {
            "idProyecto": row.get("ID_Proyecto"),
            "nombre": row.get("Nombre") or row.get("ID_Proyecto"),
            "estado": row.get("Estado") or "",
        }
        for row in project_rows
        if extract_base_id(to_text(row.get("ID_Proyecto"))) == base_id
    ]
    sprints.sort(key=lambda sprint: natural_key(to_text(sprint["idProyecto"])))

    return {"ok": True, "sprints": sprints}
