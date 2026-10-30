"""API de Operativa: contrato de EVA, inversion, facturabilidad y capacidad."""

import pytest

from apps.access.scope import AccessScope
from apps.portal import views
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva_loader import Eva1Load
from tests.portal.test_views import (
    capacity_data,
    eva_row,
    stub_capacity,
    stub_eva1,
    stub_facturability,
)

pytestmark = pytest.mark.django_db

BASE = "/api/v1/screens/"
OPS = frozenset({"view_operations"})
SCREENS = [
    "eva-2/",
    "eva-3/",
    "inversion/",
    "capacidad/",
    "facturabilidad/",
    "facturabilidad/especialidad/",
    "facturabilidad/recurso/",
]


def data(client, path, **params):
    response = client.get(BASE + path, params)
    assert response.status_code == 200, response.content
    return response.json()


def test_eva3_lists_its_projects_and_the_renewal_average(client, monkeypatch):
    stub_eva1(monkeypatch, [eva_row()])

    body = data(client, "eva-3/")["data"]

    assert [p["project_id"] for p in body["eva"]["projects"]] == ["AER.001"]
    assert body["renewal_average"] == 8


def test_eva1_and_eva2_share_the_ixb_raas_cut(client, monkeypatch):
    load = Eva1Load(view=build_eva1_view([eva_row()]), error="")
    monkeypatch.setattr(views, "load_eva2", lambda *a, **k: load)

    assert client.get(BASE + "eva-1/").status_code == 404
    second = data(client, "eva-2/")["data"]

    assert second["error"] == ""
    assert second["eva"]["total_projects"] == 1


def test_facturability_general_keeps_the_partial_months(client, monkeypatch):
    stub_facturability(monkeypatch)

    body = data(client, "facturabilidad/", mes="2026-02")

    assert body["data"]["selected"]["error"] == "GSE: sin base"
    assert body["data"]["first"]["fixed_percent"] == 50.0
    assert body["meta"]["period"]["end_month"] == "2026-02"
    assert [o["label"] for o in body["data"]["role_options"]][0] == "DEV"


def test_facturability_by_specialty_and_by_resource(client, monkeypatch):
    stub_facturability(monkeypatch)

    specialty = data(client, "facturabilidad/especialidad/")["data"]
    resource = data(client, "facturabilidad/recurso/")["data"]

    assert specialty["specialties"][0]["name"] == "Dev"
    assert specialty["headcount"] == 1
    # Un mes sin datos es null, no cero.
    assert resource["rows"][0]["percents"] == [50.0, None]
    assert resource["workdays"] == [21, 19]


def test_investment_for_a_month(client, monkeypatch):
    stub_facturability(monkeypatch)

    body = data(client, "inversion/", mes="2026-01")["data"]

    assert body["month"] == "2026-01"
    assert "investment" in body


def test_capacity_keeps_its_filters(client, monkeypatch):
    stub_capacity(monkeypatch, capacity_data())

    body = data(client, "capacidad/", mes="2026-10")["data"]

    assert body["filters"]["month"] == "2026-10"
    assert body["error"] == ""
    assert "capacity" in body


@pytest.mark.parametrize("path", SCREENS)
def test_needs_the_capability(client, enforced, monkeypatch, path):
    enforced("sin", caps=frozenset({"view_costs"}))
    for name in ("load_portfolio", "load_eva2", "load_eva1"):
        monkeypatch.setattr(views, name, lambda *a, **k: pytest.fail("fuentes"))

    assert client.get(BASE + path).status_code == 403


@pytest.mark.parametrize("path", SCREENS)
def test_limited_scope_is_refused_before_reading_sources(
    client, enforced, monkeypatch, path
):
    enforced("ana", caps=OPS, scope=AccessScope.limited(accounts=["Acme"]))
    for name in ("load_portfolio", "load_eva2", "load_eva1"):
        monkeypatch.setattr(views, name, lambda *a, **k: pytest.fail("fuentes"))

    assert client.get(BASE + path).status_code == 403
