from django.test import RequestFactory, override_settings
from apps.portal import views
from apps.portal.services import cost_audit_cache, executive_refresh


@override_settings(PORTAL_LOGIN_REQUIRED=False)
def test_prepared_table_starts_missing_costs_without_clicking_details(
    monkeypatch,
):
    import json

    summary = {
        "projects": [{"id": "AER.NEM.001.02", "cost": None}],
        "pending": 1,
    }
    monkeypatch.setattr(
        cost_audit_cache, "prepared_summary", lambda account: summary
    )
    called = []
    monkeypatch.setattr(
        executive_refresh,
        "request_refresh",
        lambda: called.append(True) or {"state": "queued"},
    )
    response = views.costos_revenue(RequestFactory().get("/ejecutiva/costos/"))
    assert json.loads(response.content)["preparing"] is True
    assert called == [True]
