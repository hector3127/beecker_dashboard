"""One bounded background worker; DB lock coordinates other processes."""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from django.db import close_old_connections

from apps.datastore.services.locks import sync_lock
from apps.portal.services.eva_native_sync import extract_eva

logger = logging.getLogger(__name__)
_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="eva-refresh")
_lock = threading.Lock()
_running = False


def request_refresh() -> bool:
    """Queue once per process; the worker also takes a durable source lock."""
    global _running
    with _lock:
        if _running:
            return False
        _running = True
    _executor.submit(_refresh)
    return True


def _refresh() -> None:
    global _running
    close_old_connections()
    try:
        with sync_lock("eva_native", 7200) as acquired:
            if acquired:
                extract_eva()
    except Exception:
        logger.exception(
            "Falló la extracción EVA; se conserva el corte anterior."
        )
    finally:
        close_old_connections()
        with _lock:
            _running = False
