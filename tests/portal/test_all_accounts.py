from unittest.mock import Mock
from django.test import RequestFactory, override_settings
from apps.portal import views
from apps.portal.services import account_profitability as service
from tests.fakes import InMemorySheetRepository


def test_intermediate_accounts_are_in_full_list(monkeypatch):
    reader = InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status", "Account", "", "", "ID", "", "Date", "USD"],
                ["Collected", "Middle", "", "", "MID", "", "2026-01-01", 100],
                ["Collected", "Old", "", "", "OLD", "", "2025-01-01", 100],
            ]
        }
    )
    monkeypatch.setattr(service, "build_sheet_repository", lambda: reader)
    monkeypatch.setattr(
        service.cache,
        "get",
        lambda key: {"complete": True, "entries": {"entry": 50}},
    )
    result = service.account_profitability()
    assert result["healthy"] == result["unhealthy"] == []
    assert len(result["accounts"]) == 1
    assert result["accounts"][0]["classification"] == "intermediate"


@override_settings(PORTAL_LOGIN_REQUIRED=False)
def test_all_accounts_page_renders_links(monkeypatch):
    monkeypatch.setattr(
        service,
        "account_profitability",
        lambda: {
            "year": 2026,
            "accounts": [
                {
                    "name": "Middle",
                    "url": "/cuenta/middle/",
                    "classification": "intermediate",
                    "projects": 1,
                    "revenue": 100,
                    "cost": 50,
                    "gross_profit": 50,
                    "margin": 50,
                    "pending": 0,
                }
            ],
        },
    )
    response = views.todas_cuentas(RequestFactory().get("/ejecutiva/cuentas/"))
    assert response.status_code == 200
    html = response.content.decode()
    assert "Middle" in html and "Intermedia" in html
    assert "target=" not in html
    assert "/ejecutiva/costos/detalle/?nombre=Middle" in html
