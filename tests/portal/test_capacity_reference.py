import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.datastore.models import SheetSnapshot
from apps.portal.services.capacity_reference import HEADERS, REFERENCE_SHEET
from apps.portal.services.clockify_capacity import capacity_report
from apps.portal.services.facturability import build_month_facturability
from apps.portal.services.roster import apply_roster
from tests.portal.test_clockify_capacity import (
    clockify_capacity as clockify_capacity,
)

pytestmark = pytest.mark.django_db


@pytest.mark.usefixtures("clockify_capacity")
def test_referencia_excel_no_sustituye_bandas_ni_horas_clockify():
    SheetSnapshot.objects.create(
        name=REFERENCE_SHEET,
        synced_at=timezone.now(),
        rows=[
            HEADERS,
            ["2026-10", "Ana", "DEV", 80, "GSE"],
            ["2026-10", "Luis", "QA", 0, "GSE"],
        ],
    )
    report = capacity_report("2026-10")
    assert report["summary"]["base"] == 352
    people = {person["name"]: person for person in report["people"]}
    assert people["Luis"]["base"] == 176
    assert people["Luis"]["billable"] == 2
    assert people["Ana"]["base"] == 176
    assert capacity_report("2026-10", 4)["summary"]["base"] == 176


def test_facturabilidad_usa_la_misma_capacidad_de_referencia():
    people = [
        {"nombre": "Ana", "rol": "DEV", "capacidad_horas": 80},
        {"nombre": "Luis", "rol": "QA", "capacidad_horas": 0},
    ]
    gse = apply_roster(
        {
            "capacidadInicial": True,
            "detalle": [
                {
                    "recurso": "Luis",
                    "area": "QA",
                    "servicio": "IXB",
                    "categorias": ["Facturable"],
                    "horas": 20,
                }
            ],
        },
        people,
    )
    result = build_month_facturability("2026-10", gse)
    assert result.capacity == 80
    assert result.variable_hours == 20
    assert result.global_percent == 25


def test_importacion_repetible_conserva_meses_fuera_del_rango(monkeypatch):
    from apps.datastore.management.commands import (
        import_capacity_reference as command,
    )

    SheetSnapshot.objects.create(
        name=REFERENCE_SHEET,
        synced_at=timezone.now(),
        rows=[HEADERS, ["2025-09", "Ana", "DEV", 100, "anterior"]],
    )
    monkeypatch.setattr(
        command,
        "read_reference",
        lambda *args: [
            ["2026-08", "Ana", "DEV", 168, "GSE"],
            ["2026-09", "Ana", "DEV", 80, "GSE"],
        ],
    )
    for _ in range(2):
        call_command(
            "import_capacity_reference",
            "prueba.xlsx",
            year=2026,
            from_month=9,
            through=9,
        )
    rows = SheetSnapshot.objects.get(name=REFERENCE_SHEET).rows
    assert rows == [
        HEADERS,
        ["2025-09", "Ana", "DEV", 100, "anterior"],
        ["2026-09", "Ana", "DEV", 80, "GSE"],
    ]


def test_facturabilidad_del_reporte_no_suma_saas_roc_ni_sin_servicio():
    gse = apply_roster(
        {
            "capacidadInicial": True,
            "serviciosFacturables": ["AER", "TYM", "IXB", "RAAS"],
            "detalle": [
                {
                    "recurso": "Ana",
                    "area": "DEV",
                    "servicio": service,
                    "categorias": ["Facturable"],
                    "horas": hours,
                }
                for service, hours in [
                    ("AER", 10),
                    ("TYM", 20),
                    ("ROC", 30),
                    ("SaaS", 50),
                    ("NA", 40),
                ]
            ],
        },
        [{"nombre": "Ana", "rol": "DEV", "capacidad_horas": 100}],
    )
    result = build_month_facturability("2026-09", gse)
    assert result.fixed_hours == 10
    assert result.variable_hours == 20
    assert result.global_percent == 30
