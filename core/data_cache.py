"""Namespace source-derived caches by committed DB generation per request.

No cache deletion, TTL shortcut or network access. Authentication, locks,
configuration and refresh-job status retain their original keys.
"""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from django.conf import settings
from django.core.cache.backends.base import default_key_func
from django.db.models import F
from django.http import HttpRequest, HttpResponse

_revision: ContextVar[str | None] = ContextVar(
    "source_cache_revision", default=None
)
PREFIXES = (
    "portal:",
    "dashboard:",
    "ejecutivo:",
    "clockify:",
    "gse:result:",
    "ixs_panel_azure_",
    "ixs_raid_lastok_",
    "azure:v1:",
)


def enabled() -> bool:
    """Enable generations only when at least one persistent source is active."""
    return any(
        getattr(settings, k, False)
        for k in (
            "CLOCKIFY_STORE_ENABLED",
            "AZURE_STORE_ENABLED",
            "SHEETS_STORE_ENABLED",
        )
    )


def read_revision() -> str:
    """Read the committed generation and the active source modes."""
    from apps.datastore.models import DataRevision

    value = (
        DataRevision.objects.filter(pk=1)
        .values_list("version", flat=True)
        .first()
    )
    modes = "".join(
        str(int(bool(getattr(settings, k, False))))
        for k in (
            "CLOCKIFY_STORE_ENABLED",
            "AZURE_STORE_ENABLED",
            "SHEETS_STORE_ENABLED",
        )
    )
    return f"{modes}:{value or 0}"


def bump_revision() -> None:
    """Must run inside the transaction that publishes changed source rows."""
    from apps.datastore.models import DataRevision

    DataRevision.objects.get_or_create(pk=1)
    DataRevision.objects.filter(pk=1).update(version=F("version") + 1)


@contextmanager
def revision_scope() -> Iterator[None]:
    """Pin cache writes to the starting generation, including worker threads."""
    token = _revision.set(read_revision() if enabled() else "")
    try:
        yield
    finally:
        _revision.reset(token)


def make_key(key: str, key_prefix: str, version: int) -> str:
    """Version derived results without changing sessions or job status."""
    if (
        enabled()
        and str(key).startswith(PREFIXES)
        and not str(key).startswith("portal:executive-refresh:")
    ):
        from core.utils.source_refresh import force_sources

        generation = _revision.get()
        if generation is None:
            generation = read_revision()
        mode = "live" if force_sources.get() else "stored"
        key = f"sources:{generation}:{mode}:{key}"
    return default_key_func(key, key_prefix, version)


class SourceCacheMiddleware:
    """One revision lookup per request; no worker-local stale value."""

    def __init__(
        self, get_response: Callable[[HttpRequest], HttpResponse]
    ) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Share a generation with all computations of the request."""
        with revision_scope():
            return self.get_response(request)
