"""Rango de fechas de cada proyecto para consultar Clockify."""

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date

from apps.clockify.constants import (
    HEADER_SEARCH_ROWS,
    HISTORY_COLUMN_COUNT,
    MPB_COLUMN_COUNT,
    MPB_END_FALLBACK_INDEX,
    MPB_PROJECT_PREFIXES,
    MPB_SERVICES,
    SHEET_MPB,
)
from apps.clockify.services.cr_hours import canonical_cr_id, cr_nomenclature
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue
from core.utils.dates import to_datetime
from core.utils.text import strip_accents, to_text

"""BKD.020.005 - Rangos de fechas por proyecto
Equivale a _obtenerRangoDiscoveryDeployment(), _clockifyRangoMPB_() y
_clockifyRangoHistoricoAI_():
- AER y TYM usan INICIO y FIN de la hoja MPB.
- IXB, RaaS y SaaS usan el inicio de Discovery y el fin de Deployment
  de Historico_Proyectos (columnas A:I).
"""

SHORT_DAY_MONTH_YEAR = re.compile(r"^(\d{1,2})/(\d{1,2})/(\d{2}|\d{4})$")

TWO_DIGIT_YEAR_LENGTH = 2

STAGE_DISCOVERY = "discovery"
STAGE_DEPLOYMENT = "deployment"

RANK_REAL = 3
RANK_OPERATION = 2
RANK_ESTIMATED = 1
RANK_OTHER = 0
RANK_NONE = -1


@dataclass(frozen=True, slots=True)
class ProjectDateRange:
    """Rango de fechas usado para consultar Clockify."""

    start_date: date | None
    end_date: date | None
    source: str


