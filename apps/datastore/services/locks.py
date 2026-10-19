"""Candados: un paso de la sincronizacion no corre dos veces a la vez."""

import os
import socket
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.datastore.models import SyncLock

"""BKD.130.013 - Candados de sincronizacion
Un programador de tareas lanza la siguiente ejecucion aunque la anterior no
haya terminado. Cada paso (hojas, azure, clockify, catalogos) toma un
candado en la base: si otra ejecucion lo tiene, esta se omite. Funciona
igual en SQLite y PostgreSQL (restriccion UNIQUE). Si un proceso muere sin
soltarlo, el candado vence solo despues de su plazo.
"""


def _holder() -> str:
    """Identifica a quien toma el candado (equipo, proceso y una marca)."""
    return f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:8]}"


def _acquire(name: str, ttl_seconds: int) -> str | None:
    """Toma el candado; devuelve quien lo tiene o None si esta ocupado."""
    holder = _holder()
    now = timezone.now()
    try:
        with transaction.atomic():
            SyncLock.objects.create(name=name, holder=holder, locked_at=now)
        return holder
    except IntegrityError:
        # Lo tiene otra ejecucion; solo se le quita si ya vencio. El filtro
        # y la actualizacion son una sola sentencia: gana una sola.
        expired = now - timedelta(seconds=ttl_seconds)
        taken = SyncLock.objects.filter(
            name=name, locked_at__lt=expired
        ).update(holder=holder, locked_at=now)
        return holder if taken else None


@contextmanager
def sync_lock(name: str, ttl_seconds: int) -> Iterator[bool]:
    """
    Toma el candado de un paso mientras dura el bloque.

    Args:
        name: Paso que se protege.
        ttl_seconds: Despues de este tiempo un candado se considera
            abandonado y otra ejecucion puede tomarlo.

    Yields:
        True si este proceso tiene el candado; False si lo tiene otro (el
        bloque debe omitir su trabajo).
    """
    holder = _acquire(name, ttl_seconds)
    try:
        yield holder is not None
    finally:
        if holder is not None:
            SyncLock.objects.filter(name=name, holder=holder).delete()
