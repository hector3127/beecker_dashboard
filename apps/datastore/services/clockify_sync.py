"""Descarga meses completos del workspace de Clockify a la base diaria."""

import calendar
import logging
import time
from collections.abc import Callable, Iterable
from datetime import date, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from apps.clockify.constants import (
    FORBIDDEN_STATUS,
    REPORT_TIMEZONE,
    SUCCESS_STATUS_LIMIT,
)
from apps.clockify.exceptions import (
    ClockifyReportForbiddenError,
    ClockifyRequestError,
)
from apps.clockify.services.clockify_client import ClockifyClient
from apps.clockify.services.duration_parser import parse_duration_hours
from apps.clockify.services.report_mapper import (
    parse_entry_day,
    read_tag_names,
    read_task_id,
    read_task_name,
)
from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry, SyncRun
from core.utils.text import to_text

"""BKD.130.003 - Sincronizacion de Clockify
Un solo reporte detallado de todo el workspace por mes (1,000 registros
por pagina, el maximo de Clockify) en lugar de un reporte por proyecto.
Cada mes se reemplaza completo dentro de una transaccion: las paginas
siguen leyendo el mes anterior hasta que termina.
"""

logger = logging.getLogger(__name__)

JsonObject = dict[str, Any]

PAGE_SIZE = 1000
MAX_PAGES = 200
PAGE_PAUSE_SECONDS = 0.25
# Clockify bloquea los registros con mas de 8 dias; 10 da margen.
OPEN_WINDOW_DAYS = 10
INSERT_BATCH_SIZE = 2000


def window_months(today: date) -> list[date]:
    """
    Meses que aun pueden cambiar: los de los ultimos dias abiertos.

    Args:
        today: Fecha local de hoy.

    Returns:
        Primer dia de cada mes, del mas antiguo al actual.
    """
    first = (today - timedelta(days=OPEN_WINDOW_DAYS)).replace(day=1)
    return month_range(first, today.replace(day=1))


def month_range(first: date, last: date) -> list[date]:
    """
    Primer dia de cada mes entre dos meses, ambos incluidos.

    Args:
        first: Mes inicial (cualquier dia).
        last: Mes final (cualquier dia).

    Returns:
        Los meses en orden.
    """
    months: list[date] = []
    month = first.replace(day=1)
    while month <= last:
        months.append(month)
        month = (month + timedelta(days=32)).replace(day=1)
    return months


def build_month_payload(month: date, page: int) -> JsonObject:
    """
    Cuerpo del reporte detallado de todo el workspace para un mes.

    Args:
        month: Primer dia del mes.
        page: Pagina solicitada (base 1).

    Returns:
        El cuerpo JSON de la peticion.
    """
    last_day = calendar.monthrange(month.year, month.month)[1]
    return {
        "dateRangeStart": f"{month.isoformat()}T00:00:00.000",
        "dateRangeEnd": f"{month.replace(day=last_day).isoformat()}"
        "T23:59:59.999",
        "timeZone": REPORT_TIMEZONE,
        "amountShown": "HIDE_AMOUNT",
        "dateRangeType": "ABSOLUTE",
        "detailedFilter": {
            "page": page,
            "pageSize": PAGE_SIZE,
            "sortColumn": "ID",
        },
        "sortOrder": "ASCENDING",
        "rounding": False,
        "exportType": "JSON",
    }


