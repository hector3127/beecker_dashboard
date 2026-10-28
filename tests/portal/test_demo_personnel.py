"""Plantilla visible con estado explícito y población seleccionada."""

import pytest

from apps.portal.services.facturability_loader import MonthSources
from tests.portal.test_facturability import BILLABLE, gse

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("todos", ["Ana", "Eva", "Luis"]),
        ("activo", ["Ana"]),
        ("baja", ["Eva"]),
        ("sin_confirmar", ["Luis"]),
        ("inventado", ["Ana", "Eva", "Luis"]),
    ],
)
def test_personnel_population_and_team_average(
    client, monkeypatch, mode, expected
):
    data = gse(
        {"DEV": ["Ana", "Eva", "Luis"]},
        ("Ana", "DEV", "AER", 40, BILLABLE),
        ("Eva", "DEV", "AER", 20, BILLABLE),
        ("Luis", "DEV", "AER", 10, BILLABLE),
    )
    data.update(
        plantilla=[{"nombre": "Ana", "rol": "DEV"}], plantillaBajas=["Eva"]
    )
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda _: [MonthSources(month="2026-01", gse=data)],
    )
    result = client.get(
        "/operativa/facturabilidad/recurso/",
        {
            "mes": "2026-01",
            "personal": mode,
            "roles": "1",
            "rol": ["DEV", "QA"],
        },
    )
    assert result.status_code == 200
    assert [row.name for row in result.context["rows"]] == expected
    assert result.context["population"] == {
        "total": 3,
        "activos": 1,
        "bajas": 1,
        "sin_confirmar": 1,
    }
    assert 'name="personal"' in result.content.decode()
    population_form = (
        result.content.decode()
        .split('class="resource-population">', 1)[1]
        .split("</form>", 1)[0]
    )
    assert population_form.count('name="rol" value=') == 2
    if mode == "activo":
        assert (
            result.context["team_average"] == result.context["rows"][0].average
        )


def test_missing_month_roster_is_not_assumed_active(client, monkeypatch):
    data = gse({"DEV": ["Ana"]})
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda _: [MonthSources(month="2026-01", gse=data)],
    )
    response = client.get(
        "/operativa/facturabilidad/recurso/?mes=2026-01&personal=activo"
    )
    assert not response.context["rows"]
    assert response.context["population"]["sin_confirmar"] == 1
