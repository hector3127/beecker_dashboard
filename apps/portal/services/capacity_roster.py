"""Plantilla operativa mensual y metadatos, sin consultar Recursos."""

from collections import defaultdict
from typing import Any

from apps.datastore.models import EvaExtraction, EvaScopeSnapshot
from apps.ejecutivo.services.aer_tym_summary import (
    find_mpb_header,
    resolve_columns,
)
from apps.ejecutivo.services.ixb_rules import read_history_id, read_project_id
from apps.ejecutivo.services.mpb_values import read_cell
from apps.gse.exceptions import GseError
from apps.gse.services.cells import cell_at, norm, trimmed
from apps.gse.services.roster import find_band_column, read_roster_sheet
from apps.portal.constants import OPERATIONAL_ROLES
from apps.portal.services.eva_azure_source import BUSINESS_ID
from core.exceptions import DashboardError
from core.sheets import sheet_names
from core.sheets.factory import build_sheet_repository
from core.utils.text import get_flexible_value


def operations_roster(month: str) -> list[dict[str, Any]]:
    """Solo roles operativos vigentes en la banda del mes, con o sin horas."""
    sheet = read_roster_sheet(
        build_sheet_repository(), "Bandas/rol requiere Nombre y ROL."
    )
    band_col = find_band_column(sheet.headers, int(month[5:7]), month[:4])
    if band_col < 0:
        from apps.capacidad.services.capacity_base import (
            find_band_column as capacity_band,
        )
        from apps.capacidad.services.sheet_table import SheetTable

        band_col = capacity_band(
            SheetTable(headers=list(sheet.headers), rows=[], header_index=0),
            month,
        ).index
    if band_col < 0:
        raise GseError(f"Bandas/rol no tiene columna de banda para {month}.")
    id_col = (
        sheet.headers.index("id clockify")
        if "id clockify" in sheet.headers
        else -1
    )
    roles = {norm(key): label for key, label in OPERATIONAL_ROLES.items()}
    people = []
    seen = set()
    for row in sheet.data_rows:
        name = trimmed(cell_at(row, sheet.headers.index("nombre")))
        role = roles.get(norm(cell_at(row, sheet.role_column)))
        band = trimmed(cell_at(row, band_col))
        if not name or not role or norm(band) in ("", "baja", "na"):
            continue
        clockify_id = trimmed(cell_at(row, id_col))
        key = clockify_id or "name:" + norm(name)
        if key in seen:
            raise GseError(f"Persona duplicada en Bandas/rol: {name}.")
        seen.add(key)
        people.append(
            {
                "id": key,
                "clockify_id": clockify_id,
                "name": name,
                "role": role,
                "band": band,
            }
        )
    return people


def roster_match(
    people: list[dict[str, Any]], user_id: str, user_name: str
) -> dict[str, Any] | None:
    """ID prioritario; nombre normalizado solo si falta el ID en Bandas/rol."""
    exact = [
        p for p in people if p["clockify_id"] and p["clockify_id"] == user_id
    ]
    if exact:
        return exact[0]
    fallback = [
        p
        for p in people
        if not p["clockify_id"] and norm(p["name"]) == norm(user_name)
    ]
    return fallback[0] if len(fallback) == 1 else None


def project_metadata() -> dict[str, dict[str, set[str]]]:
    """Delivery y nombre del inventario Summary publicado, sin extracción."""
    run = (
        EvaExtraction.objects.filter(
            published=True, metrics__kind="summary_inventory"
        )
        .order_by("-pk")
        .first()
    )
    result: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"managers": set(), "names": set()}
    )
    for block in (
        EvaScopeSnapshot.objects.filter(source__extraction=run).select_related(
            "source"
        )
        if run
        else []
    ):
        fields = block.row.get("fields") or {}
        for key in (block.project_id, block.source.name):
            value = result[key.upper()]
            if fields.get("delivery_manager"):
                value["managers"].add(fields["delivery_manager"])
            if fields.get("project_name"):
                value["names"].add(fields["project_name"])
    reader = build_sheet_repository()
    try:
        if reader.sheet_exists("MPB"):
            values = reader.read_values("MPB")
            header = find_mpb_header(values)
            if header is not None:
                cols = resolve_columns(values[header])
                for row in values[header + 1 :]:
                    pid = (
                        str(read_cell(row, cols["project_id"]) or "")
                        .strip()
                        .upper()
                    )
                    manager = str(read_cell(row, cols["manager"]) or "").strip()
                    if pid and manager and not result[pid]["managers"]:
                        result[pid]["managers"].add(manager)
                    title = str(read_cell(row, cols["name"]) or "").strip()
                    if pid and title and not result[pid]["names"]:
                        result[pid]["names"].add(title)
        for sheet, identify in (
            (sheet_names.SHEET_PROJECTS, read_project_id),
            (sheet_names.SHEET_PROJECTS_HISTORY, read_history_id),
        ):
            if not reader.sheet_exists(sheet):
                continue
            for record in reader.read_as_objects(sheet):
                pid = identify(record).upper()
                manager = str(
                    get_flexible_value(
                        record, ["Delivery Manager", "Delivery_Manager", "DM"]
                    )
                    or ""
                ).strip()
                if pid and manager and not result[pid]["managers"]:
                    result[pid]["managers"].add(manager)
    except DashboardError:
        # El DM no confirmado permanece explícitamente pendiente.
        pass
    return result


def project_identity(
    clockify_name: str, metadata: dict[str, dict[str, set[str]]]
) -> dict[str, str]:
    """Un ID de negocio explícito; no asigna un DM por semejanza de nombre."""
    match = BUSINESS_ID.search(clockify_name)
    business_id = match.group(0).upper() if match else ""
    info = metadata.get(business_id) or {}
    return {
        "business_id": business_id,
        "manager": " / ".join(sorted(info.get("managers", [])))
        or "Sin DM confirmado",
        "project_title": " / ".join(sorted(info.get("names", [])))
        or clockify_name,
    }
