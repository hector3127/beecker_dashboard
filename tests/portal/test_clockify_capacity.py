"""La capacidad incluye todos los registros salvo el ID de Comida."""

from datetime import date
from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry, SyncRun
from apps.portal.services.clockify_capacity import (
    FOOD_PROJECT_ID,
    capacity_report,
)
from apps.portal.services.operational_sources import legacy_capacity

pytestmark = pytest.mark.django_db


@pytest.fixture
def clockify_capacity(settings, monkeypatch):
    settings.CLOCKIFY_STORE_ENABLED = True

    class Reader:
        rows = [
            ["Nombre", "ROL", "ID Clockify", "Septiembre", "Octubre"],
            ["Ana", "DEV", "Ana", "B1", "B2"],
            ["Luis", "QA", "Luis", "B1", "B1"],
            ["Only Food", "Administración", "Only Food", "B1", "B1"],
            ["Baja", "DEV", "Baja", "B1", "Baja"],
        ]

        def sheet_exists(self, name):
            assert name != "Recursos"
            return name == "Bandas/rol"

        def read_values(self, name):
            assert name == "Bandas/rol"
            return self.rows

        def read_as_objects(self, name):
            assert name != "Recursos"
            return []

    reader = Reader()
    monkeypatch.setattr(
        "apps.portal.services.capacity_roster.build_sheet_repository",
        lambda: reader,
    )
    monkeypatch.setattr(
        "apps.portal.api.capacity_daily.build_sheet_repository", lambda: reader
    )
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.build_sheet_repository",
        lambda: reader,
    )
    run = SyncRun.objects.create(kind="test")
    ClockifyMonthSync.objects.create(
        month=date(2026, 10, 1),
        entries_count=7,
        total_seconds=31 * 3600,
        synced_at=timezone.now(),
        run=run,
    )
    for index, (pid, name, person, hours, billable, day) in enumerate(
        [
            ("admin", "Administrative Activities", "Ana", 6, False, 1),
            ("nyb", "TYM.NYB.009", "Ana", 5, True, 1),
            ("roc", "ROC.AIN.001", "Ana", 3, True, 2),
            ("weekend", "Other", "Luis", 4, False, 3),
            ("another", "Comida", "Luis", 2, True, 4),
            (FOOD_PROJECT_ID, "Comida", "Ana", 8, False, 1),
            (FOOD_PROJECT_ID, "Comida", "Only Food", 3, False, 1),
        ]
    ):
        ClockifyTimeEntry.objects.create(
            entry_id=str(index),
            project_id=pid,
            project_name=name,
            user_id=person,
            user_name=person,
            month=date(2026, 10, 1),
            entry_date=date(2026, 10, day),
            duration_seconds=hours * 3600,
            billable=billable,
            description="Registro completo",
            task_name="Tarea",
            tags=["Etiqueta"],
        )

    return reader


def test_complete_scope_and_single_id_exclusion(clockify_capacity):
    with patch(
        "apps.portal.services.operational_sources.build_sheet_repository",
        return_value=clockify_capacity,
    ):
        report = capacity_report("2026-10")
        card = legacy_capacity("2026-10")
    s = report["summary"]
    assert all(
        card[key] == s[key]
        for key in ("base", "consumed", "billable", "available")
    )
    assert s["consumed"] == 20 and s["billable"] == 10
    assert s["nonbillable"] == 10
    assert s["base"] == 352 and s["available"] == 332
    assert s["registered_people"] == 2 and s["projects"] == 5
    assert s["clockify_month"]["entries"] == 5
    assert s["over"] == 1
    assert {p["id"] for p in report["projects"]} == {
        "admin",
        "nyb",
        "roc",
        "weekend",
        "another",
    }
    assert sum(p["hours"] for p in report["projects"]) == 20
    assert sum(p["hours"] for p in report["people"]) == 20
    assert {p["name"]: p["projects"] for p in report["people"]} == {
        "Ana": 3,
        "Luis": 2,
    }
    assert capacity_report("2026-10", 6)["summary"]["base"] == 264


def test_overcapacity_remains_negative_and_never_hides_hours(clockify_capacity):
    ClockifyTimeEntry.objects.filter(entry_id="0").update(
        duration_seconds=400 * 3600
    )
    s = capacity_report("2026-10")["summary"]
    assert s["consumed"] == 414
    assert s["available"] == -62


