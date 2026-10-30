"""API de KPIs de Delivery Managers: periodo, cortes, historico y alcance."""

import pytest

from apps.access.scope import AccessScope
from apps.portal import views
from tests.portal.test_views import portfolio, stub_history, stub_portfolio

pytestmark = pytest.mark.django_db

URL = "/api/v1/screens/kpis-dm/"
PAGE = "/operativa/kpis-delivery-managers/"
OPS = frozenset({"view_operations"})


@pytest.fixture(autouse=True)
def history(monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    from tests.portal.kpi_cut_support import stub_inventory

    stub_inventory(monkeypatch)
    monkeypatch.setattr(
        "apps.portal.views.load_portfolio",
        lambda: pytest.fail("Proyectos no se consulta para KPIs"),
    )


def data(client, **params):
    response = client.get(URL, params)
    assert response.status_code == 200
    return response.json()["data"]


def test_managers_and_totals_come_from_the_cut(client):
    body = data(client)

    assert body["summary"]["totals"]["total"] == 3
    assert [r["name"] for r in body["summary"]["rows"]] == ["Ana", "Beto"]
    assert body["summary"]["rows"][0]["slug"] == "ana"


def test_it_opens_on_the_whole_year_with_monthly_and_quarterly_history(client):
    body = data(client)
    months = body["history"]["months"]

    assert body["period"]["kind"] == "anio"
    assert (
        months["headers"][0] == "Ene"
        and months["headers"][-1] == "Dic"
        and len(months["headers"]) == 12
    )
    assert [r["name"] for r in months["rows"]] == ["Ana", "Beto"]
    assert body["history"]["quarters"]["headers"][0] == "T1"
    # Beto no tenia proyectos en los primeros meses: sin dato, no cero.
    assert months["rows"][1]["cells"][0]["total"] == 1


def test_the_picker_keeps_the_period_links(client):
    picker = data(client, periodo="anio", anio="2026")["picker"]

    assert picker["label"] == "2026" and picker["kind"] == "anio"
    assert picker["query"] == "?periodo=anio&anio=2026"
    assert any(link["active"] for link in picker["years"])


def test_chart_and_history_years_are_independent_from_cut(client):
    body = data(
        client, corte="2026-02-15", chart_year="2025", history_year="2026"
    )
    assert body["cut"]["label"] == "15/02/2026"
    assert body["filters"]["chart_year"] == 2025
    assert body["filters"]["history_year"] == 2026
    assert len(body["history"]["chart"]["labels"]) == 12
    assert len(body["history"]["months"]["headers"]) == 12
    assert body["summary"]["totals"]["total"] == 2
    assert body["history"]["months"]["totals"][-1] is None
    assert body["history"]["quarters"]["headers"] == ["T1", "T2", "T3", "T4*"]


@pytest.mark.parametrize(
    "cut,total", [("2026-02-15", 2), ("2026-03-15", 3), ("2026-10-28", 3)]
)
def test_table_uses_exact_cut_not_month_end(client, cut, total):
    body = data(client, corte=cut)
    assert body["filters"]["cut"] == cut
    assert body["summary"]["totals"]["total"] == total
    ana = body["summary"]["rows"][0]
    assert ana["t"] == (100 if total == 2 else 50)
    assert ana["c"] == 0  # C es cumplimiento: sobrecosto y pendientes no suman


@pytest.mark.parametrize(
    "query",
    [{"corte": "2027-01-01"}, {"history_year": "bad"}, {"chart_year": "2027"}],
)
def test_invalid_cut_or_year_returns_400(client, query):
    assert client.get(URL, query).status_code == 400


def test_global_manager_filter_changes_all_panels_and_weighted_totals(client):
    body = data(client, corte="2026-09-30", dm=["Ana"])
    assert [r["name"] for r in body["summary"]["rows"]] == ["Ana"]
    assert body["summary"]["totals"]["total"] == 2
    assert body["summary"]["totals"]["t"] == 50
    assert body["summary"]["totals"]["c"] == 0
    assert [r["name"] for r in body["history"]["months"]["rows"]] == ["Ana"]
    assert [r["name"] for r in body["history"]["quarters"]["rows"]] == ["Ana"]
    assert [r["name"] for r in body["history"]["chart"]["series"]] == ["Ana"]
    assert body["history"]["months"]["totals"][0]["total"] == 1
    assert body["history"]["months"]["totals"][0]["c"] == 0
    assert body["filters"]["managers"] == ["Ana", "Beto"]


def test_multiple_and_empty_global_manager_selection(client):
    selected = data(client, dm=["Ana", "Beto"])
    assert selected["summary"]["totals"]["total"] == 3
    assert selected["summary"]["totals"]["c"] == pytest.approx(100 / 3)
    empty = data(client, dm="__none__")
    assert empty["summary"]["totals"]["total"] == 0
    assert empty["summary"]["totals"]["c"] is None
    assert empty["history"]["months"]["rows"] == []
    assert empty["history"]["quarters"]["rows"] == []
    assert empty["history"]["chart"]["series"] == []


def test_quarterly_numbers_are_not_rounded_for_the_screen(client):
    cells = data(client)["history"]["quarters"]["rows"][0]["cells"]
    firsts = [c["c"] for c in cells if c]

    assert firsts[0] == pytest.approx(0)


def test_a_history_failure_says_why_and_leaves_the_tables_empty(
    client, monkeypatch
):
    stub_history(monkeypatch, error="Clockify no responde.")

    body = data(client)

    assert body["history"]["months"] is None
    assert body["history"]["quarters"] is None
    assert body["history"]["error"] == "Clockify no responde."


# ---------- Permisos y pagina ----------


def test_it_needs_operations_and_the_whole_team(client, enforced):
    enforced("sin", caps=frozenset({"view_costs"}))
    assert client.get(URL).status_code == 403

    enforced("ana", caps=OPS, scope=AccessScope.limited(accounts=["Acme"]))
    assert client.get(URL).status_code == 403
    assert client.get(PAGE).status_code == 403

    enforced("beto", caps=OPS)
    assert client.get(URL).status_code == 200


def test_the_page_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get(PAGE).status_code == 302


@pytest.mark.parametrize("previous", [False, True])
def test_page_defers_history_and_retains_modular_shell(
    client, monkeypatch, previous
):
    monkeypatch.setattr(
        views, "load_kpi_history", lambda *a: pytest.fail("API only")
    )
    response = client.get(
        PAGE, {"mes": "2026-02", **({"vista": "anterior"} if previous else {})}
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert "/static/app/scripts/pages/kpis_dm/main.js" in html
    assert 'id="kpis-content"' in html
    assert "portal/js/" not in html


def test_retired_query_does_not_bypass_team_scope(client, enforced):
    enforced("ana", caps=OPS, scope=AccessScope.limited(accounts=["Acme"]))
    assert client.get(PAGE, {"vista": "anterior"}).status_code == 403
