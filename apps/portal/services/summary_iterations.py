"""Exact iteration blocks and calendar stages, separate from business state."""

import re
from datetime import date
from typing import Any

STAGES = {
    "discovery": "Discovery",
    "development": "Development",
    "deployment": "Deployment",
    "suspendido": "Suspendido",
    "suspended": "Suspendido",
}
HEADER = re.compile(
    r"^(general|discovery|development|deployment|suspendido|suspended)(?:[_\s-]+(CR\d*(?:_S\d+)?|S\d+))?$",
    re.I,
)


def iteration_blocks(tree: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Read exact scope ancestry; never fold CR2 into CR or S10 into S1."""
    blocks: dict[str, list[dict[str, Any]]] = {}

    def walk(node: dict[str, Any], inherited: str = "BASE") -> None:
        match = HEADER.fullmatch(str(node.get("name", "")))
        scope = (match[2] or inherited).upper() if match else inherited
        if match:
            blocks.setdefault(scope, [])
            if match[1].lower() in STAGES:
                attrs = node.get("attributes") or {}
                blocks[scope].append(
                    {
                        "stage": STAGES[match[1].lower()],
                        "identifier": node.get("identifier"),
                        "id": node.get("id"),
                        "path": node.get("path"),
                        "start": str(attrs.get("startDate") or "")[:10],
                        "finish": str(attrs.get("finishDate") or "")[:10],
                    }
                )
        for child in node.get("children") or []:
            walk(child, scope)

    walk(tree)
    return blocks


def calendar_fields(
    stages: list[dict[str, Any]], observed: date
) -> dict[str, Any]:
    """Use the latest valid stage finish, retaining incomplete evidence."""
    issues = []
    valid = []
    finishes = []
    discovery_starts = []
    for stage in stages:
        if stage["stage"] == "Suspendido":
            continue
        dates = {}
        for key in ("start", "finish"):
            try:
                dates[key] = date.fromisoformat(stage[key])
            except ValueError:
                issues.append(f"iteration_invalid_{key}:{stage['stage']}")
        if (
            stage["start"]
            and stage["finish"]
            and stage["start"] > stage["finish"]
        ):
            issues.append("iteration_inverted_dates")
            continue
        if "finish" in dates:
            finishes.append(dates["finish"].isoformat())
        if stage["stage"] == "Discovery" and "start" in dates:
            discovery_starts.append(dates["start"].isoformat())
        if len(dates) == 2:
            valid.append(stage)
    start = discovery_starts[0] if len(discovery_starts) == 1 else None
    finish = max(finishes) if finishes else None
    active = [
        s["stage"]
        for s in valid
        if s["start"] <= observed.isoformat() <= s["finish"]
    ]
    label = (
        " · ".join(dict.fromkeys(active))
        if active
        else "Fuera de rango programado"
    )
    if not valid:
        label = "Pendiente"
    for suspension in (s for s in stages if s["stage"] == "Suspendido"):
        try:
            start_s = date.fromisoformat(suspension["start"])
            end_s = (
                date.fromisoformat(suspension["finish"])
                if suspension.get("finish")
                else date.max
            )
        except ValueError:
            continue
        if start_s <= observed <= end_s:
            label = "Suspendido"
    return {
        "iteration_start": start,
        "iteration_finish": finish,
        "calendar_stage": label,
        "stages": stages,
        "iteration_issues": issues,
    }
