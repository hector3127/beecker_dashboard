"""File cache compatible with concurrent Windows readers."""

from django.core.cache.backends.filebased import FileBasedCache


class ConcurrentFileBasedCache(FileBasedCache):
    """Defer cleanup of locked expired files instead of failing reads."""

    def _delete(self, fname: str) -> bool:
        try:
            return bool(super()._delete(fname))
        except PermissionError as exc:
            # Windows cannot unlink a file while another request has it open.
            # Django still treats the expired entry as a miss; later writes or
            # culling can replace/remove it once that reader closes the file.
            if getattr(exc, "winerror", None) in (32, 33):
                return False
            raise
