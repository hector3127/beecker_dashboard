"""Detecta cambios en meses antiguos de Clockify antes de sincronizar."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

from apps.clockify.constants import REPORT_TIMEZONE, SUCCESS_STATUS_LIMIT
from apps.clockify.exceptions import ClockifyRequestError
from apps.clockify.services.clockify_client import ClockifyClient
from apps.datastore.models import ClockifyMonthSync, SyncRun
from apps.datastore.services.clockify_sync import (
    OPEN_WINDOW_DAYS,
    build_month_payload,
    month_range,
    window_months,
)
from apps.datastore.services.retry import MAX_CONSECUTIVE_FAILURES, with_retries
from core.utils.text import to_text

"""BKD.130.006 - Deteccion de cambios en meses bloqueados
Clockify bloquea los registros con mas de 8 dias (lockTimeEntries), pero un
administrador puede desbloquear y editar meses antiguos. Dos revisiones:
1. La fecha de bloqueo: todo lo posterior a ella puede cambiar, asi que
   esos meses se vuelven a descargar.
2. Los totales de cada mes guardado contra el reporte resumido de Clockify
   (registros y segundos): el mes que no cuadra se vuelve a descargar. Esto
   tambien cubre una edicion hecha mientras estaba desbloqueado y que se
   bloqueo de nuevo antes de la siguiente corrida.
