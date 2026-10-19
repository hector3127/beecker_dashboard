"""Regression coverage for concurrent expiration on Windows."""

import errno
from unittest.mock import patch

import pytest

from core.cache import ConcurrentFileBasedCache


def test_locked_expired_entry_is_a_miss_and_can_be_replaced(tmp_path):
    cache = ConcurrentFileBasedCache(str(tmp_path), {})
    cache.set("expired", "old", timeout=-1)
    locked = PermissionError("File used by another process")
    locked.winerror = 32
    with patch("os.remove", side_effect=locked):
        assert cache.get("expired", "missing") == "missing"
        assert not cache.has_key("expired")
    cache.set("expired", "new")
    assert cache.get("expired") == "new"


def test_actual_permission_error_is_not_hidden(tmp_path):
    cache = ConcurrentFileBasedCache(str(tmp_path), {})
    cache.set("expired", "old", timeout=-1)
    with patch("os.remove", side_effect=PermissionError("Access denied")):
        with pytest.raises(PermissionError, match="Access denied"):
            cache.get("expired")


def test_permission_denied_during_pickle_read_returns_default(tmp_path, caplog):
    cache = ConcurrentFileBasedCache(str(tmp_path), {})
    cache.set("metadata", {"p1": 100})
    with patch(
        "django.core.cache.backends.filebased.pickle.load",
        side_effect=PermissionError(errno.EACCES, "Permission denied"),
    ):
        assert cache.get("metadata", "missing") == "missing"
        assert not cache.has_key("metadata")
    assert "Cache read unavailable" in caplog.text
    assert cache.get("metadata") == {"p1": 100}


def test_locked_file_open_and_write_do_not_interrupt_response(tmp_path):
    cache = ConcurrentFileBasedCache(str(tmp_path), {})
    denied = PermissionError(errno.EACCES, "Permission denied")
    with patch("builtins.open", side_effect=denied):
        assert cache.get("locked", "missing") == "missing"
    with patch(
        "django.core.cache.backends.filebased.file_move_safe",
        side_effect=denied,
    ):
        assert cache.set("locked", 123) is False
    cache.set("locked", 456)
    with patch("os.remove", side_effect=denied):
        assert cache.delete("locked") is False
    assert cache.get("locked") == 456
