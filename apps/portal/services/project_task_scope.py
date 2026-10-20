"""Keep base projects and S# task variants mutually exclusive."""

import re
from dataclasses import replace

SUFFIX = re.compile(r"^(.*?)[_\s-]+(S\d+)$", re.I)
TOKEN = re.compile(r"(?<![A-Z0-9])(S\d+)(?![A-Z0-9])", re.I)


def variant(project_id):
    """Return the base ID and S# suffix, when present."""
    match = SUFFIX.fullmatch(project_id.strip())
    return (
        (match.group(1).casefold(), match.group(2).upper()) if match else None
    )


def task_tokens(name):
    """Extract complete S# tokens without confusing S4 with S40."""
    return {token.upper() for token in TOKEN.findall(name or "")}


def scope_entries(pid, ids, entries, loader, lookup):
    """Partition task variants before aggregating financial costs."""
    selected = variant(pid)
    excluded = {
        item[1]
        for candidate in ids
        if (item := variant(candidate)) and item[0] == pid.strip().casefold()
    }
    if not selected and not excluded:
        return entries
    entries = list(entries)
    if any(e.task_id and not e.task_name for e in entries):
        project = loader.find_clockify_project(lookup)
        if project is None:
            raise ValueError(
                "No se pudo resolver el proyecto para separar las tareas S#"
            )
        names = {
            str(task.get("id")): str(task.get("name") or "")
            for task in loader.load_project_tasks(project.project_id)
        }
        entries = [
            replace(e, task_name=names.get(e.task_id, ""))
            if e.task_id and not e.task_name
            else e
            for e in entries
        ]
        if any(e.task_id and not e.task_name for e in entries):
            raise ValueError(
                "Falta identificar tareas de Clockify; "
                "no se pueden separar las horas S# sin duplicarlas"
            )
    if selected:
        return [e for e in entries if task_tokens(e.task_name) == {selected[1]}]
    return [e for e in entries if not (task_tokens(e.task_name) & excluded)]


def financial_variant(project_id):
    """Financial identity: unregistered sprint/CR variants belong to the base."""
    match = re.fullmatch(r"(.*?)[_\s|/-]+(S\d+|CR\d*)", project_id.strip(), re.I)
    return (match.group(1).strip().casefold(), match.group(2).upper()) if match else None
