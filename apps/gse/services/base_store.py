"""Base de horas guardada en Sheets y su cobertura."""

import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from apps.gse.constants import (
    BASE_REQUIRED_HEADERS,
    BASE_SHEET_PREFIX,
    BILLABLE_TEXT,
    CONTROL_SHEET,
    HEADER_SEARCH_ROWS,
    LEGACY_DATE,
    TAG_SEPARATOR,
)
from apps.gse.exceptions import GseError
from apps.gse.services.cells import (
    SheetValues,
    cell_at,
    format_base_date,
    norm,
    trimmed,
)
from core.sheets.protocols import SheetReader
from core.utils.cell_types import CellValue
from core.utils.dates import LOCAL_TIMEZONE, to_datetime
from core.utils.js_values import js_number, js_or_text
from core.utils.text import to_text

"""BKD.100.007 - Base de GSE en Sheets
Equivale a gseBaseLeer_(), gseBaseMes_() y gseBaseSchema_(): lee los
registros de 08.Base Clockify AAAA y su cobertura en GSE_Base_Control.
"""

STALE_SECONDS = 3600
WORKSPACE_UNSAFE = re.compile(r"[^a-zA-Z0-9_-]")


@dataclass(frozen=True, slots=True)
class HourRecord:
    """Registro de horas de una persona en un dia."""

    record_id: str
    user_id: str
    resource: str
    project: str
    task: str
    tags: list[str]
    billable: bool
    day: str
    hours: float


@dataclass(frozen=True, slots=True)
class Connection:
    """Workspace de Clockify y llave de la conexion activa."""

    workspace: str
    key: str


def build_connection(api_key: str, workspace_id: str) -> Connection:
    """
    Calcula la llave de conexion como _clockifyClaveConexionCache_().

    Nunca contiene la API key: solo los primeros 8 bytes de su SHA-256.

    Args:
        api_key: API key de Clockify.
        workspace_id: ID del workspace.

    Returns:
        El workspace y la llave workspace_huella.
    """
    safe_workspace = WORKSPACE_UNSAFE.sub("_", workspace_id)
    fingerprint = hashlib.sha256(api_key.encode()).hexdigest()[:16]

    return Connection(workspace_id, f"{safe_workspace}_{fingerprint}")


def base_sheet_title(year: int | str) -> str:
    """Nombre de la hoja de la base de un ano."""
    return f"{BASE_SHEET_PREFIX}{year}"


def find_base_sheet(reader: SheetReader, year: int | str) -> str | None:
    """Hoja de la base del ano (compara sin espacios laterales)."""
    title = base_sheet_title(year)

    for name in reader.list_sheet_names():
        if name.strip() == title:
            return name

    return None


def check_base_schema(
    sheet_name: str,
    values: SheetValues,
) -> list[str]:
    """
    Valida los encabezados de la base GSE.

    Args:
        sheet_name: Nombre de la hoja, para el mensaje.
        values: Contenido de la hoja.

    Returns:
        Los encabezados normalizados.

    Raises:
        GseError: Cuando la hoja tiene otro formato.
    """
    headers = [norm(value) for value in (values[0] if values else [])]

    if not all(name in headers for name in BASE_REQUIRED_HEADERS):
        raise GseError(
            f"La hoja {sheet_name} ya existe con otro formato. Renómbrala "
            "antes de crear la base GSE para conservarla.",
        )

    return headers


def unique_ids(user_ids: Sequence[str] | None) -> list[str] | None:
    """IDs sin repetir y ordenados; None si no hay filtro."""
    if not user_ids:
        return None

    return sorted(set(user_ids))


