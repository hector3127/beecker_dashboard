from core import throttled_cache
from core.throttled_cache import ThrottledCullFileCache


def build(tmp_path, max_entries=5):
    return ThrottledCullFileCache(
        str(tmp_path),
        {"OPTIONS": {"MAX_ENTRIES": max_entries, "CULL_FREQUENCY": 2}},
    )


def test_the_directory_is_only_listed_every_cull_every_writes(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(throttled_cache, "CULL_EVERY", 10)
    cache = build(tmp_path)
    cache._writes_since_cull = 10
    listings = []
    original = cache._list_cache_files
    cache._list_cache_files = lambda: listings.append(1) or original()

    for number in range(25):
        cache.set(f"k{number}", number)

    # Primera escritura (revisa), la 11 y la 21: tres revisiones, no 25.
    assert len(listings) == 3


def test_the_cache_still_returns_what_was_stored_and_gets_culled(tmp_path):
    cache = build(tmp_path, max_entries=5)

    for number in range(8):
        cache.set(f"k{number}", number)

    # Una sola revision (la primera): la cache puede pasar de MAX_ENTRIES.
    assert cache.get("k7") == 7
    assert cache.get("nunca") is None


def test_it_is_the_concurrent_cache_the_project_already_relies_on(tmp_path):
    from core.cache import ConcurrentFileBasedCache

    assert isinstance(build(tmp_path), ConcurrentFileBasedCache)
