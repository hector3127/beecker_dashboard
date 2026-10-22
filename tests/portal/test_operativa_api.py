"""API de Operativa: contrato, alcance de datos y permisos."""

import pytest
from django.core.cache import cache

from apps.access.scope import AccessScope
from apps.portal import views
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.eva_loader import Eva1Load, Eva2Load
from apps.portal.services.facturability_loader import MonthSources
from tests.access.fake_provider import DictProvider
from tests.portal.test_views import portfolio, stub_portfolio

pytestmark = pytest.mark.django_db

SNAPSHOT = "/api/v1/screens/operativa/"
BLOCKS = "/api/v1/screens/operativa/datos/"
BILLING = "/api/v1/screens/operativa/facturabilidad/"
OPERATIONS = frozenset({"view_operations"})


@pytest.fixture(autouse=True)
def served(monkeypatch):
    cache.clear()
    monkeypatch.setattr(
        views,
        "load_eva1",
        lambda *a, **k: Eva1Load(view=build_eva1_view([]), error=""),
    )
    monkeypatch.setattr(
        views,
        "load_eva2",
        lambda **k: Eva2Load(view=build_eva2_view([]), error=""),
    )
    stub_portfolio(monkeypatch, portfolio())
    yield
    cache.clear()


@pytest.fixture
def enforced(settings, django_user_model, client):
    settings.ACCESS_ENFORCED = True
    settings.ACCESS_PROVIDER = "tests.access.fake_provider.DictProvider"
    DictProvider.GRANTS = {}

    def sign_in(name, caps=OPERATIONS, scope=None):
        grant = (caps, scope or AccessScope.everything())
        DictProvider.GRANTS[name] = grant
        client.force_login(django_user_model.objects.create_user(name))

    yield sign_in
    DictProvider.GRANTS = {}


def data_of(client, url=BLOCKS, **params):
    return client.get(url, {"bloque": "eva3", **params}).json()["data"]


# ---------- Contrato ----------


def test_block_contract_has_only_what_the_screen_uses(client):
    data = data_of(client)

    assert set(data) == {
        "filters", "options", "loaded_at", "loading", "consumption_pending",
        "portfolio_unavailable", "stale", "error", "source_errors",
        "block_error", "has_projects", "summary", "health_states",
        "managers", "investment", "eva", "capacity", "restricted",
    }  # fmt: skip
    assert (
        data["summary"]["in_progress"] == 3 and data["summary"]["paused"] == 1
    )
    assert [m["name"] for m in data["managers"]] == ["Alberto", "Laura Vega"]
    assert [s["state"] for s in data["health_states"]] == [
        "on_time",
        "at_risk",
        "critical",
    ]
    assert data["restricted"] is False


def test_investment_never_sends_the_detail_by_project(client):
    cache.set(
        "portal:ops:investment:v3",
        {
            "complete": True,
            "totals": {"operational": 10, "commercial": 5},
            "by_project": {"1": {"operational": 10, "commercial": 5}},
        },
    )

    data = data_of(client)

    assert data["investment"] == {
        "complete": True,
        "loading": False,
        "error": "",
        "operational": 10,
        "commercial": 5,
    }
    assert "by_project" not in str(data)


def test_manager_investment_is_summed_per_manager(client):
    cache.set(
        "portal:ops:investment:v3",
        {
            "complete": True,
            "totals": {"operational": 9, "commercial": 4},
            "by_project": {
                "2": {"operational": 6, "commercial": 1},
                "3": {"operational": 3, "commercial": 3},
            },
        },
    )

    managers = {m["name"]: m for m in data_of(client)["managers"]}

    assert managers["Alberto"]["investment"] == {
        "ready": True,
        "operational": 9,
        "commercial": 4,
    }
    assert managers["Laura Vega"]["investment"]["ready"] is False


def test_filters_update_the_indicators(client):
    everything = data_of(client)
    by_service = data_of(client, servicio="T&M")
    by_client = data_of(client, cuenta="Clinica Sur")
    nothing = data_of(client, servicio="IXB")

    assert everything["summary"]["in_progress"] == 3
    assert by_service["summary"]["in_progress"] == 1
    assert by_service["filters"] == {"service": "T&M", "client": ""}
    assert by_client["summary"]["in_progress"] == 1
    assert nothing["has_projects"] is False
    assert "T&M" in everything["options"]["services"]


def test_snapshot_without_a_saved_cut_says_it_is_loading(client):
    data = client.get(SNAPSHOT, {"servicio": "T&M"}).json()["data"]

    assert data["loading"] is True and data["async"] is True
    assert data["filters"]["service"] == "T&M"
    assert data["pending_blocks"] == [
        "base",
        "eva3",
        "inversion",
        "capacidad",
        "eva4",
    ]
    assert data["billing_fresh"] is False


def test_snapshot_returns_the_cut_the_blocks_saved(client):
    data_of(client)

    data = client.get(SNAPSHOT).json()["data"]

    assert data["loading"] is False
    assert data["summary"]["in_progress"] == 3