class ProjectDateRangeResolver:
    """Calcula el rango de fechas de cada proyecto interno."""

    def __init__(self, reader: SheetReader, today: date) -> None:
        self._reader = reader
        self._today = today
        self._rows_by_sheet: dict[str, list[list[CellValue]]] = {}

    def resolve(self, project_id: str) -> ProjectDateRange:
        """
        Calcula el rango del proyecto segun su tipo.

        Args:
            project_id: ID interno del proyecto.

        Returns:
            El rango de fechas; las fechas son None si no se encontro.
        """
        if cr_nomenclature(project_id):
            return self._resolve_from_history(project_id)
        if project_id.strip().upper().startswith(MPB_PROJECT_PREFIXES):
            # Preserve the original range contract for every consumer, not only
            # the dashboard that explicitly requests resolve_full().
            return self._resolve_from_mpb(project_id, union=True)

        return self._resolve_from_history(project_id)

    def resolve_full(self, project_id: str) -> ProjectDateRange:
        """
        Alias explícito del rango completo de resolve().

        Un proyecto puede tener una fila terminada y otra en curso;
        ambos accesos conservan el rango histórico que abarca todas sus filas.
        """
        if cr_nomenclature(project_id) or not (
            project_id.strip().upper().startswith(MPB_PROJECT_PREFIXES)
        ):
            return self.resolve(project_id)

        return self._resolve_from_mpb(project_id, union=True)

    def resolve_from_history(self, project_id: str) -> ProjectDateRange:
        """
        Rango Discovery -> Deployment de Historico_Proyectos A:I.

        Equivale a _clockifyRangoHistoricoAI_(); se usa para cualquier
        tipo de proyecto (Gantt de etapas).

        Args:
            project_id: ID interno del proyecto.

        Returns:
            El rango; las fechas son None si no hay Discovery.
        """
        return self._resolve_from_history(project_id)

    def _resolve_from_mpb(
        self, project_id: str, union: bool = False, any_service: bool = False
    ) -> ProjectDateRange:
        """
        Lee INICIO y FIN de la hoja MPB.

        Si el encabezado FIN ya no existe (la hoja actual tiene
        "FIN ORIGINAL" en H), la fecha fin se toma de la columna I.
        """
        from apps.ejecutivo.constants import (
            MPB_COLUMN_COUNT as EVA_MPB_COLUMNS,
        )

        rows = self._read_first_columns(
            SHEET_MPB,
            max(MPB_COLUMN_COUNT, EVA_MPB_COLUMNS),
        )
        header_index = find_header_row(
            rows,
            ("ID", "SERVICE", "INICIO"),
            normalize_mpb_text,
        )

        if header_index is None:
            return ProjectDateRange(None, None, SHEET_MPB)

        headers = [normalize_mpb_text(cell) for cell in rows[header_index]]
        id_column = headers.index("ID")
        service_column = headers.index("SERVICE")
        start_column = headers.index("INICIO")
        end_column = (
            headers.index("FIN") if "FIN" in headers else MPB_END_FALLBACK_INDEX
        )
        normalized_id = normalize_mpb_text(project_id)
        first_data_row = header_index + 1

        matches = [
            ProjectDateRange(
                start_date=parse_sheet_date(read_cell(row, start_column)),
                end_date=(
                    parse_sheet_date(read_cell(row, end_column)) or self._today
                ),
                source=SHEET_MPB,
            )
            for row in rows[first_data_row:]
            if normalize_mpb_text(read_cell(row, id_column)) == normalized_id
            and (
                any_service
                or normalize_mpb_text(read_cell(row, service_column))
                in MPB_SERVICES
            )
        ]

        if matches:
            starts = [m.start_date for m in matches if m.start_date]
            ends = [m.end_date for m in matches if m.end_date]
            if union and starts and ends:
                return ProjectDateRange(min(starts), max(ends), SHEET_MPB)
            return matches[0]

        if any_service:
            return ProjectDateRange(None, None, SHEET_MPB)

        suffix = re.sub(r"^(?:AER|TYM)\.", "", normalized_id)
        aliases = [
            row
            for row in rows[first_data_row:]
            if normalize_mpb_text(read_cell(row, service_column))
            in MPB_SERVICES
            and re.sub(
                r"^(?:AER|TYM)\.",
                "",
                normalize_mpb_text(read_cell(row, id_column)),
            )
            == suffix
        ]
        if len(aliases) == 1:
            row = aliases[0]
            return ProjectDateRange(
                parse_sheet_date(read_cell(row, start_column)),
                parse_sheet_date(read_cell(row, end_column)) or self._today,
                SHEET_MPB + " (ID equivalente AER/TYM)",
            )
        return ProjectDateRange(None, None, SHEET_MPB)

    def _mpb_fallback(self, project_id: str, source: str) -> ProjectDateRange:
        """Use MPB only when the historical stages provide no start."""
        found = self._resolve_from_mpb(project_id, union=True, any_service=True)
        if found.start_date is None:
            return ProjectDateRange(None, None, source)
        return found

    def _resolve_from_history(self, project_id: str) -> ProjectDateRange:
        """Lee Discovery y Deployment de Historico_Proyectos A:I."""
        source = sheet_names.SHEET_PROJECTS_HISTORY
        rows = self._read_first_columns(source, HISTORY_COLUMN_COUNT)
        header_index = find_header_row(
            rows,
            ("project id", "status", "start", "finish"),
            normalize_history_text,
        )

        if header_index is None:
            return self._mpb_fallback(project_id, source)

        headers = [normalize_history_text(cell) for cell in rows[header_index]]
        id_column = headers.index("project id")
        status_column = headers.index("status")
        start_column = headers.index("start")
        finish_column = headers.index("finish")
        normalized_id = normalize_project_id(project_id)
        first_data_row = header_index + 1
        matches = [
            row
            for row in rows[first_data_row:]
            if normalize_project_id(read_cell(row, id_column)) == normalized_id
        ]

        terminal_rows = [
            row
            for row in matches
            if normalize_history_text(read_cell(row, status_column))
            in {"completed", "completado", "cancelled", "canceled", "cancelado"}
        ]
        terminal_dates = [
            day
            for row in terminal_rows
            if (
                day := parse_sheet_date(read_cell(row, finish_column))
                or parse_sheet_date(read_cell(row, start_column))
            )
            is not None
        ]
        if terminal_dates:
            finish = max(terminal_dates)
            operational_starts = [
                day
                for row in matches
                if normalize_history_text(read_cell(row, status_column))
                == "discovery op"
                and (day := parse_sheet_date(read_cell(row, start_column)))
                is not None
                and day <= finish
            ]
            real_starts = [
                day
                for row in matches
                if normalize_history_text(read_cell(row, status_column))
                == "discovery"
                and (day := parse_sheet_date(read_cell(row, start_column)))
                is not None
                and day <= finish
            ]
            starts = operational_starts or real_starts
            if starts:
                return ProjectDateRange(min(starts), finish, source)
        discovery_start = pick_stage_date(
            matches,
            STAGE_DISCOVERY,
            status_column,
            start_column,
        )

        if discovery_start is None:
            return self._mpb_fallback(project_id, source)

        deployment_end = pick_stage_date(
            matches,
            STAGE_DEPLOYMENT,
            status_column,
            finish_column,
        )

        return ProjectDateRange(
            start_date=discovery_start,
            end_date=deployment_end or self._today,
            source=source,
        )

    def _read_first_columns(
        self,
        sheet_name: str,
        column_count: int,
    ) -> list[list[CellValue]]:
        """Lee una sola vez las primeras columnas de una hoja."""
        if sheet_name not in self._rows_by_sheet:
            rows: list[list[CellValue]] = []

            if self._reader.sheet_exists(sheet_name):
                rows = [
                    list(row[:column_count])
                    for row in self._reader.read_values(sheet_name)
                ]

            self._rows_by_sheet[sheet_name] = rows

        return self._rows_by_sheet[sheet_name]


