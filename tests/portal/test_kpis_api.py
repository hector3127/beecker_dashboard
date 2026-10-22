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
    stub_history(monkeypatch)
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

    assert body["summary"]["totals"]["total"] == 2
    assert [r["name"] for r in body["summary"]["rows"]] == ["Ana", "Beto"]
    assert body["summary"]["rows"][0]["slug"] == "ana"


def test_it_opens_on_the_whole_year_with_monthly_and_quarterly_history(client):
    body = data(client)
    months = body["history"]["months"]

    assert body["period"]["kind"] == "anio"
    assert months["headers"][0] == "Ene" and "Oct*" in months["headers"]
    assert [r["name"] for r in months["rows"]] == ["Ana", "Beto"]
    assert body["history"]["quarters"]["headers"][0] == "T1"
    # Beto no tenia proyectos en los primeros meses: sin dato, no cero.
    assert months["rows"][1]["cells"][0] is None


def test_the_picker_keeps_the_period_links(client):
    picker = data(client, periodo="anio", anio="2026")["picker"]

    assert picker["label"] == "2026" and picker["kind"] == "anio"
    assert picker["query"] == "?periodo=anio&anio=2026"
    assert any(link["active"] for link in picker["years"])


def test_the_chart_shades_the_chosen_period(client):
    chart = data(client, periodo="mes", mes="2026-08")["history"]["chart"]
    assert chart["labels"][-1] == "Ago" and chart["highlight"] == ["Ago"]

    current = data(client, periodo="mes", mes="2026-10")["history"]["chart"]
    assert current["labels"][-1] == "Oct*" and current["highlight"] == ["Oct*"]


def test_a_closed_month_and_a_quarter_use_their_own_cut(client):
    month = data(client, periodo="mes", mes="2026-02")
    quarter = data(client, periodo="trimestre", anio="2026", trim="1")

    assert month["cut"] == {"label": "28/02/2026", "current": False}
    assert month["history"]["months"]["headers"] == ["Feb"]
    assert quarter["history"]["months"]["headers"] == ["Ene", "Feb", "Mar"]
    assert quarter["history"]["quarters"]["headers"] == ["T1"]
    assert quarter["cut"]["label"] == "31/03/2026"


@pytest.mark.parametrize(
    "query,end_month",
    [
        ({"periodo": "mes", "mes": "2026-02"}, "2026-02"),
        ({"periodo": "trimestre", "anio": "2026", "trim": "1"}, "2026-03"),
        ({"periodo": "anio", "anio": "2026"}, "2026-10"),
    ],
)
def test_the_table_uses_the_exact_cut_selected_by_the_picker(
    client, query, end_month
):
    body = data(client, **query)
    cut = next(
        c
        for c in views.load_kpi_history(2026).history.months
        if c.key == end_month
    )

    assert body["period"]["end_month"] == end_month
    assert body["cut"]["label"] == cut.cut_label
    assert body["summary"]["totals"]["total"] == cut.view.totals.total


def test_quarterly_numbers_are_not_rounded_for_the_screen(client):
    cells = data(client)["history"]["quarters"]["rows"][0]["cells"]
    firsts = [c["c"] for c in cells if c]

    assert any(c != round(c) for c in firsts if c is not None)


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
