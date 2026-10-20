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
