"""Facturabilidad con horas de GSE y capacidad de Recursos."""

from apps.portal.services.facturability import (
    build_month_facturability,
    build_resources,
    build_specialties,
    normalize_service,
    person_month_hours,
    team_averages,
)


def gse(*rows):
    return {
        "ok": True,
        "detalle": [
            {"recurso": name, "area": area, "servicio": service, "horas": hours}
            for name, area, service, hours in rows
        ],
    }


def capacity(*rows):
    return {
        "filas": [
            {
                "recurso": name,
                "rol": role,
                "horasEstimadas": hours,
                "activo": active,
            }
            for name, role, hours, active in rows
        ],
    }


GSE_OCT = gse(
    ("Ana", "DEV", "AER", 100),
    ("Ana", "DEV", "T&M", 20),
    ("Luis", "DEV", "IXB", 30),
    ("Eva", "QA", "RaaS", 10),
    ("Eva", "QA", "SaaS", 5),
    ("Eva", "QA", "Interno", 40),
)
CAPACITY = capacity(
    ("Ana", "DEV", 150, True),
    ("Luis", "DEV", 100, True),
    ("Eva", "QA", 100, True),
    ("Baja", "QA", 500, False),
)


def test_normalize_service():
    assert normalize_service("T&M") == "TYM"
    assert normalize_service("t & m") == "TYM"
    assert normalize_service("RaaS") == "RAAS"
    assert normalize_service(" aer ") == "AER"
    assert normalize_service(None) == ""


def test_person_month_hours_uses_workdays_by_eight():
    assert person_month_hours("2026-10") == 176


def test_month_totals_follow_the_formula():
    month = build_month_facturability("2026-10", GSE_OCT, CAPACITY)

    assert month.label == "Octubre"
    assert month.short_label == "Oct"
    assert month.capacity == 350
    assert month.fixed_hours == 100
    assert month.fixed_percent == 28.57
    assert month.fixed_hc == 1
    assert month.variable_capacity == 250
    assert month.variable_hours == 65
    assert month.service_hours == (20, 30, 5, 10)
    assert month.variable_percent == 26.0
    assert month.free_hours == 185
    assert month.free_fte == 1
    assert month.global_percent == 47.14
    assert month.bar_height == 42.9


def test_month_without_data():
    month = build_month_facturability("2026-02", {}, {}, "sin base")

    assert month.capacity == 0
    assert month.fixed_percent is None
    assert month.global_percent is None
    assert month.bar_height == 0
    assert month.error == "sin base"


def test_specialties():
    rows = build_specialties(GSE_OCT, CAPACITY, "2026-10")

    assert [row.name for row in rows] == ["DEV", "QA"]
    dev, qa = rows
    assert (dev.headcount, dev.capacity, dev.fixed_hours) == (2, 250, 100)
    assert dev.fixed_percent == 40.0
    assert dev.variable_hours == 50
    assert dev.variable_percent == 33.33
    assert dev.free_fte == 1
    assert (qa.headcount, qa.fixed_percent, qa.variable_hours) == (1, 0.0, 15)


def test_specialty_only_in_gse_has_no_capacity():
    rows = build_specialties(gse(("X", "", "AER", 10)), {}, "2026-10")

    assert rows[0].name == "Sin rol"
    assert rows[0].fixed_percent is None


def test_resources_by_month_and_team_average():
    months = [
        (gse(("Ana", "DEV", "AER", 75)), capacity(("Ana", "DEV", 150, True))),
        (GSE_OCT, CAPACITY),
    ]

    rows = build_resources(months)
    by_name = {row.name: row for row in rows}

    assert by_name["Ana"].percents == (50.0, 80.0)
    assert by_name["Ana"].average == 65.0
    assert by_name["Luis"].percents == (None, 30.0)
    assert by_name["Eva"].percents == (None, 15.0)
    by_month, overall = team_averages(rows, 2)
    assert by_month == (50.0, 41.7)
    assert overall == 36.7
