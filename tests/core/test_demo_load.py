"""La herramienta de carga permanece local, acotada y sin redirecciones."""

from unittest.mock import Mock

import pytest

from scripts import check_load


@pytest.mark.parametrize(
    "url,requests,workers",
    [
        ("https://example.com/api", 40, 4),
        ("file:///tmp/data", 40, 4),
        ("http://user:pass@localhost/api", 40, 4),
        ("http://localhost/api", 0, 4),
        ("http://localhost/api", 1001, 4),
        ("http://localhost/api", 40, 0),
        ("http://localhost/api", 40, 33),
    ],
)
def test_refuses_unsafe_targets_before_any_request(
    monkeypatch, url, requests, workers
):
    network = Mock(side_effect=AssertionError("Unexpected network"))
    monkeypatch.setattr(check_load, "build_opener", network)
    with pytest.raises(ValueError):
        check_load.run_load(url, requests, workers)
    network.assert_not_called()


def test_redirect_is_never_followed():
    assert (
        check_load.NoRedirect().redirect_request(
            None, None, 302, "", {}, "https://example.com/"
        )
        is None
    )
