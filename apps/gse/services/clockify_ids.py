"""IDs de Clockify de las personas de Bandas/rol."""

import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from apps.capacidad.constants import MONTH_PATTERN
from apps.clockify.constants import FORBIDDEN_STATUS, SUCCESS_STATUS_LIMIT
from apps.clockify.services.clockify_client import ClockifyClient
from apps.gse.constants import ROLE_COLUMN, SHEET_ROSTER
from apps.gse.exceptions import GseError
from apps.gse.services.base_store import HourRecord
from apps.gse.services.base_writer import SheetStore
from apps.gse.services.cells import cell_at, norm, trimmed
from core.exceptions import DashboardError, describe_error
from core.utils.locks import LockTimeoutError, script_lock
from core.utils.text import to_text

"""BKD.100.015 - IDs de Clockify
Equivale a gseObtenerIDsClockify(), gseIdsGuardar_() y gseIdRoster_():
busca el ID de Clockify de cada persona (por la lista de usuarios o, si
la clave no puede listarlos, por el reporte del mes) y lo escribe en la
columna ID Clockify de Bandas/rol. Solo escribe coincidencias unicas por
nombre completo y nunca sobreescribe un ID existente.
"""

USERS_PAGE_SIZE = 200
USERS_MAX_PAGES = 1000
USERS_TIME_LIMIT_SECONDS = 40
LOCK_SECONDS = 5
ID_COLUMN = 4
ID_HEADER = "ID Clockify"
SOURCE_USERS = "Lista de usuarios"
NOTICE_REPORT = (
    "La clave no permitió listar usuarios. Se obtuvieron los IDs presentes "
    "en el reporte del mes; puedes elegir otro mes para completar "
    "pendientes."
)
NOTICE_USERS = (
    "Solo se guardan coincidencias únicas por nombre completo. Los IDs "
    "existentes se conservan."
)

JsonObject = dict[str, Any]
Candidate = tuple[str, str]
MonthHours = Callable[[str, bool, list[str] | None], list[HourRecord]]


@dataclass(frozen=True, slots=True)
class IdsContext:
    """Lo que necesita la busqueda de IDs de Clockify."""

    sheets: SheetStore
    client: ClockifyClient | None
    workspace: str
    load_month_hours: MonthHours
    clock: Callable[[], float] = time.monotonic


def get_clockify_ids(
    context: IdsContext,
    month: object,
    report_only: object,
) -> JsonObject:
    """
    Busca los IDs de Clockify y los guarda en Bandas/rol.

    Args:
        context: Hojas, cliente de Clockify y reporte del mes.
        month: Mes YYYY-MM para el reporte cuando no hay lista de usuarios.
        report_only: Salta la lista de usuarios y usa solo el reporte.

    Returns:
        {"ok", "guardados", "pendientes", "fuente", "aviso"} o
        {"ok": False, "error"}.
    """
    try:
        return find_and_save_ids(context, month, bool(report_only))
    except DashboardError as error:
        return {"ok": False, "error": describe_error(error)}


def find_and_save_ids(
    context: IdsContext,
    month: object,
    report_only: bool,
) -> JsonObject:
    """
    Reune los candidatos y los guarda.

    Raises:
        GseError: Cuando el mes, Clockify o Bandas/rol no sirven.
    """
    if not isinstance(month, str) or not MONTH_PATTERN.fullmatch(month):
        raise GseError("Mes inválido.")

    candidates: list[Candidate] = []
    source = SOURCE_USERS

    if not report_only:
        if context.client is None or not context.workspace:
            raise GseError("Clockify no está configurado.")

        users = list_users(context)

        if users is None:
            report_only = True
        else:
            candidates.extend(users)

    if report_only:
        source = f"Reporte de {month}"
        records = context.load_month_hours(month, False, None)
        candidates.extend(
            (record.resource, record.user_id)
            for record in records
            if record.user_id
        )

    result = save_ids(context.sheets, candidates)
    result["fuente"] = source
    result["aviso"] = NOTICE_REPORT if report_only else NOTICE_USERS

    return result


