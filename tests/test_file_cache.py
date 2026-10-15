"""Regression coverage for concurrent expiration on Windows."""

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
