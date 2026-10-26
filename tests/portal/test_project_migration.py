"""Proyecto simple: contexto, acceso por cuenta y enlaces obsoletos."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from apps.access.scope import AccessScope
from apps.portal.services.project_loader import ProjectDashboardLoad
from tests.portal.test_views import portfolio, stub_portfolio, stub_project

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("previous", [False, True])
def test_template_and_context(client, monkeypatch, previous):
    stub_portfolio(monkeypatch, portfolio())
    stub_project(monkeypatch)
    response = client.get(
        "/proyecto/3/", {"vista": "anterior"} if previous else {}
    )
    assert "pages/project.html" in [t.name for t in response.templates]
    assert response.context["page"].name == "HIS"
    if not previous:
        html = response.content.decode()
        assert "app/scripts/pages/project/main.js" in html
        assert "app/styles/pages/project.css" in html
        source = Path("frontend/templates/pages/project.html").read_text(
            encoding="utf-8"
        )
        assert 'style="' not in source
        assert "<style" not in source
        assert "onclick=" not in source


@pytest.mark.parametrize("grant", ["anonymous", "wrong", "foreign", "own"])
def test_access(client, enforced, monkeypatch, grant):
    stub_portfolio(monkeypatch, portfolio())
    detail = Mock(return_value=ProjectDashboardLoad(data={}, error=""))
    monkeypatch.setattr("apps.portal.views.load_project_dashboard", detail)
    enforced(
        "Ana",
        caps=frozenset(
            {"view_costs"} if grant == "wrong" else {"view_operations"}
        ),
        scope=AccessScope.limited(accounts=["ACME"]),
    )
    if grant == "anonymous":
        client.logout()
    response = client.get(
        "/proyecto/2/" if grant == "foreign" else "/proyecto/1/"
    )
    assert (
        response.status_code
        == {"anonymous": 302, "wrong": 403, "foreign": 404, "own": 200}[grant]
    )
    if grant == "own":
        detail.assert_called_once_with("1")
    else:
        detail.assert_not_called()


def test_retired_option_keeps_current_page_and_is_read_only(
    client, monkeypatch
):
    stub_portfolio(monkeypatch, portfolio())
    stub_project(monkeypatch)
    response = client.get("/proyecto/1/?vista=anterior")
    assert "pages/project.html" in [t.name for t in response.templates]
    assert client.post("/proyecto/1/").status_code == 405