class BaseStore:
    """Lee la base persistente de horas de GSE."""

    def __init__(
        self,
        reader: SheetReader,
        connection: Connection,
        now: datetime,
    ) -> None:
        """
        Crea el lector de la base.

        Args:
            reader: Repositorio de Sheets.
            connection: Conexion activa de Clockify.
            now: Momento actual con zona horaria.
        """
        self._reader = reader
        self._connection = connection
        self._now = now

    def read_stored_month(
        self,
        month: str,
        user_ids: Sequence[str] | None,
        allow_old: bool,
    ) -> list[HourRecord] | None:
        """
        Lee un mes de la base si su cobertura lo permite.

        Args:
            month: Mes YYYY-MM.
            user_ids: IDs de Clockify pedidos; None para todos.
            allow_old: Acepta coberturas del mes actual con mas de 1 h.

        Returns:
            Los registros (posiblemente vacios), o None si no hay base,
            cobertura o esta vencida.
        """
        sheet_name = find_base_sheet(self._reader, month[:4])
        has_control = self._reader.sheet_exists(CONTROL_SHEET)

        if not has_control or sheet_name is None:
            return None

        ids = unique_ids(user_ids)
        coverage = self._find_coverage(month, ids)

        if coverage is None or self._is_stale(month, coverage, allow_old):
            return None

        grouped = self._group_months(sheet_name)

        return [
            record
            for record in grouped.get(month, [])
            if ids is None or record.user_id in ids
        ]

    def read_sheet_month(
        self,
        month: str,
        user_ids: Sequence[str] | None,
    ) -> list[HourRecord]:
        """
        Lee un mes de la base (equivale a gseBaseMes_).

        Args:
            month: Mes YYYY-MM.
            user_ids: IDs de Clockify pedidos; None para todos.

        Returns:
            Los registros del mes.

        Raises:
            GseError: Cuando falta la base o su formato no sirve.
        """
        stored = self.read_stored_month(month, user_ids, True)

        if stored is not None:
            return stored

        sheet_name = find_base_sheet(self._reader, month[:4])

        if sheet_name is None:
            raise GseError(
                "No existe la base del año. Selecciona API Clockify para "
                "extraerla primero.",
            )

        values = self._reader.read_values(sheet_name)

        if values and any(norm(value) == "conexion gse" for value in values[0]):
            raise GseError(
                "Mes sin cobertura completa para estas personas en la "
                "base. Selecciona API Clockify para extraerlo.",
            )

        return read_legacy_month(values, month)

    def _find_coverage(
        self,
        month: str,
        ids: list[str] | None,
    ) -> list[CellValue] | None:
        """Cobertura mas reciente que incluye a las personas pedidas."""
        prefix = f"{self._connection.key}|{month}|"
        rows = self._reader.read_values(CONTROL_SHEET)[1:]
        candidates = [
            list(row)
            for row in rows
            if to_text(cell_at(row, 0)).startswith(prefix)
            and cell_at(row, 3)
            and covers_ids(cell_at(row, 2), ids)
        ]

        if not candidates:
            return None

        candidates.sort(
            key=lambda row: to_text(cell_at(row, 3)),
            reverse=True,
        )

        return candidates[0]

    def _is_stale(
        self,
        month: str,
        coverage: Sequence[CellValue],
        allow_old: bool,
    ) -> bool:
        """El mes actual solo se acepta si se guardo hace menos de 1 h."""
        current = self._now.astimezone(LOCAL_TIMEZONE).strftime("%Y-%m")

        if allow_old or month < current:
            return False

        saved_at = parse_saved_at(cell_at(coverage, 3))

        if saved_at is None:
            return False

        return (self._now - saved_at).total_seconds() > STALE_SECONDS

    def _group_months(self, sheet_name: str) -> dict[str, list[HourRecord]]:
        """Registros de la conexion por mes, sin IDs de registro repetidos."""
        values = self._reader.read_values(sheet_name)
        headers = check_base_schema(sheet_name, values)
        columns = {name: headers.index(name) for name in headers[::-1]}
        groups: dict[str, list[HourRecord]] = {}
        seen: set[str] = set()

        for row in values[1:]:
            record = read_stored_row(row, columns, self._connection.key)

            if record is None or record.record_id in seen:
                continue

            seen.add(record.record_id)
            groups.setdefault(record.day[:7], []).append(record)

        return groups


def covers_ids(raw_ids: CellValue, ids: list[str] | None) -> bool:
    """La cobertura guardada incluye todas las personas pedidas."""
    try:
        saved = json.loads(to_text(raw_ids))
    except ValueError as error:
        raise GseError(
            "La cobertura de GSE_Base_Control no es valida.",
        ) from error

    if saved is None:
        return True

    return ids is not None and all(item in saved for item in ids)


