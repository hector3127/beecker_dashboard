"""Relacion entre IDs internos y Team Projects de Azure DevOps."""

from collections.abc import Sequence

from core.utils.text import extract_base_id, strip_accents, to_text

"""BKD.030.004 - Resolucion de Team Project
Equivale a _altoNivelResolverProyectoAzure(): primero el nombre exacto y
despues el ID base antes del guion bajo (AMK.008_S4 -> AMK.008).
"""


def normalize_azure_name(value: str) -> str:
    """
    Normaliza un nombre como _altoNivelNormalizar().

    Args:
        value: Nombre o ID.

    Returns:
        El texto sin acentos, en mayusculas y sin espacios externos.
    """
    return strip_accents(to_text(value)).upper().strip()


def resolve_azure_project(
    internal_id: str,
    azure_project_names: Sequence[str],
) -> str:
    """
    Busca el Team Project de Azure de un proyecto interno.

    Args:
        internal_id: ID interno del proyecto.
        azure_project_names: Proyectos de la organizacion.

    Returns:
        El nombre del Team Project, o cadena vacia si no hay coincidencia.
    """
    normalized_id = normalize_azure_name(internal_id.strip())

    for project_name in azure_project_names:
        if normalize_azure_name(project_name) == normalized_id:
            return project_name

    normalized_base = normalize_azure_name(extract_base_id(internal_id))

    for project_name in azure_project_names:
        if (
            normalize_azure_name(extract_base_id(project_name))
            == normalized_base
        ):
            return project_name

    return ""
