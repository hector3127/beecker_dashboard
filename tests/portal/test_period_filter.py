from datetime import date

from apps.portal.schemas import SpecialtyRow
from apps.portal.services.facturability import (
    build_month_facturability,
    combine_months,
    merge_specialties,
)
from apps.portal.services.period_filter import (
    build_period,
    build_picker,
    parse_period,
)

TODAY = date(2026, 10, 13)


def test_default_period_is_the_current_month():
    period = parse_period({}, TODAY)

    assert period.kind == "mes"
    assert period.months == ("2026-10",)
    assert period.label == "Octubre 2026"


def test_legacy_month_parameter_still_works():
    period = parse_period({"mes": "2026-02"}, TODAY)

    assert period.months == ("2026-02",)
    assert period.end_month == "2026-02"


def test_quarter_and_year_stop_at_the_current_month():
    quarter = parse_period(
        {"periodo": "trimestre", "anio": "2026", "trim": "4"}, TODAY
    )
    year = parse_period({"periodo": "anio", "anio": "2026"}, TODAY)
    past = parse_period({"periodo": "anio", "anio": "2025"}, TODAY)

    assert quarter.months == ("2026-10",)
    assert quarter.label == "T4 2026"
    assert year.months[0] == "2026-01"
    assert year.end_month == "2026-10"
    assert len(past.months) == 12


def test_future_values_are_clamped_and_garbage_is_ignored():
    future_month = parse_period({"mes": "2027-05"}, TODAY)
    future_year = parse_period({"periodo": "anio", "anio": "2030"}, TODAY)
    garbage = parse_period({"periodo": "x", "mes": "hola"}, TODAY)

    assert future_month.months == ("2026-10",)
    assert future_year.label == "2026"
    assert garbage.months == ("2026-10",)


def test_quarter_after_today_falls_back_to_the_current_quarter():
    period = build_period("trimestre", 2026, 4, date(2026, 8, 5))

    assert period.quarter == 3
    assert period.months == ("2026-07", "2026-08")


def test_picker_marks_the_active_option_and_keeps_other_filters():
    period = parse_period(
        {"periodo": "trimestre", "anio": "2026", "trim": "3"}, TODAY
    )
    picker = build_picker(period, TODAY, {"roles": ["1"], "rol": ["DEV"]})
    current = next(item for item in picker.by_year if item.year == 2026)
    active = [link.label for link in current.quarters if link.active]

    assert picker.label == "T3 2026"
    assert picker.kind == "trimestre"
    assert active == ["T3"]
    assert current.quarters[3].disabled is False
    assert current.months[10].disabled is True
    assert current.months[9].disabled is False
    assert current.months[0].href == (
        "?roles=1&rol=DEV&periodo=mes&mes=2026-01"
    )
    assert picker.query == "?periodo=trimestre&anio=2026&trim=3"
    assert ("trim", "3") in picker.hidden


def test_picker_has_only_year_quarter_and_month_options():
    picker = build_picker(parse_period({}, TODAY), TODAY, {})

    assert [item.year for item in picker.by_year] == [2024, 2025, 2026]
    assert [link.label for link in picker.years] == ["2024", "2025", "2026"]
    assert not hasattr(picker, "presets")
    assert all(not link.disabled for link in picker.by_year[0].months)


def month(key, gse_hours, error=""):
    gse = {
        "areas": [{"area": "DEV", "recursos": 2, "personas": []}],
        "detalle": [
            {
                "recurso": "Ana",
                "area": "DEV",
                "servicio": "AER",
                "horas": gse_hours,
                "categorias": ["Facturable"],
            },
            {
                "recurso": "Beto",
                "area": "DEV",
                "servicio": "TYM",
                "horas": 10,
                "categorias": ["Facturable"],
            },
        ],
    }

    return build_month_facturability(key, gse, error)


def test_combine_months_sums_hours_and_recomputes_percents():
    first, second = month("2026-01", 100), month("2026-02", 50, "sin base")

    total = combine_months([first, second], "T1 2026", "T1 2026")

    assert total.capacity == first.capacity + second.capacity
    assert total.fixed_hours == 150
    assert total.variable_hours == 20
    assert total.fixed_percent == round(150 * 100 / total.capacity, 2)
    assert total.service_hours[0] == 20
    assert total.label == "T1 2026"
    assert total.error == "sin base"
    assert total.resources == 2


def test_combine_single_month_returns_it_unchanged():
    only = month("2026-01", 100)

    assert combine_months([only], "Enero", "Enero") is only


def test_merge_specialties_sums_and_averages():
    def row(capacity, fixed, variable, people):
        return SpecialtyRow(
            name="Dev",
            headcount=people,
            capacity=capacity,
            fixed_hours=fixed,
            fixed_percent=None,
            variable_hours=variable,
            variable_percent=None,
            free_fte=2,
        )

    merged = merge_specialties(
        [(row(300.0, 100.0, 50.0, 2),), (row(100.0, 50.0, 25.0, 3),)]
    )

    assert len(merged) == 1
    assert merged[0].capacity == 400.0
    assert merged[0].fixed_hours == 150.0
    assert merged[0].fixed_percent == 37.5
    assert merged[0].variable_percent == round(75 * 100 / 250, 2)
    assert merged[0].headcount == 3
