"""API de EVA-04: contrato, permisos y alcance de datos."""

from datetime import date

import pytest

from apps.access.scope import AccessScope
from apps.portal.services import eva4
from tests.portal.test_eva4 import HEADER, TODAY, row

pytestmark = pytest.mark.django_db

URL = "/api/v1/screens/eva4/"
OPERATIONS = frozenset({"view_operations"})


def report():
    """Nestlé (2 activos, 1 suspendido) y Cagsa (1 activo), ya con horas."""
    rows = [HEADER, row("1"), row("2"), row("3", "Suspendido"), row("4")]
    rows[4] = [*rows[4]]
    rows[4][0], rows[4][2] = "Cagsa", "SAAS.CAG.001"
    data = eva4.build_eva4(rows, TODAY)
    for process in data["processes"]:
        missing = process["bot_id"] == "2"
        process.update(
            bot_label=process["bot_id"],
            invested_hours=None if missing else 12.5,
            average_limit=30,
            hours_balance=None if missing else 17.5,
        )
    data.update(
        month="2026-10",
        hours_origin="database",
        hours_source="08.Base Clockify 2026",
        unmatched_tasks=1,
        missing_limits=0,
    )
    return data


@pytest.fixture
def served(monkeypatch):
    calls = []

    def fake(*args):
        calls.append(args)
        return report()

    monkeypatch.setattr(eva4, "load_eva4", fake)
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    return calls


# ---------- Contrato ----------


def test_contract_has_only_the_fields_the_screen_uses(client, served):
    body = client.get(URL, {"mes": "2026-10"}).json()
    data = body["data"]

    assert set(data) == {
        "available",
        "error",
        "month",
        "loaded_at",
        "summary",
        "processes",
        "renewals",
        "clients",
        "notes",
    }
    assert data["summary"] == {
        "active": 3,
        "suspended": 1,
        "total": 4,
        "renewal_count": 2,
    }
    assert len(data["processes"]) == 3  # solo activos
    assert set(data["processes"][0]) == {
        "manager",
        "country",
        "client",
        "bot",
        "service",
        "process",
        "status",
        "status_code",
        "start",
        "finish",
        "average_limit",
        "invested_hours",
        "hours_balance",
        "package_limit",
        "package_available",
        "risk",
    }
    assert body["meta"]["generated_at"]
    assert [s["name"] for s in body["meta"]["sources"]] == ["ROC", "Clockify"]


def test_dates_are_iso_and_blanks_are_null(client, served):
    processes = client.get(URL).json()["data"]["processes"]
    second = next(p for p in processes if p["bot"] == "2")

    assert second["start"] == "2026-01-01" and second["finish"] == "2026-10-20"
    assert second["invested_hours"] is None and second["hours_balance"] is None
    assert second["package_limit"] is None
    assert second["package_available"] == 0  # un cero real no es "sin dato"
    assert second["average_limit"] == 30


def test_internal_fields_are_never_exposed(client, served):
    text = client.get(URL).content.decode()

    assert "bot_id" not in text and "bot_label" not in text


def test_month_is_passed_to_the_loader_only_when_given(client, served):
    client.get(URL, {"mes": "2026-09"})
    client.get(URL)

    assert served == [("2026-09",), ()]


def test_unavailable_report_is_a_normal_answer_with_the_reason(
    client, monkeypatch
):
    monkeypatch.setattr(
        eva4, "load_eva4", lambda *a: {"available": False, "error": "mes mal"}
    )

    response = client.get(URL, {"mes": "x"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["available"] is False and data["error"] == "mes mal"
    assert data["processes"] == [] and data["summary"]["total"] == 0


def test_stale_cut_keeps_its_rows_and_reports_the_error(client, monkeypatch):
    stale = {**report(), "error": "Sheets no responde"}
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: stale)

    data = client.get(URL).json()["data"]

    assert data["available"] is True and data["error"] == "Sheets no responde"
    assert len(data["processes"]) == 3


# ---------- Permisos ----------


def test_off_everyone_reads_the_screen(client, served):
    assert client.get(URL).status_code == 200


def test_on_without_the_capability_gets_403_and_no_data(
    client, served, enforced
):
    enforced("sin", caps=frozenset({"view_executive"}))

    response = client.get(URL)

    assert response.status_code == 403
    assert "Nestl" not in response.content.decode()
    assert served == []  # ni siquiera se consultaron las fuentes


def test_on_anonymous_gets_403(client, served, enforced):
    assert client.get(URL).status_code == 403
    assert served == []


def test_on_with_the_capability_reads_it(client, served, enforced):
    enforced("ana")

    assert client.get(URL).status_code == 200


# ---------- Alcance de datos ----------


def test_limited_scope_only_returns_its_accounts_with_recomputed_totals(
    client, served, enforced
):
    enforced("ana", scope=AccessScope.limited(accounts=["Cagsa"]))

    data = client.get(URL).json()["data"]

    assert {p["client"] for p in data["processes"]} == {"Cagsa"}
    assert data["summary"] == {
        "active": 1,
        "suspended": 0,
        "total": 1,
        "renewal_count": 1,
    }
    assert [r["name"] for r in data["clients"]["rows"]] == ["Cagsa"]
    assert [r["project_id"] for r in data["renewals"]] == ["SAAS.CAG.001"]
    assert sum(data["clients"]["service_totals"]) == 1


def test_scope_never_leaks_other_accounts_anywhere_in_the_body(
    client, served, enforced
):
    enforced("ana", scope=AccessScope.limited(accounts=["Cagsa"]))

    assert "Nestl" not in client.get(URL).content.decode()


def test_scope_without_matches_answers_empty_not_error(
    client, served, enforced
):
    enforced("ana", scope=AccessScope.limited())

    data = client.get(URL).json()["data"]

    assert data["available"] is True
    assert data["summary"]["total"] == 0 and data["processes"] == []


# ---------- Pagina ----------


def test_page_is_a_shell_without_business_data(client, served):
    html = client.get("/operativa/eva-4/", {"mes": "2026-09"}).content.decode()

    assert 'id="eva4-content"' in html
    assert 'src="/static/app/scripts/pages/eva4/main.js' in html
    assert "Nestl" not in html and "ROC.NSC" not in html
    assert served == []  # la pagina no consulta fuentes


def test_page_requires_the_capability_when_enforced(client, enforced):
    enforced("sin", caps=frozenset())

    assert client.get("/operativa/eva-4/").status_code == 403


def test_page_sends_anonymous_people_to_login_when_enforced(client, enforced):
    response = client.get("/operativa/eva-4/")

    assert response.status_code == 302
    assert response.url.startswith("/admin/login/")


def test_retired_parameter_still_serves_the_shell_and_defers_sources(
    client, monkeypatch, served
):
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: date(2026, 10, 22))
    response = client.get(
        "/operativa/eva-4/", {"vista": "anterior", "mes": "2026-09"}
    )
    html = response.content.decode()
    assert response.status_code == 200
    assert 'id="eva4-content"' in html
    assert "Estás viendo la pantalla anterior" not in html
    assert served == []
