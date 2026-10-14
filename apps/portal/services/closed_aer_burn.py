"""Consulta y conserva Burn solo para proyectos finalizados de MPB."""
import math
from datetime import date
from apps.ejecutivo.services.aer_tym_summary import find_mpb_header, resolve_columns, build_summary_row
from apps.clockify.provider import build_clockify_loader
from core.sheets.factory import build_sheet_repository
from core.sheets.read_cache import SheetReadCache
from django.conf import settings
from django.core.cache import cache
from apps.ejecutivo.rpc import SUMMARY_CACHE_KEY
from django.utils import timezone


def fill_closed_burn(project_id):
    repo = build_sheet_repository()
    api = repo._service.spreadsheets().values()
    def read():
        return api.get(spreadsheetId=repo._spreadsheet_id, range="'MPB'!A:CL", valueRenderOption="UNFORMATTED_VALUE").execute().get("values", [])
    def find(values):
        header = find_mpb_header(values)
        if header is None:
            raise ValueError("No se encontraron encabezados de MPB")
        columns = resolve_columns(values[header])
        matches = []
        for index, row in enumerate(values[header + 1:], header + 2):
            item = build_summary_row(row, columns, timezone.localdate(), closed_year=2026)
            if item and item["idProyecto"].strip().casefold() == project_id.strip().casefold():
                matches.append((index, item))
        if len(matches) != 1:
            raise ValueError("El ID debe tener una fila finalizada unica en MPB")
        return columns, matches[0]
    columns, (index, item) = find(read())
    if item["burn"] is not None:
        return {"id": project_id, "burn": item["burn"], "saved": True}
    start, finish = date.fromisoformat(item["fechaInicio"]), date.fromisoformat(item["fechaFin"])
    entries = build_clockify_loader(repo).load_project(item["idProyecto"], (start, finish))
    burn = round(sum(entry.duration_hours for entry in entries), 2)
    if not math.isfinite(burn) or burn < 0:
        raise ValueError("Clockify no devolvio un consumo valido")
    # Read again so a manual Burn or changed status is preserved.
    columns, (index, current) = find(read())
    if current["burn"] is not None:
        return {"id": project_id, "burn": current["burn"], "saved": True}
    if (current["fechaInicio"], current["fechaFin"]) != (item["fechaInicio"], item["fechaFin"]):
        raise ValueError("Las fechas cambiaron; vuelve a consultar")
    number = columns["burn"] + 1
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    api.update(spreadsheetId=repo._spreadsheet_id, range=f"'MPB'!{letters}{index}", valueInputOption="RAW", body={"values": [[burn]]}).execute()
    SheetReadCache(repo._spreadsheet_id, settings.SHEETS_READ_CACHE_SECONDS).invalidate_values("MPB")
    cache.delete(SUMMARY_CACHE_KEY)
    return {"id": project_id, "burn": burn, "saved": True}
