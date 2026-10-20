"""EVA 4 usa datos de ROC sin inventar limites ni consumir Clockify."""

from datetime import date
from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.test import RequestFactory

from apps.portal import views
from apps.portal.services import eva4
from core.exceptions import SheetNotFoundError
from tests.fakes import InMemorySheetRepository

TODAY = date(2026, 10, 14)
BASE_HEADER = [
    "Project",
    "User",
    "Start Date",
    "Duration (decimal)",
    "Task",
    "Tags",
    "Billable",
    "ID Registro",
    "Workspace",
]
HEADER = [
    "Client",
    "Country",
    "ROC ID",
    "BOT ID",
    "Service",
    "Status ROC",
    "Process Name",
    "Delivery Manager",
    "Account Manager",
    "Start ",
    "Finish",
    "Hours Consumed",
    "Risk",
]


def row(bot="1", status="Activo", finish="2026-10-20", country="MEX"):
    return [
        "Nestlé",
        country,
        "ROC.NSC.001",
        bot,
        "ROC",
        status,
        "Reporte",
        "Ana",
        "Beto",
        "2026-01-01",
        finish,
        0,
        "Riesgo",
    ]


def reader_fixture():
    return InMemorySheetRepository(
        {
            "ROC": [HEADER, row()],
            "08.Base Clockify 2026": [
                BASE_HEADER,
                [
                    "ROC.NSC.001",
                    "Ana",
                    "2026-10-01",
                    0,
                    "Reporte",
                    "Monitoreo",
                    "No",
                    "e1",
                    "w1",
                ],
            ],
        }
    )


@pytest.fixture(autouse=True)
def clean_cache(monkeypatch):
    cache.clear()
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    yield
    cache.clear()


def test_tables_use_current_rows_and_do_not_repeat_contract_renewals():
    data = eva4.build_eva4(
        [
            HEADER,
            row(),
            row("2"),
            row("3", "Suspendido", country="COL"),
            row("4", "Finalizado"),
        ],
        TODAY,
    )
    assert data["total"] == 3
    assert data["active"] == 2
    assert data["suspended"] == 1
    assert data["clients"][0]["total"] == 3
    assert data["renewal_count"] == 2
    assert data["renewals"][0]["due"] == 6
    assert data["processes"][0]["invested_hours"] == ""
    assert data["processes"][0]["average_limit"] == ""
    assert "Tope Mensual" in data["missing_columns"]


def test_page_structure_is_accessible_and_puts_processes_first(monkeypatch):
    data = eva4.build_eva4([HEADER, row(finish="2026-10-20")], TODAY)
    monkeypatch.setattr(eva4, "load_eva4", lambda: data)
    html = views.eva4(
        RequestFactory().get("/operativa/eva-4/")
    ).content.decode()
    # base.html ya abre el <main>: la pagina no abre otro.
    assert html.count("<main") == 1
    table = html.split('id="eva4-processes"', 1)[1].split("</table>", 1)[0]
    assert table.count('<th scope="col">') == 15
    assert "<caption" in table
    assert html.index('id="eva4-processes"') < html.index('id="eva4-renewals"')
    assert html.index('id="eva4-renewals"') < html.index('id="eva4-clients"')
    # Renovaciones y clientes quedan plegados bajo la tabla principal.
    assert html.count('<details class="eva4-card eva4-fold"') == 2
    assert 'role="status"' in html and 'id="eva4-count"' in html
    assert 'class="eva4-kpis"' not in html


def render_eva4(monkeypatch, params=None, today=TODAY):
    data = eva4.build_eva4([HEADER, row()], TODAY)
    data["month"] = "2026-10"
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: data)
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: today)
    request = RequestFactory().get("/operativa/eva-4/", params or {})
    return views.eva4(request).content.decode()


def test_anterior_view_is_available_until_the_cutoff_date(monkeypatch):
    html = render_eva4(monkeypatch, {"vista": "anterior"})
    assert "Estás viendo la pantalla anterior" in html
    assert "03/11/2026" in html
    assert "eva4-month-form" in html  # sigue siendo EVA-04


def test_new_view_does_not_show_a_link_to_the_anterior_one(monkeypatch):
    html = render_eva4(monkeypatch)
    assert "ver la pantalla anterior" not in html
    assert "Validación:" not in html
    assert "Estás viendo la pantalla anterior" not in html


