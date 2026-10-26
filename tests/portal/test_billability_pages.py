"""Las páginas modulares mantienen autorización y contexto de Facturabilidad."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from apps.access.scope import AccessScope
from tests.portal.test_views import stub_facturability

pytestmark = pytest.mark.django_db
SCREENS = [
    ("", "billability"),
    ("especialidad/", "billability_specialty"),
    ("recurso/", "billability_resource"),
]
BASE = "/operativa/facturabilidad/"


@pytest.mark.parametrize(("suffix", "name"), SCREENS)
@pytest.mark.parametrize("previous", [False, True])
def test_active_template_has_separate_assets(
    client, monkeypatch, suffix, name, previous
):
    stub_facturability(monkeypatch)
    response = client.get(
        BASE + suffix,
        {"mes": "2026-02", **({"vista": "anterior"} if previous else {})},
    )
    assert response.status_code == 200
    assert f"pages/{name}.html" in [t.name for t in response.templates]
    html = response.content.decode()
    assert f"app/scripts/pages/{name}/main.js" in html
    assert f"app/styles/pages/{name}.css" in html
    source = Path(f"frontend/templates/pages/{name}.html").read_text(
        encoding="utf-8"
    )
    assert 'style="' not in source
    assert "<style" not in source
    assert "onclick=" not in source
    assert "portal/_period_picker.html" not in source


@pytest.mark.parametrize(("suffix", "name"), SCREENS)
@pytest.mark.parametrize("grant", ["anonymous", "limited", "wrong"])
@pytest.mark.parametrize("previous", [False, True])
def test_rejects_before_loading_sources(
    client, enforced, monkeypatch, suffix, name, grant, previous
):
    month = Mock(side_effect=AssertionError("Unexpected source read"))
    year = Mock(side_effect=AssertionError("Unexpected source read"))
    monkeypatch.setattr("apps.portal.views.load_month_sources", month)
    monkeypatch.setattr("apps.portal.views.load_year_sources", year)
    enforced(
        "Ana",
        caps=frozenset(
            {"view_costs"} if grant == "wrong" else {"view_operations"}
        ),
        scope=AccessScope.limited(accounts=["Acme"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()
    response = client.get(
        BASE + suffix, {"vista": "anterior"} if previous else {}
    )
    assert response.status_code in {302, 403}
    month.assert_not_called()
    year.assert_not_called()
