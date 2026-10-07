"""Horas de un mes de todo el workspace de Clockify."""

import calendar
import hashlib
import logging
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from apps.clockify.constants import (
    FORBIDDEN_STATUS,
    REPORT_PAGE_SIZE,
    REPORT_PAUSE_SECONDS,
    SUCCESS_STATUS_LIMIT,
)
from apps.clockify.services.clockify_client import ClockifyClient
from apps.clockify.services.duration_parser import parse_duration_hours
from apps.gse.exceptions import GseError
from apps.gse.services.base_store import BaseStore, Connection, HourRecord
from core.utils.text import to_text

"""BKD.100.012 - Reporte mensual de Clockify para GSE
Equivale a gseReporteMes_(): primero usa la base guardada y la cache, y
solo si no hay datos descarga el reporte detallado de todo el workspace.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

MAX_PAGES = 200
CACHE_SECONDS = 3600
FILTER_BYTES = 12
CACHE_VERSION = "gse_workspace_v5"

Persist = Callable[[str, list[HourRecord], list[str] | None], None]


class MonthReportLoader:
    """Obtiene las horas de un mes: base, cache o API de Clockify."""

    def __init__(
        self,
        settings: tuple[str, str, str],
        sources: tuple[BaseStore, Connection, Any],
        persist: Persist | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """
        Crea el cargador del reporte mensual.

        Args:
            settings: API key, workspace y zona horaria.
            sources: Base guardada, conexion y cache de Django.
            persist: Guarda en la base los registros descargados.
            sleep: Pausa entre paginas (se cambia en las pruebas).
        """
        self._api_key, self._workspace, self._timezone = settings
        self._store, self._connection, self._cache = sources
        self._persist = persist
        self._sleep = sleep

    def __call__(
        self,
        month: str,
        force: bool,
        user_ids: Sequence[str] | None,
    ) -> list[HourRecord]:
        """
        Devuelve los registros del mes.

        Args:
            month: Mes YYYY-MM.
            force: Ignora la base guardada y la cache.
            user_ids: IDs de Clockify por los que filtrar; vacio es todos.

        Returns:
            Los registros del mes.

        Raises:
            GseError: Cuando Clockify no esta configurado o responde mal.
        """
        if not self._api_key or not self._workspace:
            raise GseError("Clockify no está configurado.")

        ids = list(user_ids) if user_ids else None
        key = self._cache_key(month, ids)

        if not force:
            cached = self._read_saved(month, ids, key)

            if cached is not None:
                return cached

        records = self._download(month, ids)

        if self._persist is not None:
            self._persist(month, records, ids)

        self._cache.set(
            key,
            [asdict(record) for record in records],
            CACHE_SECONDS,
        )

        return records

    def _read_saved(
        self,
        month: str,
        ids: list[str] | None,
        key: str,
    ) -> list[HourRecord] | None:
        """Base guardada o cache de Django; None si no hay."""
        stored = self._store.read_stored_month(month, ids, False)

        if stored is not None:
            return stored

        cached = self._cache.get(key)

        if not isinstance(cached, list):
            return None

        records = [HourRecord(**item) for item in cached]

        if self._persist is not None:
            self._persist(month, records, ids)

        return records

    def _cache_key(self, month: str, ids: list[str] | None) -> str:
        """Llave de cache por filtro, conexion, mes y zona horaria."""
        signature = (
            hashlib.sha256("|".join(ids).encode()).hexdigest()[
                : FILTER_BYTES * 2
            ]
            if ids
            else "all"
        )

        return (
            f"{CACHE_VERSION}_{signature}_{self._connection.key}_"
            f"{month}_{self._timezone}"
        )

    def _download(
        self,
        month: str,
        ids: list[str] | None,
    ) -> list[HourRecord]:
        """Descarga todas las paginas del reporte del mes."""
        client = ClockifyClient(self._api_key, sleep=self._sleep)
        entries: dict[str, HourRecord] = {}
        seen: set[str] = set()

        for page in range(1, MAX_PAGES + 1):
            payload = build_payload(month, ids, page, self._timezone)
            response = client.post_workspace_report(self._workspace, payload)
            raise_for_report_status(response.status_code, month)
            page_entries = read_page_entries(response)
            signature = "|".join(
                to_text(item.get("_id") or item.get("id"))
                for item in page_entries
            )

            if signature and signature in seen:
                raise GseError("Clockify repitió una página.")

            seen.add(signature)

            for item in page_entries:
                record = read_report_entry(item, self._timezone)
                entries[record.record_id] = record

            if len(page_entries) < REPORT_PAGE_SIZE:
                return list(entries.values())

            self._sleep(REPORT_PAUSE_SECONDS)

        raise GseError("Demasiadas páginas. No se guardaron totales parciales.")


def build_payload(
    month: str,
    ids: list[str] | None,
    page: int,
    timezone_name: str,
) -> JsonObject:
    """Cuerpo del reporte detallado del mes completo."""
    year, month_number = int(month[:4]), int(month[5:])
    last_day = calendar.monthrange(year, month_number)[1]
    payload: JsonObject = {
        "dateRangeStart": f"{month}-01T00:00:00.000",
        "dateRangeEnd": f"{month}-{last_day:02d}T23:59:59.999",
        "timeZone": timezone_name,
        "amountShown": "HIDE_AMOUNT",
        "dateRangeType": "ABSOLUTE",
        "detailedFilter": {
            "page": page,
            "pageSize": REPORT_PAGE_SIZE,
            "sortColumn": "ID",
        },
        "sortOrder": "ASCENDING",
        "rounding": False,
        "exportType": "JSON",
    }

    if ids:
        payload["users"] = {"ids": ids, "contains": "CONTAINS"}

    return payload


def raise_for_report_status(status_code: int, month: str) -> None:
    """
    Traduce un estatus de error del reporte.

    Raises:
        GseError: Cuando Clockify no devolvio el reporte.
    """
    if status_code < SUCCESS_STATUS_LIMIT:
        return

    advice = (
        "La clave no tiene permiso para este reporte global. Puedes "
        "consultar la base en Sheets."
        if status_code == FORBIDDEN_STATUS
        else "Revisa la conexión o la respuesta del servicio."
    )

    raise GseError(
        f"Clockify HTTP {status_code} al consultar {month}. {advice} "
        "No se guardaron totales parciales.",
    )


def read_page_entries(response: Any) -> list[JsonObject]:
    """
    Lista timeentries de una pagina del reporte.

    Raises:
        GseError: Cuando la respuesta no trae la lista.
    """
    try:
        data = response.json()
    except ValueError as error:
        raise GseError("Clockify no devolvio JSON valido.") from error

    entries = data.get("timeentries") if isinstance(data, dict) else None

    if not isinstance(entries, list):
        raise GseError("Respuesta Clockify sin timeentries.")

    return entries


def read_report_entry(
    item: Mapping[str, Any],
    timezone_name: str,
) -> HourRecord:
    """
    Convierte un registro del reporte.

    Raises:
        GseError: Cuando el registro no trae ID o duracion.
    """
    entry_id = to_text(item.get("_id") or item.get("id"))

    if not entry_id:
        raise GseError("Registro sin ID.")

    interval = item.get("timeInterval") or {}

    if interval.get("duration") is None:
        raise GseError("Registro sin duración.")

    return HourRecord(
        record_id=entry_id,
        user_id=named_value(item, "userId", "user", "id"),
        resource=named_value(item, "userName", "user", "name"),
        project=named_value(item, "projectName", "project", "name"),
        task=named_value(item, "taskName", "task", "name"),
        tags=[read_tag(tag) for tag in item.get("tags") or []],
        billable=bool(item.get("billable")),
        day=read_local_day(interval.get("start"), timezone_name),
        hours=parse_duration_hours(interval["duration"], entry_id),
    )


def named_value(
    item: Mapping[str, Any],
    direct_key: str,
    nested_key: str,
    nested_field: str,
) -> str:
    """Valor directo o del objeto anidado, como a||(b&&b.c)||''."""
    direct = item.get(direct_key)

    if direct:
        return to_text(direct)

    nested = item.get(nested_key)

    if isinstance(nested, Mapping) and nested.get(nested_field):
        return to_text(nested[nested_field])

    return ""


def read_tag(tag: object) -> str:
    """Nombre de una etiqueta (objeto con name o texto)."""
    if isinstance(tag, Mapping):
        return to_text(tag.get("name") or "")

    if isinstance(tag, str | int | float | bool):
        return to_text(tag)

    return ""


def read_local_day(start: object, timezone_name: str) -> str:
    """Dia local (YYYY-MM-DD) del inicio del registro; vacio si no hay."""
    if not start:
        return ""

    moment = datetime.fromisoformat(str(start))

    return moment.astimezone(ZoneInfo(timezone_name)).strftime("%Y-%m-%d")
