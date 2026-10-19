import pytest
from django.test import Client, override_settings
from django.urls import reverse

from apps.portal.models import ExecutiveAgreement
from apps.portal.services import account_profitability as service
from apps.portal.services.revenue_costs import key
from tests.fakes import InMemorySheetRepository


@pytest.mark.django_db
@override_settings(PORTAL_LOGIN_REQUIRED=False)
def test_global_agreement_create_edit_and_read_across_periods(client):
    url = reverse("portal:acuerdos_ejecutivos")
    data = {
        "title": "Revisar presupuesto",
        "kind": "agreement",
        "owner": "Ana",
        "due_date": "2026-12-01",
        "status": "open",
        "notes": "Aprobar estimacion",
    }
    response = client.post(url, data)
    assert response.status_code == 200
    item = response.json()["items"][0]
    data.update({"id": item["id"], "status": "done", "notes": "Aprobado"})
    assert client.post(url, data).status_code == 200
    saved = client.get(
        url, {"periodo": "trimestre", "anio": "2026", "trimestre": "1"}
    ).json()["items"]
    assert (
        len(saved) == 1
        and saved[0]["status"] == "done"
        and saved[0]["notes"] == "Aprobado"
    )
    assert ExecutiveAgreement.objects.count() == 1


@pytest.mark.django_db
@override_settings(PORTAL_LOGIN_REQUIRED=False)
def test_agreement_validation_and_csrf(client):
    url = reverse("portal:acuerdos_ejecutivos")
    assert (
        client.post(
            url, {"title": "", "kind": "pending", "status": "open"}
        ).status_code
        == 400
    )
    assert (
        client.post(
            url, {"title": "x", "kind": "bad", "status": "open"}
        ).status_code
        == 400
    )
    assert client.post(url, {"id": "999", "title": "x"}).status_code == 404
    assert (
        Client(enforce_csrf_checks=True).post(url, {"title": "x"}).status_code
        == 403
    )
    assert ExecutiveAgreement.objects.count() == 0


@pytest.mark.django_db
@override_settings(PORTAL_LOGIN_REQUIRED=True)
def test_agreement_api_requires_login_when_enabled(client):
    assert client.get(reverse("portal:acuerdos_ejecutivos")).status_code == 401


def test_unhealthy_ranking_has_no_limit_and_excludes_partial_accounts(
    monkeypatch,
):
    rows = [["Status", "Account", "", "", "ID", "", "Date", "USD"]]
    results = {}
    for i in range(8):
        pid = f"P{i}"
        rows.append(
            ["Collected", f"Account {i}", "", "", pid, "", "2026-06-01", 100]
        )
        if i < 7:
            results[key(pid)] = {"complete": True, "entries": {f"E{i}": 80}}
    r = InMemorySheetRepository({"DataRevenue": rows})
    monkeypatch.setattr(
        service.cache, "get", lambda cache_key: results.get(cache_key)
    )
    result = service.account_profitability(r)
    assert len(result["unhealthy"]) == 7
    assert all(a["margin"] == 20 for a in result["unhealthy"])
    assert result["pending_accounts"] == 1
