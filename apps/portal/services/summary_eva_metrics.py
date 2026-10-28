"""Persist provider evidence and project EVA fields without page-time IO."""

import re
from datetime import date
from typing import Any

from apps.azure_devops.services.azure_client import flatten_iterations
from apps.portal.services.eva_native_rows import (
    assign_hours,
    build_row,
    scope_tokens,
)
from apps.portal.services.eva_native_sync import _clockify


def metric_rows(
    rows: list[dict[str, Any]],
    items: list[dict[str, Any]],
    tree: dict[str, Any],
    cut: date,
) -> list[dict[str, Any]]:
    """Adapt identities and iteration ranges to the existing EVA engine."""
    iterations: list[dict[str, Any]] = []
    flatten_iterations(tree, "", iterations)
    result = []
    counts = {
        r["scope"]: sum(x["scope"] == r["scope"] for x in rows) for r in rows
    }
    for row in rows:
        candidate = {
            **row,
            "start": row.get("iteration_start"),
            "finish": row.get("iteration_finish"),
        }
        scope = row["scope"] if counts[row["scope"]] == 1 else ""
        own_items = items
        engine_scope = scope
        alias = row.get("summary_scope", scope)
        if scope and scope != "BASE" and alias != scope:
            own_items = []
            for item in items:
                fields = item.get("fields") or {}
                path = str(fields.get("System.IterationPath", ""))
                if scope_tokens(path) == {alias}:
                    path = re.sub(
                        rf"(?<![A-Z0-9]){re.escape(alias)}(?![A-Z0-9])",
                        scope,
                        path,
                        flags=re.I,
                    )
                    own_items.append(
                        {
                            **item,
                            "fields": {**fields, "System.IterationPath": path},
                        }
                    )
                else:
                    own_items.append(item)
        if scope == "BASE":
            # Isolate unscoped work items from explicitly named siblings.
            engine_scope = "S0"
            own_items = []
            for item in items:
                fields = item.get("fields") or {}
                path = str(fields.get("System.IterationPath", ""))
                if not scope_tokens(path):
                    own_items.append(
                        {
                            **item,
                            "fields": {
                                **fields,
                                "System.IterationPath": f"S0\\{path}",
                            },
                        }
                    )
        projected = build_row(
            candidate, engine_scope, own_items, iterations, cut
        )
        projected["scope"] = scope
        projected["summary_scope"] = row.get("summary_scope", row["scope"])
        projected["scope_aliases"] = list(
            {scope, row.get("summary_scope", scope)}
        )
        projected["business_base"] = (
            row["azure_project"].split("_", 1)[0].upper()
        )
        # A successful complete WI transport proves zero counts even if no
        # General Epic exists. Unknown/ambiguous identities remain pending.
        projected["azure_pending"] = not scope or not row.get("stages")
        result.append(projected)
    return result


def enrich(
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    items: list[dict[str, Any]],
    azure_ok: bool,
    context: Any,
    cut: date,
) -> dict[str, Any]:
    """Extract Clockify and return immutable evidence plus projected values."""
    projected = metric_rows(rows, items, summary.get("iteration_tree", {}), cut)
    data = {"rows": projected}
    if context is not None:
        projects, workspace, months = context
        data = _clockify(
            data, projects, workspace, months, cut, include_all_scopes=True
        )
    for row, metric in zip(rows, projected, strict=True):
        if not azure_ok:
            metric["azure_pending"] = True
        row["eva_metrics"] = metric
        row["metrics_observed_date"] = cut.isoformat()
    return {
        "work_items": items,
        "azure_ok": azure_ok,
        "clockify": data.get("clockify_evidence", {}),
        "clockify_requests": data.get("clockify_requests", 0),
        "clockify_failures": data.get("clockify_failures", []),
        "clockify_available": context is not None,
        "clockify_dedicated": {
            r["scope"]: r.get("clockify_dedicated_scope", False)
            for r in projected
        },
    }


def at_cut(
    rows: list[dict[str, Any]], evidence: dict[str, Any], cut: date
) -> list[dict[str, Any]]:
    """Recalculate historical hours from evidence, keeping states observed."""
    projected = [dict(r.get("eva_metrics") or {}) for r in rows]
    for metric in projected:
        if metric:
            metric.update(
                burn=None,
                etc=None,
                avance=None,
                hoursDeviation=None,
                hours_pending=True,
            )
    providers = {r.get("clockify_project_id") for r in projected if r}
    for provider in providers - {None}:
        if cut.isoformat() > evidence.get("observed_date", ""):
            continue
        if provider not in evidence.get("clockify", {}):
            continue
        selected = [
            r for r in projected if r.get("clockify_project_id") == provider
        ]
        siblings = [
            dict(r)
            for r in projected
            if r
            and r not in selected
            and not all(s.get("clockify_dedicated_scope") for s in selected)
        ]
        assign_hours(selected + siblings, evidence["clockify"][provider], cut)
    for row, metric in zip(rows, projected, strict=True):
        if row.get("metrics_observed_date") != cut.isoformat():
            metric["azure_pending"] = True
            row["azure_unavailable_label"] = (
                "Sin histórico"
                if row.get("metrics_observed_date", "") > cut.isoformat()
                else "Sin observación"
            )
            row["azure_unavailable_reason"] = (
                "No hay una observación de tareas y riesgos "
                "guardada para esta fecha."
            )
        elif metric.get("azure_pending", True):
            row["azure_unavailable_label"] = "Sin datos"
            row["azure_unavailable_reason"] = (
                "La extracción o la relación del bloque con Azure "
                "no está completa."
            )
        row["eva_metrics"] = metric
    return rows