def list_users(context: IdsContext) -> list[Candidate] | None:
    """
    Lista nombre e ID de los usuarios del workspace.

    Args:
        context: Hojas, cliente de Clockify y reporte del mes.

    Returns:
        Los usuarios, o None si la clave no puede listarlos (HTTP 403).

    Raises:
        GseError: Cuando Clockify falla o la lista no termina a tiempo.
    """
    client = context.client
    assert client is not None
    started = context.clock()
    users: list[Candidate] = []

    for page in range(1, USERS_MAX_PAGES + 1):
        response = client.get_users_page(
            context.workspace,
            page,
            USERS_PAGE_SIZE,
        )

        if response.status_code == FORBIDDEN_STATUS:
            return None

        if response.status_code >= SUCCESS_STATUS_LIMIT:
            raise GseError(
                f"Clockify HTTP {response.status_code} al listar usuarios.",
            )

        page_users = read_users(response)
        users.extend(
            (to_text(item.get("name")), item_id(item)) for item in page_users
        )

        if len(page_users) < USERS_PAGE_SIZE:
            return users

        if context.clock() - started > USERS_TIME_LIMIT_SECONDS:
            raise GseError(
                "Listado de usuarios demasiado largo; no se guardaron IDs "
                "parciales.",
            )

    raise GseError("No se completó la lista de usuarios.")


def read_users(response: Any) -> list[JsonObject]:
    """
    Lista de usuarios de una pagina (arreglo o {"users": [...]}).

    Raises:
        GseError: Cuando la respuesta no trae la lista.
    """
    try:
        data = response.json()
    except ValueError as error:
        raise GseError("Clockify no devolvio JSON valido.") from error

    users = data.get("users") if isinstance(data, dict) else data

    if not isinstance(users, list):
        raise GseError("Respuesta sin lista de usuarios.")

    return users


def item_id(item: JsonObject) -> str:
    """ID de un usuario como texto; vacio si no trae."""
    return to_text(item.get("id")) if item.get("id") else ""


def find_roster_header(rows: Sequence[Sequence[Any]]) -> int:
    """
    Fila con Nombre en A y ROL en C.

    Raises:
        GseError: Cuando no existe.
    """
    for index, row in enumerate(rows):
        if (
            norm(cell_at(row, 0)) == "nombre"
            and norm(cell_at(row, ROLE_COLUMN)) == "rol"
        ):
            return index

    raise GseError("Se requieren Nombre en A y ROL en C.")


def save_ids(
    sheets: SheetStore,
    candidates: Sequence[Candidate],
) -> JsonObject:
    """
    Escribe los IDs unicos en la columna ID Clockify de Bandas/rol.

    Args:
        sheets: Repositorio de Sheets con lectura y escritura.
        candidates: Nombre e ID de Clockify de cada usuario.

    Returns:
        {"ok": True, "guardados": n, "pendientes": [nombres]}.

    Raises:
        GseError: Cuando otro proceso escribe a la vez o falta la hoja.
    """
    try:
        with script_lock(LOCK_SECONDS):
            return write_ids(sheets, candidates)
    except LockTimeoutError as error:
        raise GseError("La hoja está siendo actualizada. Reintenta.") from error


def write_ids(
    sheets: SheetStore,
    candidates: Sequence[Candidate],
) -> JsonObject:
    """Agrega la columna si falta y escribe los IDs sin ambiguedad."""
    if not sheets.sheet_exists(SHEET_ROSTER):
        raise GseError("Falta Bandas/rol.")

    rows = sheets.read_values(SHEET_ROSTER)
    header_index = find_roster_header(rows)

    if norm(cell_at(rows[header_index], ID_COLUMN - 1)) != norm(ID_HEADER):
        if any(trimmed(cell_at(row, ID_COLUMN - 1)) for row in rows):
            sheets.insert_column_after(SHEET_ROSTER, ID_COLUMN - 1)

        sheets.write_cell(SHEET_ROSTER, header_index + 1, ID_COLUMN, ID_HEADER)

    current = sheets.read_values(SHEET_ROSTER)
    people = current[header_index + 1 :]
    name_counts = Counter(
        norm(cell_at(row, 0)) for row in people if norm(cell_at(row, 0))
    )
    matches: dict[str, dict[str, None]] = {}

    for name, user_id in candidates:
        key = norm(name)

        if key and user_id:
            matches.setdefault(key, {})[user_id] = None

    cells: list[tuple[int, int, str]] = []
    pending: list[str] = []

    for offset, row in enumerate(people):
        name = trimmed(cell_at(row, 0))

        if not name or trimmed(cell_at(row, ID_COLUMN - 1)):
            continue

        key = norm(name)
        ids = matches.get(key)

        if name_counts[key] != 1 or not ids or len(ids) != 1:
            pending.append(name)
            continue

        cells.append((header_index + offset + 2, ID_COLUMN, next(iter(ids))))

    sheets.write_text_cells(SHEET_ROSTER, cells)

    return {"ok": True, "guardados": len(cells), "pendientes": pending}
