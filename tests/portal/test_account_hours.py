"""Monthly hours: dates, deduplication, pending data and account access."""

from datetime import date

import pytest
from django.utils import timezone

from apps.access.scope import AccessScope
from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry, SyncRun
from apps.portal.services import account_hours
from tests.fakes import InMemorySheetRepository

pytestmark = pytest.mark.django_db
URL = "/api/v1/screens/cuenta/horas/"


@pytest.fixture
def source(monkeypatch):
    monkeypatch.setattr(
        account_hours.timezone, "localdate", lambda: date(2026, 10, 22)
    )
    repo = InMemorySheetRepository({"DataRevenue": [[]]})
    monkeypatch.setattr(account_hours, "build_sheet_repository", lambda: repo)
    monkeypatch.setattr(
        account_hours,
        "project_catalog",
        lambda r, y: {
            "p.001": {"id": "P.001", "accounts": {"Cadena Comercial Oxxo"}},
            "p.001_s1": {
                "id": "P.001_S1",
                "accounts": {"Cadena Comercial Oxxo"},
            },
            "other": {"id": "OTHER", "accounts": {"Otra"}},
        },
    )
    run = SyncRun.objects.create(kind="clockify", status="ok")
    for month in (1, 9, 10):
        ClockifyMonthSync.objects.create(
            month=date(2026, month, 1),
            entries_count=0,
            total_seconds=0,
            synced_at=timezone.now(),
            run=run,
        )
    return repo


def entry(key, day, hours, task="", **extra):
    return ClockifyTimeEntry.objects.create(
        entry_id=key,
        project_id="clock-1",
        project_name="P.001",
        entry_date=day,
        month=day.replace(day=1),
        duration_seconds=round(hours * 3600),
        task_name=task,
        **extra,
    )


def test_monthly_hours_partition_sprints_and_skip_future_dates(source):
    entry("a", date(2026, 1, 31), 1.25)
    entry("b", date(2026, 9, 1), 2, "S1 - trabajo")
    entry("c", date(2026, 10, 23), 50)
    data = account_hours.load_account_hours("Oxxo", 2026)
    base, sprint = data["projects"]
    assert base["id"] == "P.001"
    assert base["cells"][0]["hours"] == 1.25
    assert base["cells"][8]["hours"] == 0
    assert sprint["cells"][8]["hours"] == 2
    assert data["known_hours"] == 3.25
    assert data["totals"][1]["hours"] is None  # unsynchronized ≠ zero
    assert data["totals"][9]["hours"] == 0
    assert data["months"][9]["partial"]
    assert len(data["months"]) == 10


def test_unresolved_project_remains_pending(source):
    data = account_hours.load_account_hours("Oxxo", 2026)
    assert all(
        c["hours"] is None for row in data["projects"] for c in row["cells"]
    )
    assert data["totals"][0]["hours"] is None
    assert data["partial"]


def test_investment_ids_with_recorded_hours_are_not_lost(source):
    from apps.datastore.models import Client, Project

    owner = Client.objects.create(name="OXXO", key="oxxo")
    Project.objects.create(
        internal_id="CCO.000", base_id="CCO.000", client=owner
    )
    ClockifyTimeEntry.objects.create(
        entry_id="investment",
        project_id="clock-invest",
        project_name="CCO.000",
        entry_date=date(2026, 9, 1),
        month=date(2026, 9, 1),
        duration_seconds=7200,
    )
    data = account_hours.load_account_hours("Oxxo", 2026)
    row = next(r for r in data["projects"] if r["id"] == "CCO.000")
    assert row["known_hours"] == 2
    assert data["known_hours"] == 2


def test_overlapping_links_are_not_assigned_twice(source, monkeypatch):
    monkeypatch.setattr(
        account_hours,
        "project_catalog",
        lambda r, y: {
            "a": {"id": "A", "accounts": {"Oxxo"}},
            "b": {"id": "B", "accounts": {"Oxxo"}},
        },
    )
    monkeypatch.setattr(
        account_hours,
        "load_project_links",
        lambda r: {"a": "clock-1", "b": "clock-1"},
    )
    entry("a", date(2026, 9, 1), 5)
    data = account_hours.load_account_hours("Oxxo", 2026)
    assert data["known_hours"] == 0
    assert all(r["cells"][8]["partial"] for r in data["projects"])


def test_monthly_contract_ids_partition_their_base(source, monkeypatch):
    monkeypatch.setattr(
        account_hours,
        "project_catalog",
        lambda r, y: {
            "base": {"id": "AER.CCO.001", "accounts": {"Oxxo"}},
            "month": {"id": "AER.CCO.001.09", "accounts": {"Oxxo"}},
        },
    )
    ClockifyTimeEntry.objects.create(
        entry_id="september",
        project_id="clock-aer",
        project_name="AER.CCO.001",
        entry_date=date(2026, 9, 1),
        month=date(2026, 9, 1),
        duration_seconds=7200,
    )
    data = account_hours.load_account_hours("Oxxo", 2026)
    assert data["projects"][0]["cells"][8]["hours"] == 0
    assert data["projects"][1]["cells"][8]["hours"] == 2
    assert data["known_hours"] == 2