def test_missing_month_is_unknown(settings):
    settings.CLOCKIFY_STORE_ENABLED = True
    assert capacity_report("2026-09")["ok"] is False
    assert "summary" not in capacity_report("2026-09")
    settings.CLOCKIFY_STORE_ENABLED = False
    assert capacity_report("2026-10")["ok"] is False


def test_capacity_api_and_csv_use_same_clockify_scope(
    client, clockify_capacity, settings
):
    settings.ACCESS_ENFORCED = False
    settings.PORTAL_LOGIN_REQUIRED = False
    response = client.get(
        "/api/v1/screens/capacidad/diaria/", {"mes": "2026-10"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["resumen"]["registradas"] == 20
    csv = client.get(reverse("portal:capacidad_csv"), {"mes": "2026-10"})
    assert csv.status_code == 200
    text = csv.content.decode("utf-8-sig")
    assert FOOD_PROJECT_ID not in text and "Only Food" not in text
    assert "TYM.NYB.009" in text and "Administrative Activities" in text
    assert (
        "Registro completo" in text and "Etiqueta" in text and "Tarea" in text
    )
    filtered = client.get(
        reverse("portal:capacidad_csv"), {"mes": "2026-10", "persona": "Ana"}
    ).content.decode("utf-8-sig")
    assert "Luis" not in filtered and "Ana" in filtered
    assert (
        client.get(
            reverse("portal:capacidad_csv"), {"mes": "2026-09"}
        ).status_code
        == 503
    )


def test_operations_roster_excludes_other_roles_and_inactive(clockify_capacity):
    reader = clockify_capacity
    reader.rows += [["Sin horas", "BA", "zero", "B1", "B3"]]
    for pid in ("Only Food", "Baja", "Outside"):
        ClockifyTimeEntry.objects.create(
            entry_id=pid,
            project_id="nyb",
            project_name="TYM.NYB.009",
            user_id=pid,
            user_name=pid,
            month=date(2026, 10, 1),
            entry_date=date(2026, 10, 2),
            duration_seconds=360000,
        )
    result = capacity_report("2026-10")
    assert result["summary"]["consumed"] == 20
    assert result["summary"]["base"] == 528
    assert len(result["people"]) == 3
    zero = next(p for p in result["matrix"] if p["name"] == "Sin horas")
    assert zero["hours"] == 0 and zero["band"] == "B3"
    ana = next(
        p for p in result["matrix"] if p["project_name"] == "TYM.NYB.009"
    )
    assert (
        ana["clockify_id"] == "Ana"
        and ana["band"] == "B2"
        and ana["role"] == "Dev"
    )
    assert ana["daily"] == {"2026-10-01": 5}


def test_missing_roster_never_falls_back_to_everyone(clockify_capacity):
    clockify_capacity.rows[0] = ["Nombre", "ROL", "ID Clockify"]
    result = capacity_report("2026-10")
    assert not result["ok"] and "columna de banda" in result["error"]


def test_matching_id_has_priority_over_name(clockify_capacity):
    ClockifyTimeEntry.objects.filter(entry_id="0").update(
        user_name="Nombre cambiado"
    )
    assert capacity_report("2026-10")["summary"]["consumed"] == 20
    ClockifyTimeEntry.objects.filter(entry_id="0").update(
        user_id="another-id", user_name="Ana"
    )
    assert capacity_report("2026-10")["summary"]["consumed"] == 14


def test_delivery_manager_and_project_title_are_confirmed(clockify_capacity):
    from apps.datastore.models import (
        EvaAzureSource,
        EvaExtraction,
        EvaScopeSnapshot,
    )

    run = EvaExtraction.objects.create(
        cut=date(2026, 10, 28),
        started_at=timezone.now(),
        published=True,
        metrics={"kind": "summary_inventory"},
    )
    source = EvaAzureSource.objects.create(
        extraction=run, azure_id="nyb", name="TYM.NYB.009", payload={}
    )
    EvaScopeSnapshot.objects.create(
        source=source,
        project_id="TYM.NYB.009",
        scope="General",
        row={
            "fields": {
                "delivery_manager": "Delivery NYB",
                "project_name": "Trabajo NYB",
            }
        },
    )
    result = capacity_report("2026-10")
    nyb = next(
        r for r in result["matrix"] if r["project_name"] == "TYM.NYB.009"
    )
    assert (
        nyb["manager"] == "Delivery NYB"
        and nyb["project_title"] == "Trabajo NYB"
    )
    assert nyb["business_id"] == "TYM.NYB.009"
    assert (
        sum(r["hours"] for r in result["matrix"])
        == result["summary"]["consumed"]
    )