def parse_saved_at(value: CellValue) -> datetime | None:
    """Momento de guardado de una cobertura; None si no se entiende."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        moment = to_datetime(value)

        return moment.replace(tzinfo=LOCAL_TIMEZONE) if moment else None

    try:
        parsed = datetime.fromisoformat(to_text(value))
    except ValueError:
        return None

    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def read_stored_row(
    row: Sequence[CellValue],
    columns: dict[str, int],
    connection_key: str,
) -> HourRecord | None:
    """Convierte una fila de la base; None si es de otra conexion."""
    if to_text(cell_at(row, columns["conexion gse"])) != connection_key:
        return None

    day = format_base_date(cell_at(row, columns["start date"]))

    if not day[:7]:
        return None

    return HourRecord(
        record_id=to_text(cell_at(row, columns["id registro"])),
        user_id=to_text(cell_at(row, columns["id clockify"])),
        resource=to_text(cell_at(row, columns["user"])),
        project=to_text(cell_at(row, columns["project"])),
        task=to_text(cell_at(row, columns["task"])),
        tags=js_or_text(cell_at(row, columns["tags"])).split(", "),
        billable=cell_at(row, columns["billable"]) == "Yes",
        day=day,
        hours=read_decimal_hours(cell_at(row, columns["duration decimal"])),
    )


def read_decimal_hours(value: CellValue) -> float:
    """Number(x) || 0: texto no numerico cuenta como cero horas."""
    hours = js_number(value)

    return hours if math.isfinite(hours) else 0.0


def read_legacy_month(values: SheetValues, month: str) -> list[HourRecord]:
    """
    Lee un mes de una base con el formato anterior (sin control).

    Args:
        values: Contenido de la hoja.
        month: Mes YYYY-MM.

    Returns:
        Los registros del mes.

    Raises:
        GseError: Cuando faltan columnas o una duracion no es numerica.
    """
    header_index = find_legacy_header(values)
    headers = [norm(value) for value in values[header_index]]
    duration = next(
        (
            index
            for index, name in enumerate(headers)
            if name.startswith("duration") and "decimal" in name
        ),
        -1,
    )

    if duration < 0:
        raise GseError("Falta Duration (decimal) en la base.")

    def column(name: str) -> int:
        return headers.index(name) if name in headers else -1

    records: list[HourRecord] = []

    for offset, row in enumerate(values[header_index + 1 :]):
        day = read_legacy_day(cell_at(row, column("start date")))

        if not day.startswith(month):
            continue

        hours = js_number(cell_at(row, duration))

        if not math.isfinite(hours) or hours < 0:
            raise GseError(
                f"Duración no numérica en fila {header_index + offset + 2}",
            )

        records.append(
            HourRecord(
                record_id="",
                user_id="",
                resource=js_or_text(cell_at(row, column("user"))),
                project=js_or_text(cell_at(row, column("project"))),
                task=js_or_text(cell_at(row, column("task"))),
                tags=TAG_SEPARATOR.split(
                    js_or_text(cell_at(row, column("tags"))),
                ),
                billable=bool(
                    BILLABLE_TEXT.match(
                        js_or_text(cell_at(row, column("billable"))),
                    ),
                ),
                day=day,
                hours=hours,
            ),
        )

    return records


def find_legacy_header(values: SheetValues) -> int:
    """Fila con Project, User y Start Date en las primeras 20."""
    required = ("project", "user", "start date")

    for index, row in enumerate(values[:HEADER_SEARCH_ROWS]):
        norms = [norm(value) for value in row]

        if all(name in norms for name in required):
            return index

    raise GseError("Faltan Project, User o Start Date en la base Clockify.")


def read_legacy_day(raw: CellValue) -> str:
    """Dia de una celda de la base anterior: fecha, dd/MM/yyyy o ISO."""
    if isinstance(raw, int | float) and not isinstance(raw, bool):
        return format_base_date(raw)

    text = trimmed(raw)
    match = LEGACY_DATE.match(text)

    if match:
        day, month, year = match.groups()

        return f"{year}-{month}-{day}"

    return text[:10]
