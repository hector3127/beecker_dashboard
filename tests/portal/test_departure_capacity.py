"""El estimado se recorta solo ante baja explicita y datos diarios completos."""

from datetime import date

import pytest
from django.utils import timezone

from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry, SyncRun
from apps.portal.services.facturability import (
    build_month_facturability,
    build_resources,
    build_specialties,
)
from apps.portal.services.roster import apply_roster, attach_month_roster
from tests.fakes import InMemorySheetRepository

pytestmark = pytest.mark.django_db


def source(settings):
    settings.CLOCKIFY_STORE_ENABLED = True
    run = SyncRun.objects.create(kind="test")
    ClockifyMonthSync.objects.create(
        month=date(2026, 9, 1),
        entries_count=3,
        total_seconds=10800,
        synced_at=timezone.now(),
        run=run,
    )
    reader = InMemorySheetRepository(
        {
            "Bandas/rol": [
                [
                    "Nombre",
                    "ROL",
                    "ID Clockify",
                    "Agosto",
                    "Septiembre",
                    "Octubre",
                ],
                ["Ana", "DEV", "ana", "B1", "B1", "BAJA"],
                ["Luis", "DEV", "luis", "B1", "B1", "BAJA"],
                ["Eva", "DEV", "eva", "B1", "B1", "B1"],
                ["Sin registros", "DEV", "none", "B1", "B1", "BAJA"],
                ["Salida mes", "DEV", "exit", "B1", "BAJA", "BAJA"],
            ]
        }
    )
    for i, (uid, day) in enumerate(
        [("ana", 14), ("luis", 17), ("eva", 3), ("exit", 11)]
    ):
        ClockifyTimeEntry.objects.create(
            entry_id=str(i),
            user_id=uid,
            user_name="Alias " + uid,
            project_id="p",
            month=date(2026, 9, 1),
            entry_date=date(2026, 9, day),
            duration_seconds=3600,
        )
    gse = {
        "detalle": [
            {
                "recurso": n,
                "area": "DEV",
                "servicio": "AER",
                "horas": 10,
                "categorias": ["Facturable"],
            }
            for n in ["Ana", "Luis", "Eva", "Salida mes"]
        ]
    }
    return reader, gse


def test_estimates_match_ids_preserve_active_and_exclude_holiday(settings):
    reader, gse = source(settings)
    attached = attach_month_roster(gse, reader, "2026-09")
    estimates = {
        p["nombre"]: p.get("capacidad_horas") for p in attached["plantilla"]
    }
    assert estimates == {
        "Ana": 80,
        "Luis": 96,
        "Eva": None,
        "Sin registros": 0,
        "Salida mes": 72,
    }
    result = apply_roster(attached, attached["plantilla"])
    month = build_month_facturability("2026-09", result)
    assert month.capacity == 80 + 96 + 168 + 72
    assert month.fixed_hours == 40
    assert build_specialties(result, "2026-09")[0].capacity == month.capacity
    resources = {r.name: r for r in build_resources([("2026-09", result)])}
    assert resources["Ana"].percents == (12.5,)
    assert resources["Luis"].percents == (10.42,)
    assert resources["Eva"].percents == (5.95,)


def test_missing_clockify_month_does_not_invent_departure_date(settings):
    reader, gse = source(settings)
    ClockifyMonthSync.objects.all().delete()
    attached = attach_month_roster(gse, reader, "2026-09")
    assert all("capacidad_horas" not in p for p in attached["plantilla"])
    assert "Salida mes" not in [p["nombre"] for p in attached["plantilla"]]
