"""Las páginas modulares mantienen autorización y contexto de Facturabilidad."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from apps.access.scope import AccessScope
from apps.portal.services.facturability_loader import MonthSources
from tests.portal.test_views import facturable_gse, stub_facturability

pytestmark = pytest.mark.django_db
SCREENS = [
    ("", "billability"),
    ("especialidad/", "billability_specialty"),
    ("recurso/", "billability_resource"),
]
BASE = "/operativa/facturabilidad/"


def test_annual_specialty_groups_hours_and_includes_lab_ia(client, monkeypatch):
    def month_sources(month):
        number = int(month[-2:])
        if number >= 9:
            return MonthSources(month=month, error="Sin cobertura")
        return MonthSources(
            month=month,
            gse=facturable_gse(
                ("Ana", "R&D", "AER", 10 * number),
                ("Ana", "R&D", "IXB", 5 * number),
                ("Eva", "DEV", "IXB", 40),
                ("Dan", "DM", "IXB", 50),
            ),
        )

    load = Mock(side_effect=month_sources)
    monkeypatch.setattr("apps.portal.views.load_month_sources", load)
    path = BASE + "especialidad/"
    query = {"periodo": "anio", "anio": "2025"}
    response = client.get(path, query)
    assert response.status_code == 200
    assert load.call_count == 12
    lab = next(
        row
        for row in response.context["quarterly_specialties"]
        if row["name"] == "Lab IA"
    )
    assert [row.fixed_hours if row else None for row in lab["quarters"]] == [
        60,
        150,
        150,
        None,
    ]
    assert [row.variable_hours if row else None for row in lab["quarters"]] == [
        30,
        75,
        75,
        None,
    ]
    assert [q["partial"] for q in response.context["specialty_quarters"]] == [
        False,
        False,
        True,
        False,
    ]
    assert response.context["specialty_quarters"][3]["total"] is None
    assert [
        row["name"] for row in response.context["quarterly_specialties"]
    ] == ["Dev", "Lab IA"]
    assert b"Q3*" in response.content

    filtered = client.get(path, {**query, "roles": "1", "rol": "R&D"})
    assert [
        row["name"] for row in filtered.context["quarterly_specialties"]
    ] == ["Lab IA"]
    monthly = client.get(path, {"mes": "2025-02"})
    assert {row.name for row in monthly.context["specialties"]} == {
        "Dev",
        "Lab IA",
    }
    assert not monthly.context["specialty_quarters"]


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
