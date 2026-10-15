"""Catalogo de KPIs desde MPB, Historico_Proyectos A:I y Budget (Hrs) en J."""

from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Any

from apps.dashboard.schemas.records import ProjectRecord
from apps.ejecutivo.services.aer_tym_summary import (
    AER_TYM_SERVICE,
    find_mpb_header,
    resolve_columns,
)
from apps.ejecutivo.services.ixb_history import (
    HistoryPeriod,
    resolve_history_period,
)
from apps.ejecutivo.services.ixb_rules import (
    CLOSED_PROJECT_STATES,
    HISTORY_FINISH_COLUMNS,
    HISTORY_START_COLUMNS,
    read_history_date,
    read_history_id,
    read_history_status,
)
from apps.ejecutivo.services.mpb_values import (
    normalize_mpb,
    parse_mpb_date,
    parse_mpb_hours,
    read_cell,
)
from core.exceptions import SheetColumnNotFoundError
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue, SheetRow
from core.utils.dates import to_datetime
from core.utils.text import get_flexible_value, to_text


def value(row: SheetRow, *names: str) -> CellValue:
    """Lee un campo del bloque al que pertenece la fila."""
    return get_flexible_value(row, list(names))


def blocks(
    values: Sequence[Sequence[CellValue]],
) -> tuple[list[SheetRow], list[SheetRow]]:
    """Separa los bloques sin mezclar IDs de encabezados duplicados."""
    if not values:
        return [], []
    headers = [to_text(c).strip() for c in values[0]]
    ids = [
        i
        for i, h in enumerate(headers)
        if normalize_mpb(h).replace(" ", "").replace("_", "")
        in {"projectid", "idproyecto"}
    ]
    split = max(0, ids[1] - 2) if len(ids) > 1 else len(headers)
    tables = []
    for start, end in ((0, split), (split, len(headers))):
        rows = []
        for record in values[1:]:
            row = {
                headers[i]: record[i] if i < len(record) else ""
                for i in range(start, end)
                if headers[i]
            }
            if read_history_id(row):
                rows.append(row)
        tables.append(rows)
    return tables[0], tables[1]


def operational_period(
    rows: Sequence[SheetRow],
    project_id: str,
    cutoff: date,
) -> HistoryPeriod:
    """Usa el bloque desde Discovery OP hasta su cierre, sin etapas EST."""
    first = next(
        (
            i
            for i, row in enumerate(rows)
            if read_history_status(row) == "DISCOVERY OP"
        ),
        None,
    )
    operative = list(rows[first:]) if first is not None else list(rows)
    operative = [
        r for r in operative if not read_history_status(r).endswith(" EST")
    ]
    closing = None
    for i, row in enumerate(operative):
        if read_history_status(row) in CLOSED_PROJECT_STATES:
            closing = read_history_date(
                row, HISTORY_FINISH_COLUMNS
            ) or read_history_date(
                row,
                HISTORY_START_COLUMNS,
            )
            operative = operative[: i + 1]
            break
    period = resolve_history_period(operative, project_id, cutoff)
    if period.active and closing is not None:
        period.finish = datetime.combine(closing, datetime.min.time())
    return period


@dataclass
class KpiSources:
    """Fuentes por ID y resolucion del proyecto en cada fecha de corte."""

    mpb: dict[str, list[ProjectRecord]]
    events: dict[str, list[SheetRow]]
    metadata: dict[str, SheetRow]
    managers: dict[str, str]
    today: date

    def at(self, cutoff: date) -> list[ProjectRecord]:
        """Obtiene contratos MPB y etapas vigentes del historico en el corte."""
        result = []
        for versions in self.mpb.values():
            candidates = [
                p
                for p in versions
                if p.start_date
                and p.start_date.date() <= cutoff
                and p.end_date
                and cutoff <= p.end_date.date()
            ]
            if not candidates:
                continue
            record = max(candidates, key=lambda p: p.start_date or datetime.min)
            state = normalize_mpb(record.status)
            if state in {"suspendido", "suspended", "en pausa"}:
                continue
            if cutoff >= self.today and state in {
                "completed",
                "completado",
                "finalizado",
                "cancelado",
                "cancelled",
                "canceled",
                "cerrado",
                "closed",
            }:
                continue
            result.append(replace(record, status="Development"))
        for pid, rows in self.events.items():
            meta = self.metadata.get(pid.casefold(), {})
            service = to_text(
                value(meta, "Service", "Servicio")
                or value(rows[0], "Service", "Servicio")
            ).strip()
            if (
                AER_TYM_SERVICE.fullmatch(normalize_mpb(service))
                or pid.casefold() in self.mpb
            ):
                continue
            period = operational_period(rows, pid, cutoff)
            if not period.active or period.status == "Suspendido":
                continue
            result.append(
                ProjectRecord(
                    project_id=pid,
                    display_name=value(meta, "Project Name", "Nombre")
                    or value(rows[0], "Project Name", "Nombre")
                    or pid,
                    client=value(meta, "Client", "Account", "Cliente")
                    or value(rows[0], "Account", "Client", "Cliente"),
                    status="Development"
                    if period.status == "Discovery"
                    else period.status,
                    service=service,
                    budget_hours=parse_mpb_hours(
                        value(meta, "Budget", "Budget_Hrs", "Presupuesto")
                    ),
                    start_date=period.start,
                    end_date=period.finish,
                )
            )
        return result


