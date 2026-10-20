"""Bounded background refreshes for the local executive dashboard."""

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextvars import copy_context
from typing import Any

from django.core.cache import cache
from django.db import close_old_connections
from django.test import RequestFactory

from apps.portal.services.executive_period import cache_suffix, query_string

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(
    max_workers=1, thread_name_prefix="executive-refresh"
)
_lock = threading.Lock()
_pending: set[str] = set()
STATUS_SECONDS = 3600
MAX_PENDING = 2


def status_key() -> str:
    """Keep status separate for each selected period."""
    return "portal:executive-refresh:v1" + cache_suffix()


def refresh_status() -> dict[str, Any]:
    """Read status without consulting any external source."""
    return cache.get(status_key()) or {"state": "idle"}


def request_refresh(force: bool = False) -> dict[str, Any]:
    """Coalesce duplicate requests and limit queued work in this process."""
    key = status_key()
    query = query_string()
    if force:
        query += ("&" if query else "") + "forzar_fuentes=1"
    with _lock:
        if key in _pending:
            return refresh_status()
        if len(_pending) >= MAX_PENDING:
            return {"state": "busy"}
        _pending.add(key)
        try:
            cache.set(key, {"state": "queued"}, STATUS_SECONDS)
            _executor.submit(copy_context().run, _run, key, query)
        except RuntimeError:
            # A server reload can stop its executor while a page is rendering.
            # Preserve the available page instead of turning a warm-up into HTTP 500.
            _pending.discard(key)
            cache.set(key, {"state": "failed"}, STATUS_SECONDS)
            logger.warning(
                "La precarga no pudo iniciarse durante el reinicio del servidor"
            )
            return {"state": "failed"}
        except Exception:
            _pending.discard(key)
            cache.set(key, {"state": "failed"}, STATUS_SECONDS)
            raise
    return refresh_status()


def _run(key: str, query: str) -> None:
    """Prepare a new cut, preserving existing valid snapshots on failures."""
    from urllib.parse import parse_qs
    from core.utils.source_refresh import force_sources

    force_token = force_sources.set(
        parse_qs(query).get("forzar_fuentes") == ["1"]
    )
    started = time.perf_counter()
    try:
        close_old_connections()
        cache.set(key, {"state": "running"}, STATUS_SECONDS)
        partial = _prepare(query)
        cache.set(key, {"state": "ready", "partial": partial}, STATUS_SECONDS)
    except Exception:
        logger.exception("No se pudo actualizar Ejecutiva en segundo plano")
        cache.set(key, {"state": "failed"}, STATUS_SECONDS)
    finally:
        force_sources.reset(force_token)
        try:
            close_old_connections()
        finally:
            with _lock:
                _pending.discard(key)
            logger.info(
                "Actualizacion ejecutiva %s: %.1f s",
                key,
                time.perf_counter() - started,
            )


def _prepare(query: str) -> bool:
    """Reuse financial/Operations caches, then prepare the page context."""
    from apps.portal import views
    from apps.portal.services.executive_commercial import (
        warm_commercial_summary,
    )
    from apps.portal.services.executive_operations import warm_operations
    from apps.portal.services.financial_cache import warm_financial

    from core.utils.source_refresh import force_sources

    if force_sources.get():
        from django.conf import settings
        from core.sheets.read_cache import SheetReadCache
        from apps.clockify.provider import (
            build_cache_prefix,
            read_clockify_settings,
        )

        cache.delete(
            build_cache_prefix(*read_clockify_settings()) + ":projects"
        )
        sheets = SheetReadCache(
            settings.GOOGLE_SPREADSHEET_ID, settings.SHEETS_READ_CACHE_SECONDS
        )
        for name in [
            "DataRevenue",
            "Backlog_Proyectos",
            "Bandas/rol",
            "Master rates",
            "MPB",
            "Historico_Proyectos",
            "Proyectos",
            "Recursos",
            "Clockify_Vinculos",
        ]:
            sheets.invalidate_values(name)
    partial = False
    for task in (warm_financial, warm_operations):
        result = task(only_stale=not force_sources.get())
        partial = not result.get("ok", False) or partial
    partial = not warm_commercial_summary().get("ok", False) or partial
    request = RequestFactory().get("/?actualizar=1&" + query)
    # No user data or session is retained by the worker.
    request.__dict__["portal_warmer"] = True
    from django.contrib.auth.models import User

    request.user = User(username="cache-warmer")
    # Call the internal context builder using the same trusted warmer path.
    response = views.ejecutiva(request)
    if response.status_code != 200:
        raise ValueError("No se pudo preparar la pagina ejecutiva")
    return partial or b'data-portal-ready="false"' in response.content
