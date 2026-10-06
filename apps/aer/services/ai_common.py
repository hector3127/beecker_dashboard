"""Piezas comunes de la IA por proyecto AER/T&M (AERIAService.gs)."""

import base64
import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

from core.exceptions import DashboardError
from core.integrations.claude_client import ClaudeClient
from core.sheets import sheet_names
from core.sheets.protocols import SheetReader, SheetWriter
from core.utils.cell_types import CellValue
from core.utils.dates import to_datetime, to_local_naive
from core.utils.js_values import js_json, js_len, js_number, js_slice, js_str

"""BKD.080.010 - IA AER: piezas comunes
Equivale a _aeriText(), _aeriValidateProject(), _aeriSnapshot() y
_aeriCachedKey(): valida que el proyecto sea AER/T&M, arma el contexto
reducido (lista blanca de campos) y la llave de cache de Claude.
"""

JsonObject = dict[str, Any]

PROMPTS = json.loads(
    (
        Path(__file__).resolve().parent.parent
        / "prompts"
        / "aer_ia_prompts.json"
    ).read_text("utf-8"),
)
AER_SERVICES = ("AER", "TYM", "T&M")
MAX_CONTEXT = 13500
DEFAULT_TEXT = 120
HALF_MS = timedelta(microseconds=500)


class AerAiError(DashboardError):
    """Error controlado con el mismo texto que el original."""

    code = "ERR_AER_IA"
    http_status = 400
    expose_detail = True


class CacheStore(Protocol):
    """Cache de Django (get/set)."""

    def get(self, key: str) -> Any:
        """Valor guardado o None."""
        ...

    def set(self, key: str, value: Any, timeout: int | None) -> None:
        """Guarda con expiracion en segundos."""
        ...


@dataclass(slots=True)
class AerAiContext:
    """Hojas, Claude, cache, reloj y Drive de la IA AER."""

    reader: SheetReader
    writer: SheetWriter
    now: datetime
    api_key: str
    model: str
    build_client: Callable[[], ClaudeClient]
    cache: CacheStore
    new_uid: Callable[[], str]
    drive: Any = None

    def local_now(self) -> datetime:
        """Hora local sin zona."""
        return to_local_naive(self.now) if self.now.tzinfo else self.now

    def stamp(self) -> str:
        """yyyy-MM-dd HH:mm:ss."""
        return self.local_now().strftime("%Y-%m-%d %H:%M:%S")

    def today(self) -> str:
        """yyyy-MM-dd."""
        return self.local_now().strftime("%Y-%m-%d")


def clip(value: object, limit: int = 0) -> str:
    """String(v ?? '').trim().slice(0, n || 120) (_aeriText)."""
    text = "" if value is None else js_str(value)

    return js_slice(text.strip(), 0, limit or DEFAULT_TEXT)


def display(value: CellValue | datetime, kind: str = "") -> str:
    """
    Texto visible de la celda (getDisplayValues).

    Las fechas se escriben como texto yyyy-MM-dd (HH:mm:ss) y Sheets las
    guarda como fecha; se regresan con ese mismo formato.
    """
    if value is None:
        return ""

    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"

    if kind and (isinstance(value, datetime) or isinstance(value, int | float)):
        moment = to_datetime(value)

        if moment is not None:
            moment = (moment + HALF_MS).replace(microsecond=0)
            pattern = "%Y-%m-%d %H:%M:%S" if kind == "datetime" else "%Y-%m-%d"

            return moment.strftime(pattern)

    return js_str(value)


def read_rows(
    reader: SheetReader,
    sheet: str,
    kinds: Sequence[str],
) -> list[list[str]]:
    """
    Filas 2.. con el ancho de kinds, como getRange(2,1,n,w).getDisplayValues().

    Args:
        reader: Repositorio de Sheets.
        sheet: Nombre de la hoja.
        kinds: Tipo de cada columna ("", "date" o "datetime").

    Returns:
        Filas de texto; vacio si la hoja no existe o solo tiene encabezado.
    """
    if not reader.sheet_exists(sheet):
        return []

    rows = []

    for row in reader.read_values(sheet)[1:]:
        cells = list(row) + [""] * (len(kinds) - len(row))
        rows.append(
            [display(cells[i], kind) for i, kind in enumerate(kinds)],
        )

    while rows and not any(rows[-1]):
        rows.pop()

    return rows