def load_kpi_sources(reader: SheetReader, today: date) -> KpiSources:
    """Lee AER/T&M de MPB y otros servicios del historico sin usar Proyectos."""
    mpb_values = reader.read_values("MPB")
    header = find_mpb_header(mpb_values)
    if header is None:
        raise SheetColumnNotFoundError(
            "MPB no tiene CLIENTE, SERVICE y ESTATUS para los KPIs."
        )
    cols = resolve_columns(mpb_values[header])
    mpb: dict[str, list[ProjectRecord]] = defaultdict(list)
    managers: dict[str, str] = {}
    for mpb_row in mpb_values[header + 1 :]:

        def cell(key: str, record: Sequence[CellValue] = mpb_row) -> CellValue:
            """Lee una columna logica de este contrato MPB."""
            return read_cell(record, cols[key])

        service = to_text(cell("service")).strip()
        pid = to_text(cell("project_id")).strip()
        if not pid or not AER_TYM_SERVICE.fullmatch(normalize_mpb(service)):
            continue
        mpb[pid.casefold()].append(
            ProjectRecord(
                pid,
                cell("name") or pid,
                cell("client"),
                cell("status"),
                service,
                parse_mpb_hours(cell("budget")),
                to_datetime(parse_mpb_date(cell("start"))),
                to_datetime(parse_mpb_date(cell("end"))),
            )
        )
        managers[pid] = to_text(cell("manager")).strip()
    history_values = [
        list(row[:10]) for row in reader.read_values("Historico_Proyectos")
    ]
    if history_values and len(history_values[0]) > 9:
        budget_header = normalize_mpb(history_values[0][9]).replace(" ", "")
        history_values[0][9] = (
            "Budget_Hrs" if budget_header == "budget(hrs)" else ""
        )
    left, _ = blocks(history_values)
    events: dict[str, list[SheetRow]] = defaultdict(list)
    metadata: dict[str, SheetRow] = {}
    for row in left:
        events[read_history_id(row)].append(row)
    # Datos del proyecto y DM de A:I; J aporta solo el presupuesto por ID.
    for pid, rows in events.items():
        if pid.casefold() not in metadata:
            budget = next(
                (
                    row["Budget_Hrs"]
                    for row in rows
                    if row.get("Budget_Hrs") not in (None, "")
                ),
                "",
            )
            metadata[pid.casefold()] = {**rows[0], "Budget_Hrs": budget}
        managers.setdefault(
            pid,
            to_text(
                value(metadata[pid.casefold()], "Delivery Manager", "DM")
                or value(rows[0], "Delivery Manager", "DM")
            ).strip(),
        )
    return KpiSources(dict(mpb), dict(events), metadata, managers, today)


class KpiSheetReader:
    """Adapta el catalogo de Clockify a IDs derivados de las fuentes de KPIs."""

    def __init__(
        self, reader: SheetReader, projects: Sequence[ProjectRecord]
    ) -> None:
        self.reader = reader
        self.rows = [
            {
                "ID_Proyecto": p.project_id,
                "Nombre": p.display_name,
                "Servicio": p.service,
                "Fecha_Inicio": p.start_date.isoformat()
                if p.start_date
                else "",
                "Fecha_Fin_Estimada": p.end_date.isoformat()
                if p.end_date
                else "",
            }
            for p in projects
        ]

    def read_as_objects(self, name: str) -> list[SheetRow]:
        """Entrega un catalogo interno; nunca consulta la hoja Proyectos."""
        return (
            self.rows
            if name == "Proyectos"
            else self.reader.read_as_objects(name)
        )

    def read_values(self, name: str) -> list[list[CellValue]]:
        """Entrega IDs y datos exclusivamente de MPB y del historico."""
        if name != "Proyectos":
            return self.reader.read_values(name)
        headers = [
            "ID_Proyecto",
            "Nombre",
            "Servicio",
            "Fecha_Inicio",
            "Fecha_Fin_Estimada",
        ]
        values: list[list[CellValue]] = [list(headers)]
        values.extend([[row[h] for h in headers] for row in self.rows])
        return values

    def sheet_exists(self, name: str) -> bool:
        """Reconoce el catalogo interno para el emparejamiento de Clockify."""
        return name == "Proyectos" or self.reader.sheet_exists(name)

    def prefetch(self, names: Iterable[str]) -> None:
        """Precarga fuentes reales y excluye Proyectos."""
        self.reader.prefetch([n for n in names if n != "Proyectos"])

    def read_previews(
        self,
        names: Sequence[str],
        row_count: int,
        column_count: int,
    ) -> dict[str, list[list[CellValue]]]:
        """Sirve vistas previas del catalogo interno sin leer Proyectos."""
        result = self.reader.read_previews(
            [n for n in names if n != "Proyectos"],
            row_count,
            column_count,
        )
        if "Proyectos" in names:
            result["Proyectos"] = [
                row[:column_count]
                for row in self.read_values("Proyectos")[:row_count]
            ]
        return result

    def __getattr__(self, name: str) -> Any:
        """Reutiliza operaciones que no consultan el catalogo de proyectos."""
        return getattr(self.reader, name)