def test_unknown_block_is_rejected_without_loading_anything(client):
    response = client.get(BLOCKS, {"bloque": "todo"})

    assert response.status_code == 400
    assert "Bloque" in response.json()["detail"]


def test_a_block_that_did_not_arrive_is_reported(client, monkeypatch):
    monkeypatch.setattr(
        views,
        "load_eva1",
        lambda *a, **k: Eva1Load(view=build_eva1_view([]), error="MPB caído"),
    )

    data = data_of(client)

    assert data["source_errors"] == ["MPB caído"]
    assert data["block_error"] == "EVA 3 no disponible"


# ---------- Facturabilidad ----------


def test_billing_summary_contract(client, monkeypatch):
    monkeypatch.setattr(
        views, "load_year_sources", lambda month: [MonthSources(month=month)]
    )

    data = client.get(BILLING).json()["data"]

    assert set(data) == {
        "target", "month", "month_label", "month_closed", "partial",
        "errors", "gap", "selected", "months",
    }  # fmt: skip
    assert data["partial"] is False and len(data["months"]) == 1
    assert {"month", "label", "global_percent"} <= set(data["months"][0])


def test_billing_is_cached_and_refreshed_on_demand(client, monkeypatch):
    calls = []

    def sources(month):
        calls.append(month)
        return [MonthSources(month=month)]

    monkeypatch.setattr(views, "load_year_sources", sources)

    client.get(BILLING)
    client.get(BILLING)
    assert len(calls) == 1
    client.get(BILLING, {"actualizar": "1"})
    assert len(calls) == 2


def test_partial_billing_is_reported_and_never_cached(client, monkeypatch):
    monkeypatch.setattr(
        views,
        "load_year_sources",
        lambda month: [MonthSources(month=month, error="Sin conexion")],
    )

    data = client.get(BILLING).json()["data"]

    assert data["partial"] is True and "Sin conexion" in data["errors"][0]
    assert (
        cache.get(
            "portal:ops:summary-data:v1:"
            + views.last_closed_month(views.timezone.localdate())
        )
        is None
    )


# ---------- Permisos ----------


def test_off_everyone_reads_every_endpoint(client):
    assert client.get(SNAPSHOT).status_code == 200
    assert client.get(BLOCKS).status_code == 200


def test_on_without_the_capability_gets_403_and_nothing_is_loaded(
    client, enforced, monkeypatch
):
    enforced("sin", caps=frozenset({"view_executive"}))
    monkeypatch.setattr(
        views, "load_eva2", lambda **k: pytest.fail("se consulto la fuente")
    )

    for url in (SNAPSHOT, BLOCKS, BILLING):
        assert client.get(url).status_code == 403


# ---------- Alcance de datos ----------


def test_limited_scope_only_sees_its_accounts_everywhere(client, enforced):
    enforced("ana", scope=AccessScope.limited(accounts=["ACME"]))

    response = client.get(BLOCKS, {"bloque": "eva3"})
    data = response.json()["data"]

    assert data["summary"]["in_progress"] == 2  # los de ACME; Clinica Sur no
    assert data["options"]["clients"] == ["ACME"]
    assert "Clinica" not in response.content.decode()


def test_limited_scope_hides_the_team_wide_figures(client, enforced):
    enforced("ana", scope=AccessScope.limited(accounts=["ACME"]))

    data = data_of(client)

    assert data["restricted"] is True
    assert data["capacity"] is None
    assert data["eva"]["eva1"] is None and data["eva"]["eva3"] is None
    assert client.get(BILLING).status_code == 403


def test_limited_scope_totals_investment_only_for_its_projects(
    client, enforced
):
    cache.set(
        "portal:ops:investment:v3",
        {
            "complete": True,
            "totals": {"operational": 99, "commercial": 99},
            "by_project": {
                "1": {"operational": 7, "commercial": 2},  # ACME
                "2": {"operational": 50, "commercial": 50},  # Clinica Sur
            },
        },
    )
    enforced("ana", scope=AccessScope.limited(accounts=["ACME"]))

    data = data_of(client)

    assert data["investment"]["operational"] == 7
    assert data["investment"]["commercial"] == 2


def test_each_scope_has_its_own_saved_cut(client, enforced, django_user_model):
    """El corte guardado de quien ve todo no se le entrega a quien ve poco."""
    enforced("jefa")  # alcance total
    assert data_of(client)["summary"]["in_progress"] == 3
    client.logout()
    enforced("ana", scope=AccessScope.limited(accounts=["ACME"]))

    first = client.get(SNAPSHOT).json()["data"]

    assert first["loading"] is True  # no hay corte de este alcance todavia
    assert "Clinica" not in str(first)
    data_of(client)
    again = client.get(SNAPSHOT).json()["data"]
    assert again["summary"]["in_progress"] == 2


def test_scope_key_is_stable_and_separates_scopes():
    a = AccessScope.limited(accounts=["ACME", "Cagsa"])
    b = AccessScope.limited(accounts=["cagsa", "acme"])
    c = AccessScope.limited(accounts=["ACME"])

    assert a.signature() == b.signature() != c.signature()
    assert AccessScope.everything().signature() != a.signature()