def find_header_row(
    rows: Sequence[Sequence[CellValue]],
    required_headers: Sequence[str],
    normalize: Callable[[CellValue], str],
) -> int | None:
    """
    Busca la fila de encabezados entre las primeras 12 filas.

    Args:
        rows: Filas de la hoja.
        required_headers: Encabezados normalizados que deben existir.
        normalize: Funcion que normaliza cada celda.

    Returns:
        El indice de la fila de encabezados, o None.
    """
    for row_index, row in enumerate(rows[:HEADER_SEARCH_ROWS]):
        normalized_cells = {normalize(cell) for cell in row}

        if all(header in normalized_cells for header in required_headers):
            return row_index

    return None


def pick_stage_date(
    rows: Sequence[Sequence[CellValue]],
    stage: str,
    status_column: int,
    date_column: int,
) -> date | None:
    """
    Elige la fecha de una etapa priorizando la real sobre la estimada.

    Args:
        rows: Filas del historico del proyecto.
        stage: discovery o deployment.
        status_column: Columna Status.
        date_column: Columna Start o Finish.

    Returns:
        La fecha de la fila con mayor prioridad, o None.
    """
    candidates: list[tuple[int, date]] = []

    for row in rows:
        stage_rank = rank_stage_status(read_cell(row, status_column), stage)
        stage_date = parse_sheet_date(read_cell(row, date_column))

        if stage_rank >= RANK_OTHER and stage_date is not None:
            candidates.append((stage_rank, stage_date))

    if not candidates:
        return None

    if stage == STAGE_DISCOVERY:
        operational_dates = [
            day for rank, day in candidates if rank >= RANK_OPERATION
        ]
        if operational_dates:
            return min(operational_dates)
    best_rank = max(rank for rank, _ in candidates)
    dates = [day for rank, day in candidates if rank == best_rank]
    # Repeated stages represent resumptions/extensions. Keep the first
    # Discovery start and the last Deployment finish, regardless of row order.
    return max(dates) if stage == STAGE_DEPLOYMENT else min(dates)


def rank_stage_status(status: CellValue, stage: str) -> int:
    """
    Da prioridad al estatus: real, operacion (OP), estimado (EST).

    Args:
        status: Valor de la columna Status.
        stage: Etapa buscada en minusculas.

    Returns:
        3 real, 2 OP, 1 EST, 0 otro, -1 si no es la etapa.
    """
    normalized_status = normalize_history_text(status)

    if not normalized_status.startswith(stage):
        return RANK_NONE

    if normalized_status == stage:
        return RANK_REAL

    if re.search(r"\bop\b", normalized_status):
        return RANK_OPERATION

    if re.search(r"\best\b", normalized_status):
        return RANK_ESTIMATED

    return RANK_OTHER


def parse_sheet_date(value: CellValue) -> date | None:
    """
    Convierte una celda a fecha, aceptando dd/mm/aa y dd/mm/aaaa.

    Args:
        value: Numero de serie de Sheets o texto de fecha.

    Returns:
        La fecha, o None si la celda no es una fecha.
    """
    text = to_text(value).strip()
    short_match = SHORT_DAY_MONTH_YEAR.match(text)

    if short_match:
        day_text, month_text, year_text = short_match.groups()

        if len(year_text) == TWO_DIGIT_YEAR_LENGTH:
            year_text = f"20{year_text}"

        try:
            return date(int(year_text), int(month_text), int(day_text))
        except ValueError:
            # Fecha imposible (por ejemplo 31/02/2026): se trata como
            # celda sin fecha, igual que el original.
            return None

    moment = to_datetime(value)

    return moment.date() if moment is not None else None


def normalize_history_text(value: CellValue) -> str:
    """
    Normaliza texto del historico: minusculas y espacios simples.

    Args:
        value: Valor de la celda.

    Returns:
        El texto normalizado.
    """
    lowered_text = strip_accents(to_text(value)).lower()

    return re.sub(r"\s+", " ", lowered_text).strip()


def normalize_mpb_text(value: CellValue) -> str:
    """
    Normaliza texto de MPB: mayusculas y sin espacios.

    Args:
        value: Valor de la celda.

    Returns:
        El texto normalizado.
    """
    return re.sub(r"\s+", "", strip_accents(to_text(value)).upper())


def normalize_project_id(value: CellValue) -> str:
    """
    Normaliza un ID de proyecto: mayusculas y sin espacios.

    Args:
        value: ID del proyecto.

    Returns:
        El ID normalizado.
    """
    return re.sub(r"\s+", "", canonical_cr_id(to_text(value)).upper())


def read_cell(row: Sequence[CellValue], column_index: int) -> CellValue:
    """
    Lee una celda tolerando filas recortadas por la API.

    Args:
        row: Fila de valores.
        column_index: Indice de la columna.

    Returns:
        El valor de la celda, o cadena vacia si no existe.
    """
    if column_index < len(row):
        return row[column_index]

    return ""