def validate_project(reader: SheetReader, value: object) -> str:
    """
    ID de un proyecto AER/T&M de la hoja Proyectos (_aeriValidateProject).

    Raises:
        AerAiError: Si falta el ID o el proyecto no es AER/T&M.
    """
    project_id = clip(value, 80)

    if not project_id:
        raise AerAiError("Selecciona un proyecto.")

    row = next(
        (
            item
            for item in reader.read_as_objects(sheet_names.SHEET_PROJECTS)
            if js_str(item.get("ID_Proyecto") or "").strip() == project_id
        ),
        None,
    )
    service = js_str((row or {}).get("Servicio") or "").strip().upper()

    if row is None or service not in AER_SERVICES:
        raise AerAiError("El proyecto no existe o no pertenece a AER/T&M.")

    return project_id


def items(raw: Any, key: str, limit: int) -> list[Any]:
    """(raw[key] || []).slice(0, limit)."""
    values = raw.get(key) if isinstance(raw, dict) else None

    if not values:
        return []

    return list(values)[:limit] if isinstance(values, list | str) else []


def field(entry: Any, key: str) -> Any:
    """entry[key] tolerando valores que no son objetos."""
    return entry.get(key) if isinstance(entry, dict) else None


def number(value: Any) -> float:
    """Number(x) || 0."""
    result = js_number(value)

    return 0 if result != result or not result else result


def snapshot_object(raw: Any, project_id: str) -> JsonObject:
    """
    Contexto reducido del proyecto con lista blanca de campos.

    Raises:
        AerAiError: Si el contexto es de otro proyecto.
    """
    if not raw or js_str(field(raw, "id") or "") != project_id:
        raise AerAiError(
            "Contexto del proyecto no coincide. Actualiza la vista.",
        )

    def pick(key: str, limit: int, spec: dict[str, int]) -> list[JsonObject]:
        return [
            {
                name: (
                    number(field(entry, name))
                    if size == 0
                    else clip(field(entry, name), size)
                )
                for name, size in spec.items()
            }
            for entry in items(raw, key, limit)
        ]

    return {
        "id": project_id,
        "fecha": clip(field(raw, "fecha"), 12),
        "n": clip(field(raw, "n"), 90),
        "cliente": clip(field(raw, "cliente"), 70),
        "etapa": clip(field(raw, "etapa"), 45),
        "k": field(raw, "k") or {},
        "p": pick(
            "p", 16, {"a": 85, "r": 55, "f": 12, "e": 22, "z": 0, "d": 65}
        ),
        "r": pick("r", 7, {"a": 100, "i": 12, "e": 20}),
        "a": pick("a", 8, {"a": 95, "r": 45, "f": 12, "e": 18}),
        "v": pick("v", 6, {"r": 45, "i": 12, "f": 12, "e": 16}),
        "c": pick("c", 10, {"r": 45, "o": 0}),
        "b": pick("b", 24, {"a": 145, "o": 8, "f": 12, "e": 20, "n": 155}),
    }


def snapshot(raw: Any, project_id: str) -> str:
    """JSON compacto del contexto (_aeriSnapshot)."""
    compact = js_json(snapshot_object(raw, project_id))

    if js_len(compact) > MAX_CONTEXT:
        raise AerAiError(
            "Contexto demasiado largo. Reduce actividades y vuelve a intentar.",
        )

    return compact


def cache_key(payload: str) -> str:
    """aeri_v1_ + SHA-256 en base64 web-safe (35 caracteres)."""
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    encoded = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    return f"aeri_v1_{encoded[:35]}"
