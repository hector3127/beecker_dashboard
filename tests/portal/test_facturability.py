"""Facturabilidad con la logica de GSE · Horas por area."""

from datetime import date

from apps.portal.services.facturability import (
    build_month_facturability,
    build_resources,
    build_specialties,
    default_role_keys,
    display_role,
    list_roles,
    normalize_service,
    person_month_hours,
    role_key,
    team_averages,
)

BILLABLE = ["Facturable"]
NOT_BILLABLE = ["No Facturables", "Internos"]


def gse(areas, *rows):
    """areas: {area: [personas]}; rows: (persona, area, servicio, h, cats)."""
    return {
        "ok": True,
        "areas": [
            {
                "area": name,
                "recursos": len(people),
                "personas": [{"nombre": person} for person in people],
            }
            for name, people in areas.items()
        ],
        "detalle": [
            {
                "recurso": person,
                "area": area,
                "servicio": service,
                "horas": hours,
                "categorias": categories,
            }
            for person, area, service, hours, categories in rows
        ],
    }


OCT = gse(
    {"DEV": ["Ana", "Luis"], "QA": ["Eva"], "DM": ["Dan"]},
    ("Ana", "DEV", "AER", 100, BILLABLE),
    ("Ana", "DEV", "AER", 30, NOT_BILLABLE),
    ("Ana", "DEV", "T&M", 20, BILLABLE),
    ("Luis", "DEV", "IXB", 30, BILLABLE),
    ("Eva", "QA", "RaaS", 10, BILLABLE),
    ("Eva", "QA", "SaaS", 5, BILLABLE),
    ("Eva", "QA", "NA", 4, BILLABLE),
    ("Dan", "DM", "AER", 50, BILLABLE),
)


def test_normalize_service():
    assert normalize_service("T&M") == "TYM"
    assert normalize_service("t & m") == "TYM"
    assert normalize_service("RaaS") == "RAAS"
    assert normalize_service(" aer ") == "AER"
    assert normalize_service(None) == ""


def test_person_month_hours_uses_business_days():
    assert person_month_hours("2026-10") == 176
    assert person_month_hours("2026-09") == 168
    assert person_month_hours("2026-10", date(2026, 10, 12)) == 64


def test_month_follows_gse_logic():
    month = build_month_facturability("2026-10", OCT)

    assert month.label == "Octubre"
    assert month.resources == 4
    assert month.capacity == 4 * 176
    assert month.fixed_hours == 150
    assert month.service_hours == (20, 30, 5, 10)
    assert month.other_hours == 4
    assert month.variable_hours == 69
    assert month.fixed_percent == 21.31
    assert month.variable_percent == 12.45
    assert month.global_percent == 31.11
    assert month.fixed_hc == 1
    assert month.free_hours == 704 - 150 - 69
    assert month.free_fte == 3


def test_month_with_operational_roles_only():
    roles = default_role_keys(list_roles([OCT]))

    month = build_month_facturability("2026-10", OCT, scope=(roles, None))

    assert roles == frozenset({"dev", "qa"})
    assert month.capacity == 3 * 176
    assert month.fixed_hours == 100


def test_month_without_data():
    month = build_month_facturability("2026-02", {}, "sin base")

    assert month.capacity == 0
    assert month.fixed_percent is None
    assert month.global_percent is None
    assert month.bar_height == 0
    assert month.error == "sin base"


def test_specialties_by_area():
    rows = build_specialties(OCT, "2026-10")

    assert [row.name for row in rows] == ["Dev", "DM", "QA"]
    dev = rows[0]
    assert (dev.headcount, dev.capacity, dev.fixed_hours) == (2, 352, 100)
    assert dev.fixed_percent == 28.41
    assert dev.variable_hours == 50
    assert dev.variable_percent == 19.84
    assert dev.free_fte == 1


def test_resources_by_month_and_team_average():
    september = gse(
        {"DEV": ["Ana"]},
        ("Ana", "DEV", "AER", 84, BILLABLE),
    )

    rows = build_resources([("2026-09", september), ("2026-10", OCT)])
    by_name = {row.name: row for row in rows}

    assert by_name["Ana"].percents == (50.0, 68.18)
    assert by_name["Luis"].percents == (None, 17.05)
    assert by_name["Eva"].role == "QA"
    by_month, overall = team_averages(rows, 2)
    assert by_month[0] == 50.0
    assert overall is not None


def test_resources_count_people_without_billable_hours_as_zero():
    data = gse({"QA": ["Eva"]}, ("Eva", "QA", "NA", 10, NOT_BILLABLE))

    assert build_resources([("2026-10", data)])[0].percents == (0.0,)
    assert build_resources([("2026-10", {})]) == ()


def test_roles_list_and_key():
    assert list_roles([OCT]) == ("DEV", "DM", "QA")
    assert role_key("") == "sin rol"


def test_only_operational_areas_by_default():
    roles = (
        "DEV",
        "BA",
        "SM",
        "ARQ",
        "QA",
        "R&D",
        "ROC",
        "Plataforma",
        "QC",
        "DM",
        "Comercial",
        "Pre-ventas",
        "Soporte",
    )

    keys = default_role_keys(roles)

    assert keys == frozenset({"dev", "roc", "ba", "sm", "arq", "qa"})
    assert display_role("QA") == "QA"
    assert display_role("R&D") == "R&D"
    assert display_role("ARQ") == "Arq"
    assert display_role("ROC") == "ROC"
    assert display_role("Plataforma") == "Plataforma"
    assert display_role("") == "Sin rol"