def test_anterior_param_is_ignored_after_the_cutoff(monkeypatch):
    html = render_eva4(
        monkeypatch,
        {"vista": "anterior"},
        today=eva4.ANTERIOR_HASTA.replace(day=eva4.ANTERIOR_HASTA.day + 1),
    )
    assert "Estás viendo la pantalla anterior" not in html
    assert "vista=anterior" not in html
    assert 'id="eva4-processes"' in html


def test_month_picker_lists_years_months_and_limits():
    picker = eva4.month_picker("2026-09", TODAY)
    assert picker["value"] == "2026-09"
    assert (picker["year"], picker["month"]) == (2026, 9)
    assert picker["years"] == [2024, 2025, 2026]
    assert [m["name"] for m in picker["months"]][:2] == ["Enero", "Febrero"]
    assert len(picker["months"]) == 12
    assert (picker["min"], picker["max"]) == ("2024-08", "2026-10")


@pytest.mark.parametrize("value", [None, "", "wrong", "2026-13"])
def test_month_picker_falls_back_to_the_current_month(value):
    assert eva4.month_picker(value, TODAY)["value"] == "2026-10"


def test_month_picker_keeps_a_year_outside_the_normal_range():
    assert eva4.month_picker("2027-02", TODAY)["years"][-1] == 2027


def test_month_filter_is_two_selects_with_step_buttons(monkeypatch):
    html = render_eva4(monkeypatch, {"mes": "2026-09"})
    form = html.split('class="eva4-month-form"', 1)[1].split("</form>", 1)[0]
    # Sin <input type="month">: Firefox y Safari lo muestran como texto.
    assert 'type="month"' not in form
    assert form.count("<select") == 2
    assert 'aria-label="Mes anterior"' in form
    assert 'aria-label="Mes siguiente"' in form
    assert '<option value="9" selected>Septiembre</option>' in form
    assert '<option value="2026" selected>2026</option>' in form
    assert 'name="mes" value="2026-09"' in form
    assert 'data-min="2024-08"' in html and 'data-max="2026-10"' in html


def test_renewals_include_overdue_and_exclude_more_than_90_days():
    result = eva4.build_eva4(
        [HEADER, row(finish="2026-10-06"), row("2", finish="2027-06-01")], TODAY
    )
    assert result["renewal_count"] == 1
    assert result["renewals"][0]["due"] == -8
    assert result["renewals"][0]["urgency"] == "critical"


def test_loader_reuses_cache_and_preserves_previous_cut_on_failure(monkeypatch):
    reader = reader_fixture()
    reader.read_values = Mock(wraps=reader.read_values)
    monkeypatch.setattr(eva4, "build_sheet_repository", lambda: reader)
    first = eva4.load_eva4()
    assert eva4.load_eva4() == first
    assert reader.read_values.call_count == 2
    assert first["processes"][0]["invested_hours"] == 0
    cache.delete(eva4.snapshot_key() + ":fresh")
    reader.read_values.side_effect = SheetNotFoundError("ROC")
    result = eva4.load_eva4()
    assert result["error"]
    assert result["total"] == first["total"]
    assert cache.get(eva4.snapshot_key()) == first


def test_detail_renders_three_tables_with_existing_portal_layout(monkeypatch):
    data = eva4.build_eva4([HEADER, row()], TODAY)
    monkeypatch.setattr(eva4, "load_eva4", lambda: data)
    html = views.eva4(
        RequestFactory().get("/operativa/eva-4/")
    ).content.decode()
    for name in ["eva4-clients", "eva4-renewals", "eva4-processes"]:
        assert f'id="{name}"' in html
    assert "Columnas pendientes de fuente" in html
    assert "Nestlé" in html
    assert "EVA-04 Report" in html
    assert "Sin dato" not in html
    assert "Sin coincidencia en Clockify" in html


def test_eva4_block_prepares_its_own_cache_without_loading_other_sources(
    monkeypatch,
):
    reader = reader_fixture()
    monkeypatch.setattr(eva4, "build_sheet_repository", lambda: reader)
    monkeypatch.setattr(
        views, "load_eva2", lambda **kw: pytest.fail("IXB read")
    )
    req = RequestFactory().get("/operativa/datos/", {"bloque": "eva4"})
    html = views.operativa_datos(req).content.decode()
    assert 'id="ops-eva4-card"' in html
    assert cache.get(views._operativa_fresh_key(req, "eva4")) is True
