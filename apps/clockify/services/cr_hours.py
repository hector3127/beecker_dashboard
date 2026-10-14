"""Identificadores y tareas de CR para proyectos compartidos en Clockify."""

import re

CR_SUFFIX = re.compile(r"[\s_|-]+(CR\d*)$", re.IGNORECASE)
CR_TOKEN = re.compile(r"(?<![A-Z0-9])(CR\d*)(?![A-Z0-9])", re.IGNORECASE)


def cr_nomenclature(project_id: str) -> str:
    """Obtiene CR o CR# del sufijo completo del identificador."""
    match = CR_SUFFIX.search(project_id.strip())
    return match.group(1).upper() if match else ""


def canonical_cr_id(project_id: str) -> str:
    """Unifica separadores de CR sin eliminar su numero o identidad."""
    return CR_SUFFIX.sub(
        lambda match: "_" + match.group(1).upper(), project_id.strip()
    )


def matches_cr_task(task_name: str, nomenclature: str) -> bool:
    """Exige la tarea CR exacta; excluye otras variantes y tareas sin CR."""
    tokens = CR_TOKEN.findall(task_name.upper())
    return bool(tokens) and all(token == nomenclature for token in tokens)
