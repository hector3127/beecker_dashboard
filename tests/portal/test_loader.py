"""Carga del portafolio: cache corta y errores controlados."""

import pytest
from django.core.cache import cache

from apps.portal.constants import PORTFOLIO_CACHE_KEY
from apps.portal.services import portfolio_loader
from core.exceptions import ConfigurationError
from tests.portal.builders import make_project


@pytest.fixture(autouse=True)
def clean_cache():
    cache.delete(PORTFOLIO_CACHE_KEY)
    yield
    cache.delete(PORTFOLIO_CACHE_KEY)


def stub_sources(monkeypatch, calls):
    monkeypatch.setattr(
        portfolio_loader,
        "build_sheet_repository",
        lambda: object(),
    )
    monkeypatch.setattr(
        portfolio_loader,
        "build_time_entry_provider",
        lambda repository: object(),
    )

    def fake_build(reader, provider, now):
        calls.append(now)
        return (make_project(),)

    monkeypatch.setattr(portfolio_loader, "build_project_views", fake_build)


def test_loads_projects_and_reuses_the_cache(monkeypatch):
    calls = []
    stub_sources(monkeypatch, calls)

    first = portfolio_loader.load_portfolio()
    second = portfolio_loader.load_portfolio()

    assert first.error == ""
    assert [item.project_id for item in first.projects] == ["P-1"]
    assert second.projects == first.projects
    assert len(calls) == 1
    assert calls[0].tzinfo is None


def test_missing_configuration_returns_message_and_is_not_cached(monkeypatch):
    def broken():
        raise ConfigurationError("Define GOOGLE_SPREADSHEET_ID.")

    monkeypatch.setattr(portfolio_loader, "build_sheet_repository", broken)

    result = portfolio_loader.load_portfolio()

    assert result.projects == ()
    assert "Falta configurar el dashboard." in result.error
    assert "GOOGLE_SPREADSHEET_ID" in result.error
    assert cache.get(PORTFOLIO_CACHE_KEY) is None
