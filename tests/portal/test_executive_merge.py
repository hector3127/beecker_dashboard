"""Funciones ejecutivas integradas conservan fuentes, CR y precarga."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.test import RequestFactory, override_settings

from apps.portal import views
from apps.portal.services import account_profitability as accounts
from apps.portal.services import executive_operations as operations
from apps.portal.services import executive_population as population
from apps.portal.services.financial_cache import snapshot_key
from apps.portal.services.revenue_costs import key, project_ids
from core.time_entries.models import TimeEntry
from tests.fakes import InMemorySheetRepository
from tests.portal.test_kpi_sources import TODAY, reader


@pytest.fixture(autouse=True)
def isolated_cache():
    cache.clear()
    yield
    cache.clear()


def test_annual_operations_uses_a_to_i_and_budget_j_including_closed_cr(
    monkeypatch,
):
    r = reader()
    r.sheets["Historico_Proyectos"][0][9] = "Budget  (Hrs)"
    r.sheets["Historico_Proyectos"][1][9] = 400
    monkeypatch.setattr(population.timezone, "localdate", lambda: TODAY)
    projects = {p["id"]: p for p in population.population(r)}
    assert set(projects) == {"AER.001", "IXB.001_CR"}
    assert projects["IXB.001_CR"]["budget"] == 400
    assert projects["IXB.001_CR"]["end"] == "2026-03-15"
    assert projects["AER.001"]["budget"] == 100


def test_operations_preserves_exact_cr_id_dates_and_cached_consumption(
    monkeypatch,
):
    project = {
        "id": "AIN.002 CR",
        "service": "IXB",
        "budget": 100,
        "start": "2026-01-01",
        "end": "2026-01-31",
    }
    monkeypatch.setattr(operations, "population", lambda: [project])
    loader = Mock()
    loader.load_project.return_value = [
        TimeEntry(
            "e1",
            "AIN.002 CR",
            "Ana",
            datetime(2026, 1, 20),
            20,
            True,
            0,
            task_name="CR",
        ),
    ]
    monkeypatch.setattr(operations, "build_clockify_loader", lambda _: loader)
    monkeypatch.setattr(operations, "build_sheet_repository", lambda: reader())
    assert operations.operations_summary()["partial"] is True
    assert operations.calculate_burn("AIN.002 CR")["burn"] == 20
    operations.calculate_burn("AIN.002 CR")
    loader.load_project.assert_called_once()
    assert loader.load_project.call_args.args[0] == "AIN.002 CR"
    summary = operations.operations_summary()
    assert summary["advance"] == 20
    assert summary["etc"] == 80
    assert not summary["partial"]
    with pytest.raises(ValueError):
        operations.calculate_burn("OTHER")


def revenue_row(account, pid, status="Collected", amount=100):
    return [status, account, "", "", pid, "", "2026-09-01", amount]


def test_accounts_are_ranked_by_weighted_score_and_flag_pending_ones():
    rows = [
        revenue_row("Healthy", "P1"),
        revenue_row("Unhealthy", "P2"),
        revenue_row("Intermediate", "P3"),
        revenue_row("Pending", "P4"),
        revenue_row("Forecast", "P5", "Forecast", 90000),
    ]
    r = InMemorySheetRepository({"DataRevenue": [["Status"], *rows]})
    for pid, cost in [("P1", 20), ("P2", 90), ("P3", 50)]:
        cache.set(key(pid), {"complete": True, "entries": {pid: cost}})
    result = accounts.account_profitability(r)
    # Pending no tiene costos cargados aun, por eso su utilidad parcial es alta.
    assert [a["name"] for a in result["healthy"]] == ["Pending", "Healthy"]
    assert [a["name"] for a in result["unhealthy"]] == [
        "Unhealthy",
        "Intermediate",
    ]
    assert {a["name"] for a in result["accounts"] if a["partial"]} == {
        "Pending"
    }
    assert result["pending_accounts"] == 1
    assert len(result["accounts"]) == 4
    healthy = next(a for a in result["accounts"] if a["name"] == "Healthy")
    assert healthy["collections_percent"] == 100
    assert healthy["url"].startswith("/cuenta/healthy/")


def test_shared_clockify_records_make_both_accounts_pending():
    r = InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status"],
                revenue_row("A", "P1"),
                revenue_row("B", "P2"),
            ]
        }
    )
    for pid in ["P1", "P2"]:
        cache.set(key(pid), {"complete": True, "entries": {"shared": 10}})
    result = accounts.account_profitability(r)
    assert result["pending_accounts"] == 2
    assert all(a["partial"] for a in result["accounts"])


def test_prepared_accounts_avoid_sheet_queries(monkeypatch):
    prepared = {
        "accounts": [{"name": "A", "revenue": 0, "gross_profit": 0}],
        "year": 2026,
    }
    cache.set(snapshot_key(), {"accounts": prepared})
    cache.set(snapshot_key() + ":fresh", True)
    monkeypatch.setattr(
        accounts, "build_sheet_repository", lambda: pytest.fail("External read")
    )
    loaded = accounts.load_account_profitability()
    assert [a["name"] for a in loaded["accounts"]] == ["A"]


def test_account_cost_scope_keeps_explicit_revenue_of_the_account():
    r = InMemorySheetRepository(
        {
            "DataRevenue": [
                ["Status"],
                revenue_row("A", "OLD"),
                revenue_row("A", "NEW"),
                revenue_row("B", "OTHER"),
            ],
            "MPB": [
                ["ID", "INICIO", "FIN"],
                ["OLD", "2025-01-01", "2025-12-31"],
                ["NEW", "2026-01-01", "2026-12-31"],
            ],
        }
    )
    # Un registro de DataRevenue del ano sigue valido aunque MPB cierre antes.
    assert project_ids(r, "A") == ["NEW", "OLD"]


@override_settings(PORTAL_LOGIN_REQUIRED=True)
@pytest.mark.parametrize(
    "view",
    [
        views.cuentas_rentabilidad,
        views.operaciones_ejecutiva,
    ],
)
def test_new_apis_require_login(view):
    request = RequestFactory().get("/")
    request.user = SimpleNamespace(is_authenticated=False)
    assert view(request).status_code == 401


def test_account_page_and_audit_keep_portal_navigation(client, monkeypatch):
    monkeypatch.setattr(
        accounts,
        "load_account_profitability",
        lambda: {"accounts": [], "year": 2026},
    )
    page = client.get("/ejecutiva/cuentas/")
    assert page.status_code == 200
    assert "Panel anterior" not in page.content.decode()
    detail = client.get(
        "/ejecutiva/costos/detalle/", {"nombre": "ACME", "vista": "proyectos"}
    )
    assert detail.status_code == 200
    assert detail.context["cost_account"] == "ACME"
    assert detail.context["cost_back"] == "/cuenta/acme/?nombre=ACME"
