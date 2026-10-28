"""Cache identities remain portable without changing project identifiers."""

import warnings

import pytest
from django.core.cache.backends.base import (
    CacheKeyWarning,
    default_key_func,
    memcache_key_warnings,
)
from django.core.cache.backends.locmem import LocMemCache

from core import data_cache


@pytest.fixture
def scoped(settings, monkeypatch):
    settings.CLOCKIFY_STORE_ENABLED = True
    monkeypatch.setattr(data_cache, "read_revision", lambda: "111:685")
    return LocMemCache(
        "portable-source-keys", {"KEY_FUNCTION": data_cache.make_key}
    )


@pytest.mark.parametrize(
    "project",
    [
        "AIN.002 CR",
        "GPO.006_Bolsa Horas",
        "GPO.006_Bolsa de horas",
        "P\tCR",
        "P\nCR",
        "P\x00CR",
        "P\x7fCR",
        "Proyecto México",
        "P" * 500,
    ],
)
def test_report_keys_roundtrip_without_warnings(scoped, project):
    key = (
        f"clockify:v6:workspace:fingerprint:report:provider-id:{project}:"
        "2026-01-30:2026-02-26:cr-v32026-10-28T14:25:18.431444+00:00"
    )
    wire = scoped.make_key(key)
    assert wire.isascii() and len(wire.encode()) <= 250
    assert list(memcache_key_warnings(wire)) == []
    with warnings.catch_warnings():
        warnings.simplefilter("error", CacheKeyWarning)
        scoped.set(key, {"hours": 12.5})
        assert scoped.get(key) == {"hours": 12.5}
        scoped.delete(key)
        assert scoped.get(key) is None


def test_hash_preserves_spaces_prefix_and_version_as_distinct_identities(
    scoped,
):
    keys = [
        data_cache.make_key("clockify:AIN.002 CR", "tenant-a", 1),
        data_cache.make_key("clockify:AIN.002_CR", "tenant-a", 1),
        data_cache.make_key("clockify:AIN.002 CR", "tenant-b", 1),
        data_cache.make_key("clockify:AIN.002 CR", "tenant-a", 2),
        data_cache.make_key("clockify:AIN.002  CR", "tenant-a", 1),
    ]
    assert len(set(keys)) == len(keys)


def test_generation_and_live_mode_remain_isolated_after_hashing(
    scoped, monkeypatch
):
    from core.utils.source_refresh import force_sources

    key = "clockify:report:AIN.002 CR"
    scoped.set(key, "stored")
    token = force_sources.set(True)
    try:
        assert scoped.get(key) is None
        scoped.set(key, "live")
    finally:
        force_sources.reset(token)
    assert scoped.get(key) == "stored"
    monkeypatch.setattr(data_cache, "read_revision", lambda: "111:686")
    assert scoped.get(key) is None


def test_valid_configuration_and_job_keys_keep_their_original_identity(scoped):
    for key in (
        "daily:azure:active_project",
        "session:person",
        "portal:executive-refresh:v1",
    ):
        assert data_cache.make_key(key, "prefix", 1) == default_key_func(
            key, "prefix", 1
        )


def test_long_prefix_and_unicode_are_not_truncated(scoped):
    assert data_cache.make_key("key", "prefix" * 100, 1).startswith("sha256:")
    assert data_cache.make_key("é" * 150, "", 1).isascii()
    assert data_cache.make_key("x" * 500, "", 1) != data_cache.make_key(
        "x" * 499 + "y", "", 1
    )