"""

logger = logging.getLogger(__name__)


@dataclass
class DailyPlan:
    """Meses que debe descargar la corrida y por que."""

    months: list[date]
    lock_seen: str | None = None
    notes: list[str] = field(default_factory=list)


def read_lock(
    client: ClockifyClient,
    workspace_id: str,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """
    Lee la fecha lockTimeEntries del workspace.

    Args:
        client: Cliente de Clockify.
        workspace_id: ID del workspace.
        sleep: Espera entre reintentos (se cambia en las pruebas).

    Returns:
        La fecha ISO 8601, cadena vacia si no hay bloqueo, o None si no
        se pudo consultar.
    """
    try:
        response = with_retries(
            lambda: client.get(f"/workspaces/{quote(workspace_id)}"), sleep
        )
    except ClockifyRequestError as error:
        logger.warning("No se pudo leer lockTimeEntries: %s", error)
        return None
    if response.status_code >= SUCCESS_STATUS_LIMIT:
        logger.warning("lockTimeEntries respondio %s", response.status_code)
        return None
    settings = response.json().get("workspaceSettings") or {}
    return to_text(settings.get("lockTimeEntries"))


def lock_day(lock_text: str) -> date | None:
    """
    Dia local (America/Mexico_City) hasta el que esta bloqueado Clockify.

    Args:
        lock_text: Fecha ISO 8601 de lockTimeEntries.

    Returns:
        El dia, o None si el texto no es una fecha valida.
    """
    try:
        moment = datetime.fromisoformat(lock_text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if moment.tzinfo is None:
        return moment.date()
    return moment.astimezone(ZoneInfo(REPORT_TIMEZONE)).date()


def months_open_by_lock(
    lock_text: str | None,
    today: date,
    synced: list[date],
) -> tuple[list[date], list[str]]:
    """
    Meses que pueden haber cambiado segun la fecha de bloqueo.

    Args:
        lock_text: Resultado de read_lock.
        today: Fecha local de hoy.
        synced: Meses ya guardados en la base.

    Returns:
        Los meses a descargar y las notas que explican por que.
    """
    window_start = today - timedelta(days=OPEN_WINDOW_DAYS)
    months = window_months(today)
    if lock_text is None:
        return months, ["No se pudo leer el bloqueo de Clockify."]
    if lock_text == "":
        extra = sorted(set(synced) | set(months))
        return extra, ["Clockify no tiene bloqueo: se revisan todos los meses."]
    locked_until = lock_day(lock_text)
    if locked_until is None or locked_until >= window_start:
        return months, []
    return (
        month_range(locked_until.replace(day=1), today.replace(day=1)),
        [
            f"Bloqueo en {locked_until}: se revisan los meses desde "
            f"{locked_until:%Y-%m}."
        ],
    )


def fetch_month_totals(
    client: ClockifyClient,
    workspace_id: str,
    month: date,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[int, int]:
    """
    Registros y segundos de un mes segun el reporte resumido.

    Args:
        client: Cliente de Clockify.
        workspace_id: ID del workspace.
        month: Primer dia del mes.
        sleep: Espera entre reintentos (se cambia en las pruebas).

    Returns:
        (registros, segundos).

    Raises:
        ClockifyRequestError: Cuando Clockify no responde bien.
    """
    payload = build_month_payload(month, 1)
    payload.pop("detailedFilter")
    payload.pop("sortOrder")
    payload["summaryFilter"] = {"groups": ["PROJECT"], "sortColumn": "GROUP"}
    response = with_retries(
        lambda: client.post_workspace_summary(workspace_id, payload), sleep
    )
    if response.status_code >= SUCCESS_STATUS_LIMIT:
        raise ClockifyRequestError(
            f"Clockify respondio {response.status_code} al resumir "
            f"{month:%Y-%m}.",
            status_code=response.status_code,
        )
    totals = response.json().get("totals") or [{}]
    first = totals[0] or {}
    return (
        int(first.get("entriesCount") or 0),
        int(first.get("totalTime") or 0),
    )


def find_changed_months(
    client: ClockifyClient,
    workspace_id: str,
    skip: set[date],
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[list[date], list[str]]:
    """
    Compara cada mes guardado con el reporte resumido de Clockify.

    Si la conexion falla varias veces seguidas se deja de verificar: la
    verificacion es opcional y no debe alargar la tarea cuando Clockify no
    responde. El siguiente dia se vuelve a intentar.

    Args:
        client: Cliente de Clockify.
        workspace_id: ID del workspace.
        skip: Meses que ya se van a descargar (no se comparan).
        sleep: Espera entre reintentos (se cambia en las pruebas).

    Returns:
        Los meses que no cuadran y las notas con los totales.
    """
    changed: list[date] = []
    notes: list[str] = []
    failures = 0
    for saved in ClockifyMonthSync.objects.order_by("month"):
        if saved.month in skip:
            continue
        try:
            count, seconds = fetch_month_totals(
                client, workspace_id, saved.month, sleep
            )
            failures = 0
        except ClockifyRequestError as error:
            notes.append(
                f"{saved.month:%Y-%m}: no se pudo verificar ({error})."
            )
            failures = failures + 1 if not error.status_code else 0
            if failures >= MAX_CONSECUTIVE_FAILURES:
                notes.append(
                    "Clockify no responde: se omite el resto de la "
                    "verificacion hasta la siguiente corrida."
                )
                break
            continue
        if (count, seconds) != (saved.entries_count, saved.total_seconds):
            changed.append(saved.month)
            notes.append(
                f"{saved.month:%Y-%m}: Clockify tiene {count} registros y "
                f"{seconds / 3600:,.2f} h; la base tenia "
                f"{saved.entries_count} y {saved.total_seconds / 3600:,.2f} h."
            )
    return changed, notes


def plan_daily(
    client: ClockifyClient,
    workspace_id: str,
    today: date,
    verify: bool = True,
) -> DailyPlan:
    """
    Decide que meses descargar en la corrida diaria.

    Args:
        client: Cliente de Clockify.
        workspace_id: ID del workspace.
        today: Fecha local de hoy.
        verify: Comparar los totales de los meses guardados.

    Returns:
        Los meses, la fecha de bloqueo vista y las notas.
    """
    synced = list(
        ClockifyMonthSync.objects.order_by("month").values_list(
            "month", flat=True
        )
    )
    lock_text = read_lock(client, workspace_id)
    months, notes = months_open_by_lock(lock_text, today, synced)
    previous = (
        SyncRun.objects.exclude(lock_seen=None)
        .order_by("-started_at", "-pk")
        .values_list("lock_seen", flat=True)
        .first()
    )
    if (
        lock_text
        and previous
        and (lock_day(lock_text) or today) < (lock_day(previous) or today)
    ):
        notes.append(
            f"El bloqueo retrocedio de {lock_day(previous)} a "
            f"{lock_day(lock_text)}."
        )
    if verify:
        changed, more = find_changed_months(client, workspace_id, set(months))
        months = sorted(set(months) | set(changed))
        notes.extend(more)
    return DailyPlan(months, lock_text, notes)
