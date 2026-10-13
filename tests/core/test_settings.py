import os
import subprocess
import sys

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.settings.base import BASE_DIR, read_int_env


def test_sheets_cache_can_be_disabled_at_startup():
    environment = {
        **os.environ,
        "DJANGO_SETTINGS_MODULE": "config.settings.local",
        "SHEETS_READ_CACHE_SECONDS": "0",
    }
    result = subprocess.run(
        [sys.executable, "manage.py", "check"],
        cwd=BASE_DIR,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("value", ["-1", "incorrecto"])
def test_cache_duration_rejects_invalid_values(monkeypatch, value):
    monkeypatch.setenv("SHEETS_READ_CACHE_SECONDS", value)
    with pytest.raises(ImproperlyConfigured):
        read_int_env("SHEETS_READ_CACHE_SECONDS", 900, allow_zero=True)


def test_other_durations_still_require_positive_values(monkeypatch):
    monkeypatch.setenv("DASHBOARD_CACHE_TTL_SECONDS", "0")
    with pytest.raises(ImproperlyConfigured):
        read_int_env("DASHBOARD_CACHE_TTL_SECONDS", 360)
