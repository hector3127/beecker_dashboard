"""Ficha de un proyecto que no esta en la hoja Proyectos."""

from collections.abc import Mapping, Sequence
from typing import Any

from apps.clockify.constants import SHEET_MPB
from apps.clockify.services.date_ranges import (
    normalize_project_id,
    parse_sheet_date,
)
from apps.ejecutivo.services.aer_tym_summary import (
    find_mpb_header,
    resolve_columns,
)
from apps.ejecutivo.services.mpb_values import (
    normalize_mpb,
    parse_mpb_hours,
    read_cell,
)
from core.exceptions import DashboardError
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue, SheetRow
from core.utils.text import to_text

"""Proyectos cerrados o ajenos a Proyectos pero con horas en Clockify.

La ficha se arma con MPB (inicio, fin, presupuesto, estatus, DM) y, si a MPB
le falta una fecha, con las etapas de Historico_Proyectos. Lo que no se
encuentra se avisa en `datosFaltantes` para mostrarlo en la pestana.
"""

SOURCE_MPB = "MPB"
SOURCE_HISTORY = "Historico_Proyectos"
IS_NUMBER = int | float


def is_serial(value: CellValue) -> bool:
    """True si la celda es un numero de serie de fecha."""
    return isinstance(value, IS_NUMBER) and not isinstance(value, bool)


def mpb_project_row(
    reader: SheetReader,
    project: str,
    services: Sequence[str] | None = None,
) -> SheetRow | None:
    """
    Fila tipo Proyectos armada desde MPB.

    Une las filas repetidas: inicio mas temprano, fin mas tardio y
    presupuesto sumado, porque las horas tambien abarcan todas.

    Args:
        reader: Repositorio de Sheets.
        project: ID del proyecto.
        services: Servicios aceptados; None acepta cualquiera.

    Returns:
        La fila, o None si MPB no tiene el proyecto.
    """
    try:
        if not reader.sheet_exists(SHEET_MPB):
            return None
        values = reader.read_values(SHEET_MPB)
        header = find_mpb_header(values)
        if header is None:
            return None
        columns = resolve_columns(values[header])
    except DashboardError:
        return None
    wanted = normalize_mpb(project)
    rows = [
        row
        for row in values[header + 1 :]
        if normalize_mpb(read_cell(row, columns["project_id"])) == wanted
        and (
            services is None
            or to_text(read_cell(row, columns["service"])).strip().upper()
            in services
        )
    ]
    if not rows:
        return None

    def serials(column: str) -> list[CellValue]:
        return [
            cell
            for cell in (read_cell(row, columns[column]) for row in rows)
            if is_serial(cell)
        ]

    starts, ends = serials("start"), serials("end")
    latest = max(rows, key=lambda row: start_serial(row, columns))
    return {
        "ID_Proyecto": project,
        "Nombre": read_cell(latest, columns["name"]),
        "Cliente": read_cell(latest, columns["client"]),
        "Servicio": to_text(read_cell(latest, columns["service"])).strip(),
        "Delivery Manager": read_cell(latest, columns["manager"]),
        "Estado": to_text(read_cell(latest, columns["status"])).strip(),
        "Budget_Hrs": sum(
            parse_mpb_hours(read_cell(row, columns["budget"])) for row in rows
        ),
        "Fecha_Inicio": min(starts) if starts else "",
        "Fecha_Fin_Estimada": max(ends) if ends else "",
        "_fuente": SOURCE_MPB,
    }


def start_serial(row: Sequence[CellValue], columns: Mapping[str, int]) -> float:
    """Inicio de una fila de MPB para elegir la mas reciente."""
    start = read_cell(row, columns["start"])
    return float(start) if is_serial(start) else 0.0


def history_dates(
    history_rows: Sequence[SheetRow], project: str
) -> tuple[Any, Any]:
    """Inicio mas temprano y fin mas tardio de las etapas del historico."""
    wanted = normalize_project_id(project)
    starts, ends = [], []
    for row in history_rows:
        if normalize_project_id(to_text(row.get("Project ID"))) != wanted:
            continue
        start = parse_sheet_date(row.get("Start", ""))
        end = parse_sheet_date(row.get("Finish", ""))
        if start:
            starts.append(start)
        if end:
            ends.append(end)
    return (min(starts) if starts else "", max(ends) if ends else "")


def fallback_project_row(
    reader: SheetReader,
    project: str,
    history_rows: Sequence[SheetRow],
    services: Sequence[str] | None = None,
) -> SheetRow | None:
    """
    Ficha del proyecto desde MPB y, para las fechas, desde el historico.

    Returns:
        La fila, o None si ni MPB ni el historico conocen el proyecto.
    """
    row = mpb_project_row(reader, project, services)
    start, end = history_dates(history_rows, project)
    if row is None:
        if not start and not end:
            return None
        return {
            "ID_Proyecto": project,
            "Nombre": project,
            "Fecha_Inicio": start,
            "Fecha_Fin_Estimada": end,
            "_fuente": SOURCE_HISTORY,
        }
    if not row["Fecha_Inicio"] and start:
        row["Fecha_Inicio"] = start
    if not row["Fecha_Fin_Estimada"] and end:
        row["Fecha_Fin_Estimada"] = end
    return row


def missing_data(row: Mapping[str, Any]) -> list[str]:
    """Avisos de los datos que faltan para calcular fechas y avance."""
    notes = []
    source = row.get("_fuente")
    if source:
        notes.append(
            f"El proyecto no está en la hoja Proyectos; se muestra con "
            f"datos de {source}."
        )
    if not row.get("Fecha_Inicio"):
        notes.append(
            "Falta la fecha de inicio (Fecha_Inicio en Proyectos, INICIO en "
            "MPB o Start en Historico_Proyectos): no se calcula el tiempo "
            "transcurrido."
        )
    if not row.get("Fecha_Fin_Estimada"):
        notes.append(
            "Falta la fecha de fin (Fecha_Fin_Estimada en Proyectos, FIN en "
            "MPB o Finish en Historico_Proyectos): no se calcula el tiempo "
            "transcurrido ni los días restantes."
        )
    if not row.get("Budget_Hrs"):
        notes.append("Falta el presupuesto de horas (Budget_Hrs / HORAS).")
    return notes
