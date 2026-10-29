"""EVA 4 usa datos de ROC sin inventar limites ni consumir Clockify."""

from datetime import date
from unittest.mock import Mock

import pytest
from django.core.cache import cache
from django.test import RequestFactory

from apps.access.scope import AccessScope
from apps.portal import pages, views
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


def test_source_names_normalize_spacing_without_merging_or_inventing():
    first = row()
    first[0], first[6], first[7] = (
        "  Nestlé  Colombia ",
        "  1058 -  Extract KE30 ",
        " Brandon  Sotelo ",
    )
    second = row()
    second[6], second[7] = "1058 - Extract OTR", ""
    report = eva4.build_eva4([HEADER, first, second], TODAY)
    assert len(report["processes"]) == 2
    one, two = report["processes"]
    assert one["manager"] == "Brandon Sotelo"
    assert one["client"] == "Nestlé Colombia"
    assert one["process"] == "1058 - Extract KE30"
    assert two["manager"] == ""
    assert two["process"] == "1058 - Extract OTR"


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


def render_eva4(monkeypatch, params=None, today=TODAY):
    data = eva4.build_eva4([HEADER, row()], TODAY)
    data["month"] = "2026-10"
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: data)
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: today)
    request = RequestFactory().get("/operativa/eva-4/", params or {})
    return pages.eva4(request).content.decode()


@pytest.mark.parametrize("today", [TODAY, date(2026, 11, 4)])
def test_retired_parameter_keeps_the_modular_page(monkeypatch, today):
    html = render_eva4(monkeypatch, {"vista": "anterior"}, today=today)
    assert 'id="eva4-content"' in html
    assert "/static/app/scripts/pages/eva4/main.js" in html
    assert "Estás viendo la pantalla anterior" not in html
    assert "portal/js/" not in html


def test_new_view_does_not_show_a_link_to_the_anterior_one(monkeypatch):
    html = render_eva4(monkeypatch)
    assert "ver la pantalla anterior" not in html
    assert "Validación:" not in html
    assert "Estás viendo la pantalla anterior" not in html


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


def test_eva4_block_prepares_its_own_cache_without_loading_other_sources(
    monkeypatch,
):
    reader = reader_fixture()
    monkeypatch.setattr(eva4, "build_sheet_repository", lambda: reader)
    monkeypatch.setattr(
        views, "load_eva2", lambda **kw: pytest.fail("IXB read")
    )
    req = RequestFactory().get("/operativa/datos/", {"bloque": "eva4"})
    context = views.operativa_block_context(req)
    assert context["eva4"]["available"] is True
    assert cache.get(views._operativa_fresh_key(req, "eva4")) is True


def test_table_shows_only_active_processes():
    data = eva4.build_eva4(
        [HEADER, row("1"), row("2", "Suspendido"), row("3")], TODAY
    )
    assert data["total"] == 3 and data["suspended"] == 1
    assert [p["bot_id"] for p in data["active_processes"]] == ["1", "3"]


def restricted_report():
    """Tres clientes: Nestlé (2 activos), Cagsa (1 activo, 1 suspendido)."""
    rows = [HEADER, row("1"), row("2"), row("3"), row("4", "Suspendido")]
    for position in (3, 4):
        rows[position] = [*rows[position]]
        rows[position][0] = "Cagsa"
        rows[position][2] = "SAAS.CAG.001"
    report = eva4.build_eva4(rows, TODAY)
    for process in report["processes"]:
        process["invested_hours"] = None if process["bot_id"] == "2" else 5.0
        process["average_limit"] = None if process["client"] == "Cagsa" else 30
    return report


def test_restrict_keeps_everything_for_an_unrestricted_scope():
    report = restricted_report()

    scope = AccessScope.everything()
    assert eva4.restrict(report, scope, TODAY) is report


def test_restrict_recounts_totals_renewals_and_clients_from_what_is_left():
    report = restricted_report()
    assert report["total"] == 4 and report["renewal_count"] == 2

    scope = AccessScope.limited(accounts=["Cagsa"])
    result = eva4.restrict(report, scope, TODAY)

    assert [c["name"] for c in result["clients"]] == ["Cagsa"]
    assert (result["total"], result["active"], result["suspended"]) == (2, 1, 1)
    assert [p["client"] for p in result["active_processes"]] == ["Cagsa"]
    assert {r["project_id"] for r in result["renewals"]} == {"SAAS.CAG.001"}
    assert sum(result["service_totals"]) == 2
    assert result["unmatched_tasks"] == 0
    assert result["missing_limits"] == 2
    assert "Nestlé" not in str(result["clients"]) + str(result["renewals"])


def test_restrict_by_project_does_not_open_the_whole_account():
    report = restricted_report()

    scope = AccessScope.limited(projects=["saas.cag.001"])
    result = eva4.restrict(report, scope, TODAY)

    assert {p["client"] for p in result["processes"]} == {"Cagsa"}
    assert result["total"] == 2


def test_restrict_with_nothing_allowed_returns_empty_totals_not_an_error():
    result = eva4.restrict(restricted_report(), AccessScope.limited(), TODAY)

    assert result["available"] is True
    assert (result["total"], result["renewal_count"]) == (0, 0)
    assert result["clients"] == [] and result["renewals"] == []


def test_restrict_leaves_an_unavailable_report_alone():
    report = {"available": False, "error": "sin datos"}

    assert eva4.restrict(report, AccessScope.limited(), TODAY) is report