def download_month(
    client: ClockifyClient,
    workspace_id: str,
    month: date,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[list[JsonObject], int]:
    """
    Descarga todas las paginas del reporte de un mes.

    Args:
        client: Cliente de Clockify.
        workspace_id: ID del workspace.
        month: Primer dia del mes.
        sleep: Pausa entre paginas (inyectable en pruebas).

    Returns:
        Los registros sin duplicados y el numero de solicitudes.

    Raises:
        ClockifyRequestError: Cuando Clockify falla; nunca se regresa un
            mes incompleto.
    """
    entries: dict[str, JsonObject] = {}
    signatures: set[str] = set()

    for page in range(1, MAX_PAGES + 1):
        if page > 1:
            sleep(PAGE_PAUSE_SECONDS)
        response = client.post_workspace_report(
            workspace_id, build_month_payload(month, page)
        )
        if response.status_code == FORBIDDEN_STATUS:
            raise ClockifyReportForbiddenError(
                "La API key no tiene permiso para el reporte del workspace.",
                status_code=response.status_code,
            )
        if response.status_code >= SUCCESS_STATUS_LIMIT:
            raise ClockifyRequestError(
                f"Clockify respondio {response.status_code} al descargar "
                f"{month:%Y-%m}, pagina {page}. No se guardo el mes.",
                status_code=response.status_code,
            )
        payload = response.json()
        rows = payload.get("timeentries") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ClockifyRequestError(
                "Formato de reporte no reconocido: falta timeentries.",
            )
        signature = "|".join(to_text(r.get("_id") or r.get("id")) for r in rows)
        if rows and signature in signatures:
            raise ClockifyRequestError(
                "Clockify repitio una pagina del reporte. No se guardo el mes.",
            )
        signatures.add(signature)
        for row in rows:
            entry_id = to_text(row.get("_id") or row.get("id"))
            if not entry_id:
                raise ClockifyRequestError(
                    "Registro sin ID en el reporte de Clockify.",
                )
            entries[entry_id] = row
        if len(rows) < PAGE_SIZE:
            return list(entries.values()), page

    raise ClockifyRequestError(
        f"{month:%Y-%m} supera {MAX_PAGES} paginas. No se guardo el mes.",
    )


def build_entry(
    row: JsonObject, month: date, tz: ZoneInfo
) -> ClockifyTimeEntry:
    """
    Convierte un registro del reporte a una fila de la base.

    Args:
        row: Registro del reporte detallado.
        month: Mes descargado (se usa si el registro no trae inicio).
        tz: Zona horaria del reporte.

    Returns:
        La fila sin guardar.
    """
    entry_id = to_text(row.get("_id") or row.get("id"))
    interval = row.get("timeInterval") or {}
    project = row.get("project") or {}
    user = row.get("user") or {}
    day = parse_entry_day(interval.get("start"), tz)
    hours = parse_duration_hours(interval.get("duration"), entry_id)
    return ClockifyTimeEntry(
        entry_id=entry_id,
        project_id=to_text(
            row.get("projectId") or project.get("id") or project.get("_id")
        ),
        project_name=to_text(row.get("projectName") or project.get("name")),
        task_id=read_task_id(row),
        task_name=read_task_name(row),
        user_id=to_text(row.get("userId") or user.get("id")),
        user_name=to_text(row.get("userName") or user.get("name")),
        tags=list(read_tag_names(row.get("tags"))),
        description=to_text(row.get("description")),
        billable=bool(row.get("billable")),
        start=to_text(interval.get("start")),
        end=to_text(interval.get("end")),
        entry_date=day.date() if day else None,
        month=day.date().replace(day=1) if day else month,
        duration_seconds=round(hours * 3600),
    )


def save_month(
    month: date,
    rows: Iterable[JsonObject],
    run: SyncRun,
) -> int:
    """
    Reemplaza un mes completo en una sola transaccion.

    Los registros cuyo inicio cae en otro mes se dejan para ese mes.

    Args:
        month: Primer dia del mes.
        rows: Registros del reporte.
        run: Corrida que hace el cambio.

    Returns:
        Registros guardados.
    """
    tz = ZoneInfo(REPORT_TIMEZONE)
    entries = [
        entry
        for entry in (build_entry(row, month, tz) for row in rows)
        if entry.month == month
    ]
    with transaction.atomic():
        ClockifyTimeEntry.objects.filter(month=month).delete()
        ClockifyTimeEntry.objects.bulk_create(
            entries, batch_size=INSERT_BATCH_SIZE, ignore_conflicts=True
        )
        ClockifyMonthSync.objects.update_or_create(
            month=month,
            defaults={
                "entries_count": len(entries),
                "total_seconds": sum(e.duration_seconds for e in entries),
                "synced_at": timezone.now(),
                "run": run,
            },
        )
    return len(entries)


def sync_months(
    months: list[date],
    client: ClockifyClient,
    workspace_id: str,
    kind: str,
    sleep: Callable[[float], None] = time.sleep,
) -> SyncRun:
    """
    Descarga y guarda varios meses; un mes con error no borra los demas.

    Args:
        months: Primer dia de cada mes.
        client: Cliente de Clockify.
        workspace_id: ID del workspace.
        kind: Tipo de corrida (daily, backfill, manual_month).
        sleep: Pausa entre paginas.

    Returns:
        La corrida con su resultado.
    """
    run = SyncRun.objects.create(kind=kind)
    errors: list[str] = []
    for month in months:
        try:
            rows, requests = download_month(client, workspace_id, month, sleep)
            run.entries += save_month(month, rows, run)
            run.requests += requests
            run.months.append(month.strftime("%Y-%m"))
            logger.info(
                "Clockify %s: %d registros", f"{month:%Y-%m}", len(rows)
            )
        except ClockifyRequestError as error:
            errors.append(f"{month:%Y-%m}: {error}")
            logger.warning("Clockify %s fallo: %s", f"{month:%Y-%m}", error)
    run.status = "failed" if errors else "ok"
    run.error = "\n".join(errors)
    run.finished_at = timezone.now()
    run.save()
    return run