def test_unidentified_tasks_are_partial_without_guessing(source):
    entry("a", date(2026, 9, 1), 4, task_id="unknown")
    data = account_hours.load_account_hours("Oxxo", 2026)
    assert data["known_hours"] == 0
    assert all(r["cells"][8]["partial"] for r in data["projects"])
    assert all("total parcial" in r["issue"] for r in data["projects"])


def test_report_and_csv_have_the_same_account_scope(client, enforced, source):
    enforced(
        "ana",
        frozenset({"view_operations"}),
        AccessScope.limited(accounts=["Oxxo"]),
    )
    entry("a", date(2026, 9, 1), 2)
    body = client.get(URL, {"nombre": "Oxxo", "anio": 2026}).json()
    assert body["data"]["known_hours"] == 2
    csv = client.get(URL, {"nombre": "Oxxo", "anio": 2026, "descargar": "csv"})
    assert csv.status_code == 200
    assert "2026-09" in csv.content.decode("utf-8-sig")
    assert "attachment" in csv["Content-Disposition"]
    for suffix in ("", "&descargar=csv"):
        assert (
            client.get(URL + "?nombre=Otra&anio=2026" + suffix).status_code
            == 404
        )


def test_without_operations_permission_cannot_export(client, enforced, source):
    enforced("ana", frozenset({"view_costs"}), AccessScope.everything())
    assert (
        client.get(URL, {"nombre": "Oxxo", "descargar": "csv"}).status_code
        == 403
    )


def test_bad_year_is_rejected_before_reading_sources(client, source):
    for year in ("oops", "1999", "2027"):
        assert (
            client.get(URL, {"nombre": "Oxxo", "anio": year}).status_code == 400
        )


def test_page_returns_to_the_account(client, source):
    response = client.get("/cuenta/oxxo/horas/?nombre=Oxxo")
    assert response.status_code == 200
    html = response.content.decode()
    assert "/cuenta/oxxo/?nombre=Oxxo" in html
    assert "app/scripts/pages/account_hours/main.js" in html


def test_csv_text_cannot_be_an_excel_formula():
    from apps.portal.api.account_hours import csv_report

    data = {
        "client": "=1+1",
        "year": 2026,
        "cutoff": "2026-10-22",
        "months": [],
        "projects": [],
        "totals": [],
        "known_hours": 0,
        "partial": False,
    }
    assert "'=1+1" in csv_report(data)


def test_date_range_includes_both_edges_and_excludes_other_days(source):
    entry("before", date(2026, 9, 9), 20)
    entry("first", date(2026, 9, 10), 2)
    entry("last", date(2026, 9, 20), 3)
    entry("after", date(2026, 9, 21), 40)
    data = account_hours.load_account_hours(
        "Oxxo", 2026, start=date(2026, 9, 10), end=date(2026, 9, 20)
    )
    assert data["known_hours"] == 5
    assert [m["key"] for m in data["months"]] == ["2026-09"]
    assert data["months"][0]["partial"]
    assert data["start"] == "2026-09-10"
    assert data["end"] == "2026-09-20"


def test_range_across_years_keeps_december_and_january_separate(source):
    run = SyncRun.objects.first()
    ClockifyMonthSync.objects.create(
        month=date(2025, 12, 1),
        entries_count=0,
        total_seconds=0,
        synced_at=timezone.now(),
        run=run,
    )
    entry("dec", date(2025, 12, 31), 4)
    entry("jan", date(2026, 1, 1), 2)
    data = account_hours.load_account_hours(
        "Oxxo", 2025, start=date(2025, 12, 31), end=date(2026, 1, 1)
    )
    assert [m["key"] for m in data["months"]] == ["2025-12", "2026-01"]
    assert [t["hours"] for t in data["totals"]] == [4, 2]
    assert [m["label"] for m in data["months"]] == ["Dic 2025", "Ene 2026"]


def test_project_filter_and_csv_recalculate_the_same_range(client, source):
    entry("base", date(2026, 9, 10), 2)
    entry("sprint", date(2026, 9, 10), 3, "S1 - trabajo")
    query = {
        "nombre": "Oxxo",
        "desde": "2026-09-10",
        "hasta": "2026-09-10",
        "proyecto": ["P.001_S1"],
    }
    response = client.get(URL, query)
    assert response.status_code == 200
    data = response.json()["data"]
    assert [p["id"] for p in data["projects"]] == ["P.001_S1"]
    assert data["known_hours"] == data["totals"][0]["hours"] == 3
    csv = client.get(URL, {**query, "descargar": "csv"}).content.decode(
        "utf-8-sig"
    )
    assert "P.001_S1" in csv
    assert "\r\nP.001," not in csv
    both = client.get(URL, {**query, "proyecto": ["P.001", "P.001_S1"]}).json()[
        "data"
    ]
    assert both["known_hours"] == 5


def test_invalid_range_and_foreign_project_are_rejected(client, source):
    for extra in (
        {"desde": "2026-09-01"},
        {"desde": "2026-09-20", "hasta": "2026-09-01"},
        {"desde": "2020-01-01", "hasta": "2026-09-01"},
        {"desde": "bad", "hasta": "2026-09-01"},
        {"proyecto": "OTHER"},
    ):
        assert client.get(URL, {"nombre": "Oxxo", **extra}).status_code == 400
