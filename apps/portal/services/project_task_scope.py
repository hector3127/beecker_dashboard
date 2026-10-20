"""Keep base projects and S# task variants mutually exclusive."""

import re
from dataclasses import replace
from typing import Any

SUFFIX = re.compile(r"^(.*?)[_\s-]+(S\d+)$", re.I)
TOKEN = re.compile(r"(?<![A-Z0-9])(S\d+)(?![A-Z0-9])", re.I)


def variant(project_id: Any) -> Any:
    """Return the base ID and S# suffix, when present."""
    match = SUFFIX.fullmatch(project_id.strip())
    return (
        (match.group(1).casefold(), match.group(2).upper()) if match else None
    )


def task_tokens(name: Any) -> Any:
    """Extract complete S# tokens without confusing S4 with S40."""
    return {token.upper() for token in TOKEN.findall(name or "")}


def scope_entries(
    pid: Any, ids: Any, entries: Any, loader: Any, lookup: Any
) -> Any:
    """Partition task variants before aggregating financial costs."""
    selected = financial_variant(pid)
    excluded = {
        item[1]
        for candidate in ids
        if (item := financial_variant(candidate))
        and item[0] == pid.strip().casefold()
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
        return [
            e
            for e in entries
            if financial_task_tokens(e.task_name) == {selected[1]}
            or (
                selected[1].startswith("CR")
                and not e.task_id
                and not e.task_name.strip()
            )
        ]
    claimed_taskless: set[Any] = set()
    if any(not e.task_id and not e.task_name.strip() for e in entries):
        for candidate in ids:
            child = financial_variant(candidate)
            if (
                child
                and child[0] == pid.strip().casefold()
                and child[1].startswith("CR")
            ):
                claimed_taskless.update(
                    e.entry_id
                    for e in loader.load_project(candidate)
                    if not e.task_id and not e.task_name.strip()
                )
    return [
        e
        for e in entries
        if not (financial_task_tokens(e.task_name) & excluded)
        and e.entry_id not in claimed_taskless
    ]


def financial_variant(project_id: Any) -> Any:
    """Financial identity: unregistered sprint/CR variants join the base."""
    match = re.fullmatch(
        r"(.*?)[_\s|/-]+(S\d+|CR\d*)", project_id.strip(), re.I
    )
    return (
        (match.group(1).strip().casefold(), match.group(2).upper())
        if match
        else None
    )


def financial_task_tokens(name: Any) -> Any:
    """Recognize S# and CR# as complete task tokens."""
    return {
        token.upper()
        for token in re.findall(
            r"(?<![A-Z0-9])(S\d+|CR\d*)(?![A-Z0-9])", name or "", re.I
        )
    }
