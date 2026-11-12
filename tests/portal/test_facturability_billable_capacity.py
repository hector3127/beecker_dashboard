from apps.gse.constants import BILLABLE, NON_BILLABLE
from apps.gse.services.base_store import HourRecord
from apps.gse.services.catalog import Catalog, CatalogEntry
from apps.gse.services.cells import norm
from apps.gse.services.month_report import AreaTotal, MonthTotals, add_record
from apps.gse.services.roster import Person
from apps.portal.services.facturability import person_month_hours
from apps.portal.services.roster import apply_roster


def test_billable_del_registro_prevalece_sobre_catalogo_solo_al_solicitarlo():
    catalog = Catalog(
        entries={
            norm("AMK.001"): CatalogEntry(
                "proyecto", "facturable", "Proyecto", "Facturable", "RaaS"
            )
        }
    )
    person = Person("Ana", "DEV", False, "u", "A1")
    record = HourRecord(
        "1", "u", "Ana", "AMK.001", "", [], False, "2026-10-01", 8
    )
    original = MonthTotals()
    changed = MonthTotals()
    add_record(record, person, (catalog, AreaTotal("DEV")), original)
    add_record(record, person, (catalog, AreaTotal("DEV")), changed, True)
    assert BILLABLE in next(iter(original.detail.values()))["categorias"]
    assert BILLABLE not in next(iter(changed.detail.values()))["categorias"]
    assert NON_BILLABLE in next(iter(changed.detail.values()))["categorias"]


def test_capacidad_inicial_incluye_personas_sin_registros():
    people = [{"nombre": "Ana", "rol": "DEV"}, {"nombre": "Luis", "rol": "DEV"}]
    result = apply_roster({"capacidadInicial": True, "detalle": []}, people)
    assert result["areas"][0]["recursos"] == 2
    assert apply_roster({"detalle": []}, people)["areas"] == []


def test_calendario_mensual_aprobado_incluye_medio_dia_y_descanso_de_julio():
    assert person_month_hours("2026-04") == 164
    assert person_month_hours("2026-07") == 176
    assert person_month_hours("2026-10") == 176


def test_facturables_sin_banda_se_conservan_con_capacidad_cero():
    gse = {
        "capacidadInicial": True,
        "detalle": [
            {
                "recurso": "Ana",
                "area": "DEV",
                "servicio": "IXB",
                "categorias": [BILLABLE],
                "horas": 8,
            },
            {
                "recurso": "Ana",
                "area": "DEV",
                "servicio": "IXB",
                "categorias": [NON_BILLABLE],
                "horas": 4,
            },
        ],
    }
    result = apply_roster(gse, [])
    assert result["areas"] == []
    assert len(result["detalle"]) == 1
    assert result["detalle"][0]["horas"] == 8
    assert result["capacidadPorPersona"]["ana"] == 0


def test_tipo_residente_y_producto_explicitos_aportan_cero():
    from apps.gse.services.roster import RosterSheet
    from apps.portal.services.roster import excluded_capacity_rows

    rows = [
        ["Nombre", "Tipo recurso", "Departamento", "Septiembre"],
        ["Ana", "Empleado", "Producto", "A1"],
        ["Luis", "Residente", "Servicios", "R"],
        ["Eva", "Empleado", "Servicios", "B2"],
    ]
    sheet = RosterSheet(
        rows, 0, ["nombre", "tipo recurso", "departamento", "septiembre"]
    )
    assert excluded_capacity_rows(sheet, 3) == {"ana", "luis"}


def test_historico_cuenta_horas_sin_billable_y_octubre_conserva_la_marca():
    catalog = Catalog(
        entries={
            norm("AMK.008"): CatalogEntry(
                "proyecto", "facturable", "Proyecto", "Facturable", "RaaS"
            )
        }
    )
    person = Person("Ana", "DEV", False, "u", "A1")
    record = HourRecord(
        "h", "u", "Ana", "AMK.008", "", [], False, "2026-09-15", 8
    )
    historical, current = MonthTotals(), MonthTotals()
    add_record(
        record, person, (catalog, AreaTotal("DEV")), historical, True, True
    )
    add_record(
        record, person, (catalog, AreaTotal("DEV")), current, True, False
    )
    assert BILLABLE in next(iter(historical.detail.values()))["categorias"]
    assert NON_BILLABLE in next(iter(current.detail.values()))["categorias"]
    assert next(iter(historical.detail.values()))["horas"] == 8


