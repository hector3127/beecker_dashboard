"""Relacion entre los IDs internos y los proyectos de Clockify."""

import re
from collections.abc import Mapping, Sequence

from apps.clockify.services.clockify_client import ClockifyProject
from core.utils.text import extract_base_id, strip_accents, to_text

"""BKD.020.006 - Resolucion de proyectos de Clockify
Equivale a _resolverProyectoClockify(): primero el vinculo manual,
despues el nombre exacto, despues el ID base (AMK.008_S4 -> AMK.008) y
por ultimo un nombre que contenga el ID, solo si la coincidencia es unica.
En modo estricto (idCompletoEstricto, usado por Capacidad instalada) se
ignora el vinculo manual y el ID base: nombre exacto o un unico nombre
que empiece con el ID.
"""


def normalize_clockify_name(value: str) -> str:
    """
    Normaliza un nombre como _normalizarNombreParaMatchClockify().

    Args:
        value: Nombre o ID.

    Returns:
        Texto sin acentos, en minusculas y con espacios simples.
    """
    lowered_text = strip_accents(to_text(value)).lower()

    return re.sub(r"\s+", " ", lowered_text).strip()


def resolve_clockify_project(
    internal_id: str,
    projects: Sequence[ClockifyProject],
    linked_project_ids: Mapping[str, str],
    strict: bool = False,
) -> ClockifyProject | None:
    """
    Busca el proyecto de Clockify que corresponde a un ID interno.

    Args:
        internal_id: ID del proyecto en el panel.
        projects: Proyectos del workspace de Clockify.
        linked_project_ids: ID interno normalizado -> ID de Clockify.
        strict: Usa la coincidencia estricta de Capacidad instalada.

    Returns:
        El proyecto encontrado, o None si no hay coincidencia unica.
    """
    clean_id = internal_id.strip()
    base_id = extract_base_id(clean_id)
    linked_id = linked_project_ids.get(
        normalize_link_key(clean_id),
    ) or linked_project_ids.get(normalize_link_key(base_id))

    if linked_id and not strict:
        return next(
            (
                project
                for project in projects
                if project.project_id == linked_id
            ),
            None,
        )

    normalized_id = normalize_clockify_name(clean_id)
    exact_match = next(
        (
            project
            for project in projects
            if normalize_clockify_name(project.name) == normalized_id
        ),
        None,
    )

    if exact_match is not None:
        return exact_match

    if strict:
        return find_unique_prefix_match(normalized_id, projects)

    normalized_base = normalize_clockify_name(base_id)
    base_candidates = [
        project
        for project in projects
        if normalize_clockify_name(extract_base_id(project.name))
        == normalized_base
    ]
    exact_base = next(
        (
            project
            for project in base_candidates
            if normalize_clockify_name(project.name) == normalized_base
        ),
        None,
    )

    if exact_base is not None:
        return exact_base

    contains_id = re.compile(
        rf"(^|[^a-z0-9]){re.escape(normalized_base)}(?=$|[^a-z0-9])",
    )
    options_by_id = {
        project.project_id: project
        for project in [
            *base_candidates,
            *(
                project
                for project in projects
                if contains_id.search(normalize_clockify_name(project.name))
            ),
        ]
    }

    if len(options_by_id) == 1:
        return next(iter(options_by_id.values()))

    return None


def find_unique_prefix_match(
    normalized_id: str,
    projects: Sequence[ClockifyProject],
) -> ClockifyProject | None:
    """
    Busca un unico proyecto cuyo nombre empiece con el ID completo.

    El ID debe ir seguido del final, un espacio o un guion
    ("GPO.007 - MultiProfile").

    Args:
        normalized_id: ID normalizado.
        projects: Proyectos del workspace de Clockify.

    Returns:
        El proyecto si la coincidencia es unica; si no, None.
    """
    prefix_pattern = re.compile(
        rf"^{re.escape(normalized_id)}(?=$|\s|\s*-\s*)",
        re.IGNORECASE,
    )
    options = [
        project
        for project in projects
        if prefix_pattern.search(normalize_clockify_name(project.name))
    ]

    return options[0] if len(options) == 1 else None


def normalize_link_key(project_id: str) -> str:
    """
    Normaliza un ID interno para buscarlo en los vinculos manuales.

    Args:
        project_id: ID interno.

    Returns:
        El ID en mayusculas y sin espacios.
    """
    return re.sub(r"\s+", "", project_id.strip().upper())
