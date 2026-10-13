from apps.portal.services.facturability import build_month_facturability
from apps.portal.services.roster import apply_roster, attach_month_roster
from tests.fakes import InMemorySheetRepository

GSE = {
    "areas": [{"area": "DEV", "recursos": 2, "personas": []}],
    "detalle": [
        {
            "recurso": "Magda Perla Gonzalez Saenz",
            "area": "DEV",
            "servicio": "AER",
            "horas": 100,
            "categorias": ["Facturable"],
        },
        {
            "recurso": "Cesar Meza Hernandez",
            "area": "DEV",
            "servicio": "AER",
            "horas": 9,
            "categorias": ["Facturable"],
        },
    ],
}
PEOPLE = [
    {"nombre": "Magda Perla González Sáenz", "rol": "DEV"},
    {"nombre": "Karina Marmol", "rol": "DEV"},
]


def test_capacity_counts_only_roster_people_with_registered_hours() -> None:
    gse = apply_roster(GSE, PEOPLE)
    month = build_month_facturability("2026-09", gse)

    assert month.resources == 1
    assert month.capacity == 21 * 8


def test_hours_of_people_outside_the_roster_are_dropped() -> None:
    gse = apply_roster(GSE, PEOPLE)
    month = build_month_facturability("2026-09", gse)

    assert month.fixed_hours == 100


def test_roster_reads_only_monthly_bands_without_resources_or_mpb():
    reader = InMemorySheetRepository({
        "Bandas/rol": [
            ["Nombre", "Septiembre", "ROL", "Octubre"],
            ["Magda Perla González Sáenz", "B2", "DEV", "BAJA"],
            ["Karina Marmol", "B1", "DEV", "B1"],
            ["Cesar Meza Hernandez", "BAJA", "DEV", "BAJA"],
            ["No vigente", "NA", "DEV", ""],
            ["Sin banda", "", "DEV", ""],
        ],
    })
    source = attach_month_roster(GSE, reader, "2026-09")
    result = apply_roster(source, source["plantilla"])
    month = build_month_facturability("2026-09", result)
    assert month.resources == 1
    assert month.fixed_hours == 100
    assert month.capacity == 168
    assert [p["nombre"] for p in result["areas"][0]["personas"]] == [
        "Magda Perla González Sáenz",
    ]
    october = attach_month_roster(GSE, reader, "2026-10")
    assert october["plantilla"] == [{"nombre": "Karina Marmol", "rol": "DEV"}]


def test_missing_historical_band_keeps_hours_with_notice():
    reader = InMemorySheetRepository({
        "Bandas/rol": [["Nombre", "Septiembre", "ROL"], ["Ana", "B1", "DEV"]],
    })
    result = attach_month_roster(GSE, reader, "2026-01")
    assert "plantilla" not in result
    assert result["detalle"] == GSE["detalle"]
    assert "2026-01" in result["plantillaAviso"]
    assert build_month_facturability("2026-01", result).notice


def test_person_with_only_non_billable_hours_counts_for_capacity():
    gse = {
        "detalle": [{
            "recurso": "Ana", "area": "DEV", "horas": 10,
            "servicio": "IXB", "categorias": ["No facturable"],
        }],
    }
    result = apply_roster(gse, [{"nombre": "Ana", "rol": "DEV"}])
    month = build_month_facturability("2026-09", result)
    assert month.resources == 1
    assert month.capacity == 168
    assert month.fixed_hours + month.variable_hours == 0
    assert month.global_percent == 0
