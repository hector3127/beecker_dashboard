"""File cache compatible with concurrent Windows readers."""

import errno
import logging
from typing import Any

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.filebased import FileBasedCache

logger = logging.getLogger(__name__)


def _unavailable_file(error: PermissionError) -> bool:
    """Recognize OS access failures, including reads without winerror."""
    return error.errno == errno.EACCES or getattr(error, "winerror", None) in (
        32,
        33,
    )


class ConcurrentFileBasedCache(FileBasedCache):
    """Defer cleanup of locked expired files instead of failing reads."""

    def get(
        self, key: str, default: Any = None, version: int | None = None
    ) -> Any:
        """Treat an inaccessible cache file as a miss, never as source data."""
        try:
            return super().get(key, default, version)
        except PermissionError as error:
            if not _unavailable_file(error):
                raise
            logger.warning("Cache read unavailable; using fallback: %s", error)
            return default

    def has_key(self, key: str, version: int | None = None) -> bool:
        """Report an inaccessible entry as unavailable."""
        try:
            return super().has_key(key, version)
        except PermissionError as error:
            if not _unavailable_file(error):
                raise
            logger.warning("Cache check unavailable: %s", error)
            return False

    def set(
        self,
        key: str,
        value: Any,
        timeout: float | None = DEFAULT_TIMEOUT,
        version: int | None = None,
    ) -> Any:
        """Keep calculated responses usable if a cache write is denied."""
        try:
            return super().set(key, value, timeout, version)
        except PermissionError as error:
            if not _unavailable_file(error):
                raise
            logger.warning("Cache write skipped: %s", error)
            return False

    def _delete(self, fname: str) -> bool:
        try:
            return bool(super()._delete(fname))  # type: ignore[misc]
        except PermissionError as exc:
            # Windows cannot unlink a file while another request has it open.
            # Django still treats the expired entry as a miss; later writes or
            # culling can replace/remove it once that reader closes the file.
            if _unavailable_file(exc):
                logger.warning("Cache cleanup deferred: %s", exc)
                return False
            raise