def test_alcance_saas_historico_cambia_en_septiembre_sin_incluir_roc():
    from apps.portal.services.facturability_loader import facturable_services

    assert "SAAS" in facturable_services("2026-01")
    assert "SAAS" in facturable_services("2026-08")
    assert "SAAS" not in facturable_services("2026-09")
    assert "SAAS" not in facturable_services("2026-10")
    assert "ROC" not in facturable_services("2026-08")
    assert "ROC" not in facturable_services("2026-09")


def test_bandas_r_p_aportan_cero_sin_excluir_bandas_normales():
    from apps.gse.services.roster import RosterSheet
    from apps.portal.services.roster import excluded_capacity_rows

    sheet = RosterSheet(
        [
            ["Nombre", "ROL", "Octubre"],
            ["Residente", "DEV", "R"],
            ["Practicas", "QA", "p"],
            ["Ana", "DEV", "A1"],
            ["Luis", "QA", "NMK"],
        ],
        0,
        ["nombre", "rol", "octubre"],
    )
    assert excluded_capacity_rows(sheet, 2) == {"residente", "practicas"}


def test_correcciones_septiembre_no_se_aplican_a_agosto():
    from apps.portal.services.capacity_adjustments import (
        apply_capacity_adjustments,
    )

    people = [
        {
            "nombre": "Alvaro Andres Quintero Diaz",
            "rol": "DEV",
            "capacidad_horas": 72,
        },
        {"nombre": "Jhoan Ahumada Rivera", "rol": "ROC"},
        {"nombre": "Heidy Cabieles Martinez", "rol": "DEV"},
    ]
    september = apply_capacity_adjustments(people, "2026-09")
    assert september[0]["capacidad_horas"] == 80
    assert september[1]["rol"] == "DEV"
    assert september[2]["capacidad_horas"] == 0
    august = apply_capacity_adjustments(people, "2026-08")
    assert august[0]["capacidad_horas"] == 152
    assert august[1]["rol"] == "DEV"
    assert august[2]["capacidad_horas"] == 0
    assert people[0]["capacidad_horas"] == 72


def test_exclusiones_permanentes_con_revision_confirmada_en_octubre():
    from apps.portal.services.capacity_adjustments import (
        apply_capacity_adjustments,
    )

    people = [
        {"nombre": name, "rol": "DEV", "capacidad_horas": 168}
        for name in [
            "Claudia Ximena Mazon Vera",
            "Enrique Yael Badillo Gutierrez",
            "Luis Enrique Garcia Rivera",
        ]
    ]
    for month in ["2025-12", "2026-01", "2026-08", "2026-09", "2026-11"]:
        result = apply_capacity_adjustments(people, month)
        assert sum(p["capacidad_horas"] for p in result) == 0

    result = apply_capacity_adjustments(people, "2026-10")
    assert [person["capacidad_horas"] for person in result] == [0, 168, 0]
    assert all(p["capacidad_horas"] == 168 for p in people)


def test_importes_de_agosto_no_alteran_otros_meses():
    from apps.portal.services.capacity_adjustments import (
        apply_capacity_adjustments,
    )

    people = [
        {"nombre": name, "rol": "DEV"}
        for name in [
            "Alfredo Miranda Alvarez",
            "Daniel Leon Pineda",
            "Nicolas Alejandro Espitia Delgado",
            "Sofia Katherin Jojoa Unigarro",
        ]
    ]
    august = apply_capacity_adjustments(people, "2026-08")
    assert [p["capacidad_horas"] for p in august] == [168, 152, 152, 160]
    assert apply_capacity_adjustments(people, "2026-07") == people
    assert apply_capacity_adjustments(people, "2026-09") == people


def test_diego_y_heidy_cero_en_agosto_sin_alterar_julio():
    from apps.portal.services.capacity_adjustments import (
        apply_capacity_adjustments,
    )

    people = [
        {"nombre": "Diego Ovadid Acevedo Cruz", "rol": "DEV"},
        {"nombre": "Heidy Cabieles Martinez", "rol": "DEV"},
    ]
    assert all(
        p["capacidad_horas"] == 0
        for p in apply_capacity_adjustments(people, "2026-08")
    )
    assert apply_capacity_adjustments(people, "2026-07") == people
