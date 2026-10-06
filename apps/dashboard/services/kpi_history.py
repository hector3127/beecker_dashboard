"""Snapshot semanal de KPIs y comparativo contra la semana anterior."""

import logging
from datetime import datetime

from apps.dashboard.constants import (
    KPI_HISTORY_HEADERS,
    SNAPSHOT_MAX_AGE_DAYS,
    SNAPSHOT_MIN_AGE_DAYS,
    SNAPSHOT_TARGET_AGE_DAYS,
)
from apps.dashboard.schemas.dashboard_models import KpiDelta, PortfolioKpis
from core.exceptions import SheetsError
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.cell_types import CellValue, SheetRow
from core.utils.dates import days_between, to_datetime
from core.utils.numbers import round_half_up, to_number

"""BKD.010.011 - Historico de KPIs
Equivale a _guardarSnapshotKpis() y _calcularDeltaVsSemanaAnterior().
Busca el snapshot mas cercano a 7 dias (entre 5 y 10) para tolerar que
el dashboard no se abra exactamente cada semana.
"""

logger = logging.getLogger(__name__)

EMPTY_DELTA = KpiDelta(
    active_projects=None,
    average_progress=None,
    weekly_hours=None,
    high_risks=None,
    weekly_red_flags=None,
    average_margin=None,
)


class KpiHistoryService:
    """Lee y escribe la hoja Dashboard_Historico_KPIs."""

    def __init__(self, reader: SheetReader, writer: SheetWriter) -> None:
        self._reader = reader
        self._writer = writer

    def calculate_weekly_delta(
        self,
        kpis: PortfolioKpis,
        now: datetime,
    ) -> KpiDelta:
        """
        Compara los KPIs actuales contra el snapshot de hace una semana.

        Args:
            kpis: KPIs actuales.
            now: Fecha y hora actual.

        Returns:
            La diferencia por KPI; todo None si no hay snapshot util.
        """
        history_name = sheet_names.SHEET_DASHBOARD_KPI_HISTORY

        try:
            if not self._reader.sheet_exists(history_name):
                return EMPTY_DELTA

            history_rows = self._reader.read_as_objects(history_name)
        except SheetsError as error:
            # El comparativo es informativo: si falla, el dashboard se
            # muestra sin flechas de variacion, igual que el original.
            logger.warning(
                "No se pudo leer el historico de KPIs: %s",
                error.detail,
            )
            return EMPTY_DELTA

        base_row = find_week_ago_snapshot(history_rows, now)

        if base_row is None:
            return EMPTY_DELTA

        return KpiDelta(
            active_projects=calculate_delta(
                kpis.active_projects,
                base_row.get("ProyectosActivos"),
            ),
            average_progress=calculate_delta(
                kpis.average_progress,
                base_row.get("AvancePromedio"),
            ),
            weekly_hours=calculate_delta(
                kpis.weekly_hours,
                base_row.get("HorasSemana"),
            ),
            high_risks=calculate_delta(
                kpis.high_risks,
                base_row.get("RiesgosAltos"),
            ),
            weekly_red_flags=calculate_delta(
                kpis.weekly_red_flags,
                base_row.get("FocoRojoSemana"),
            ),
            average_margin=calculate_delta(
                kpis.average_margin,
                base_row.get("MargenPromedio"),
            ),
        )

    def save_snapshot(self, kpis: PortfolioKpis, now: datetime) -> None:
        """
        Guarda los KPIs actuales como snapshot del dia.

        Args:
            kpis: KPIs de la vista general sin filtros.
            now: Fecha y hora actual.
        """
        history_name = sheet_names.SHEET_DASHBOARD_KPI_HISTORY

        try:
            self._writer.ensure_sheet(history_name, KPI_HISTORY_HEADERS)
            self._writer.append_row(
                history_name,
                [
                    now,
                    kpis.active_projects,
                    kpis.average_progress,
                    kpis.weekly_hours,
                    kpis.high_risks,
                    kpis.weekly_red_flags,
                    "" if kpis.average_margin is None else kpis.average_margin,
                ],
            )
        except SheetsError as error:
            # El snapshot no debe impedir que el usuario vea el
            # dashboard; se registra y se continua.
            logger.warning(
                "No se pudo guardar el snapshot de KPIs: %s",
                error.detail,
            )


def find_week_ago_snapshot(
    history_rows: list[SheetRow],
    now: datetime,
) -> SheetRow | None:
    """
    Elige el snapshot con antiguedad mas cercana a 7 dias.

    Args:
        history_rows: Filas del historico de KPIs.
        now: Fecha y hora actual.

    Returns:
        La fila elegida, o None si ninguna tiene entre 5 y 10 dias.
    """
    candidates: list[tuple[float, SheetRow]] = []

    for history_row in history_rows:
        snapshot_date = to_datetime(history_row.get("Fecha"))

        if snapshot_date is None:
            continue

        age_days = days_between(snapshot_date, now)

        if SNAPSHOT_MIN_AGE_DAYS <= age_days <= SNAPSHOT_MAX_AGE_DAYS:
            candidates.append((age_days, history_row))

    if not candidates:
        return None

    candidates.sort(
        key=lambda candidate: abs(candidate[0] - SNAPSHOT_TARGET_AGE_DAYS),
    )

    return candidates[0][1]


def calculate_delta(
    current_value: float | None,
    previous_value: CellValue,
) -> float | None:
    """
    Calcula la variacion de un KPI con un decimal.

    Args:
        current_value: Valor actual del KPI.
        previous_value: Valor guardado en el snapshot.

    Returns:
        La diferencia, o None si alguno de los valores no existe.
    """
    if current_value is None:
        # El original convertia null a 0 y reportaba una variacion
        # falsa cuando hoy no hay margen; aqui se omite.
        return None

    if previous_value is None or previous_value == "":
        return None

    if isinstance(previous_value, str) and not is_numeric_text(previous_value):
        return None

    return round_half_up(current_value - to_number(previous_value), 1)


def is_numeric_text(text: str) -> bool:
    """
    Indica si un texto representa un numero.

    Args:
        text: Texto a evaluar.

    Returns:
        True cuando Number(text) no seria NaN en JavaScript.
    """
    try:
        float(text.strip())
    except ValueError:
        return False

    return True
