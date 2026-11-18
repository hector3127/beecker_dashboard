"""Financial project dates from the published Azure Summary inventory."""

from datetime import date
from typing import Any

from apps.datastore.models import EvaExtraction, EvaScopeSnapshot
from apps.ejecutivo.services.aer_tym_summary import (
    AER_TYM_SERVICE,
    find_mpb_header,
    resolve_columns,
)
from apps.portal.services.project_task_scope import financial_variant
from core.sheets.protocols import SheetReader
from core.utils.text import normalize_name


def project_key(project_id: str) -> str:
    """Normalize separators while preserving the scope suffix."""
    variant = financial_variant(project_id)
    return (
        f"{variant[0]}_{variant[1].lower()}"
        if variant
        else project_id.strip().casefold()
    )


def azure_scopes() -> list[dict[str, Any]]:
    """Read project scopes from the latest published Azure cut."""
    run = (
        EvaExtraction.objects.filter(
            published=True, metrics__kind="summary_inventory"
        )
        .order_by("-pk")
        .first()
    )
    return list(
        EvaScopeSnapshot.objects.filter(source__extraction=run)
        .exclude(project_id="")
        .values_list("row", flat=True)
    )


def uses_sheet_dates(project_id: str, reader: SheetReader) -> bool:
    """Keep the existing range behavior for AER and TYM."""
    base = project_key(project_id).split("_", 1)[0]
    if base.startswith(("aer.", "tym.")):
        return True
    if not reader.sheet_exists("MPB"):
        return False
    rows = reader.read_values("MPB")
    header = find_mpb_header(rows)
    if header is None:
        return False
    columns = resolve_columns(rows[header])
    pid, service = columns["project_id"], columns["service"]
    return any(
        len(row) > max(pid, service)
        and project_key(str(row[pid] or "")).split("_", 1)[0] == base
        and AER_TYM_SERVICE.match(normalize_name(str(row[service] or "")))
        for row in rows[header + 1 :]
    )


def scope_dates(row: dict[str, Any]) -> tuple[date, date] | None:
    """Resolve a scope from Summary or its own Azure iterations."""
    if set(row.get("issues", ())) & {
        "identity_mismatch",
        "scope_id_mismatch",
        "invalid_project_id",
    }:
        return None
    start, end = row.get("start"), row.get("finish")
    if not start and not end:
        start, end = row.get("iteration_start"), row.get("iteration_finish")
    if start and end and start <= end:
        return date.fromisoformat(start), date.fromisoformat(end)
    return None
