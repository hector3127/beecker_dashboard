"""Meses, topes y saldos de EVA-04 se obtienen exclusivamente de Sheets."""

import re
from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.test import RequestFactory

from apps.portal import views
from apps.portal.services import eva4
from apps.portal.services.eva4_hours import (
    apply_limits,
    enrich_hours,
    monthly_hours,
    resolve_month,
    task_matches,
)
from tests.fakes import InMemorySheetRepository
from tests.portal.test_eva4 import BASE_HEADER, HEADER, TODAY, row


def entry(
    hours=6,
    day="2026-10-01",
    task="Reporte",
    tag="Monitoreo",
    eid="e1",
    workspace="w1",
):
    return ["ROC.NSC.001", "Ana", day, hours, task, tag, "No", eid, workspace]


def report(cap=30, service="ROC"):
    values = row() + [cap]
    values[4] = service
    return eva4.build_eva4([HEADER + ["Tope Mensual"], values], TODAY)


def test_monthly_hours_respect_date_tag_and_duplicate_entry_id():
    raw = [
        BASE_HEADER,
        entry(),
        entry(),
        entry(32, eid="e2"),
        entry(999, day="2026-09-01", eid="other-month"),
        entry(999, tag="Administrativo", eid="other-tag"),
    ]
    data = report()
    enrich_hours(data, raw, TODAY.replace(day=1))
    assert data["processes"][0]["invested_hours"] == 38
    assert data["processes"][0]["hours_balance"] == -8
    assert data["month"] == "2026-10"


def test_decimal_precision_zero_limit_and_missing_limit():
    data = report(0, service="Garantía")
    enrich_hours(
        data,
        [BASE_HEADER, entry(0.1), entry(0.2, eid="e2")],
        TODAY.replace(day=1),
    )
    assert data["processes"][0]["hours_balance"] == -0.3
    data = report("", service="Garantía")
    enrich_hours(data, [BASE_HEADER, entry()], TODAY.replace(day=1))
    assert data["processes"][0]["invested_hours"] == 6
    assert data["processes"][0]["average_limit"] is None
    assert data["processes"][0]["hours_balance"] is None
    assert data["missing_limits"] == 1


@pytest.mark.parametrize(
    ("service", "limit"),
    [
        ("ROC", 30),
        ("AER", 160),
        ("RaaS", 40),
        ("RAAS", 40),
        ("SaaS", 80),
        ("T&M", 160),
        ("T & M", 160),
        ("TyM", 160),
    ],
)
def test_average_limit_depends_on_the_service_not_on_the_sheet(service, limit):
    data = report(999, service=service)
    enrich_hours(data, [BASE_HEADER, entry()], TODAY.replace(day=1))
    process = data["processes"][0]
    assert process["average_limit"] == limit
    assert process["hours_balance"] == limit - 6


def test_service_without_rule_keeps_the_sheet_limit():
    data = report(50, service="Garantía")
    enrich_hours(data, [BASE_HEADER, entry()], TODAY.replace(day=1))
    assert data["processes"][0]["average_limit"] == 50
    assert data["missing_limits"] == 0


def bot_report(*bots, project="ROC.NSC.001"):
    rows = []
    for bot in bots:
        item = row(bot=bot)
        item[2] = project
        item[6] = "Nombre sin numero"
        rows.append(item)
    return eva4.build_eva4([HEADER, *rows], TODAY)


def test_invested_hours_use_roc_id_and_the_bot_tag_of_the_task():
    data = bot_report("3634", "1386", "9999")
    raw = [
        BASE_HEADER,
        entry(task="3634 - Gestión de transporte", eid="a", hours=4),
        entry(task="1386 - SubmissionGR", eid="b", hours=1.5),
        entry(task="1386 - Sending Orders", eid="c", hours=2),
        # El mismo BOT en otro proyecto no se suma.
        [
            "ROC.OTRO.001",
            "Ana",
            "2026-10-01",
            50,
            "3634 - Otro",
            "Monitoreo",
            "No",
            "d",
            "w1",
        ],
        # El mes anterior no cuenta, pero el BOT existe: queda en cero.
        entry(task="9999 - Sin horas", day="2026-09-01", eid="e", hours=7),
    ]
    enrich_hours(data, raw, TODAY.replace(day=1))
    hours = {p["bot_id"]: p["invested_hours"] for p in data["processes"]}
    assert hours == {"3634": 4, "1386": 3.5, "9999": 0}


def test_without_roc_id_hours_of_a_same_named_task_elsewhere_do_not_count():
    values = row()
    values[2] = ""
    data = eva4.build_eva4([HEADER, values], TODAY)
    enrich_hours(data, [BASE_HEADER, entry()], TODAY.replace(day=1))
    assert data["processes"][0]["invested_hours"] is None


def test_bot_in_a_project_without_clockify_hours_has_no_data():
    data = bot_report("5555", project="ROC.SIN.CLOCKIFY")
    enrich_hours(
        data,
        [BASE_HEADER, entry(task="3634 - Otro BOT", eid="a")],
        TODAY.replace(day=1),
    )
    assert data["processes"][0]["invested_hours"] is None


@pytest.mark.parametrize(
    ("bot", "task", "expected"),
    [
        ("Mexico12", "Mexico012", True),
        ("Mexico012", "mexico12", True),
        ("AWN.001", "AWN.001 - Payne Nickles", True),
        ("3634", "3634 - Gestión de transporte", True),
        ("1386 - Sending VES", "1386 - Sending VES", True),
        ("AMK.1", "AMK.12", False),
        ("Mexico24", "Mexico024.1", False),
        ("1386 - Sending VES", "1386 - Sending Orders", False),
        ("", "AMK.001", False),
    ],
)
def test_task_matches_the_bot_id(bot, task, expected):
    assert task_matches(task, bot) is expected


def test_bot_column_shows_only_the_tag_and_process_keeps_its_name():
    data = eva4.build_eva4(
        [HEADER, row(bot="3708 - Temporary Green Coffee"), row(bot="AIN.002")],
        TODAY,
    )
    for item in data["processes"]:
        item["process"] = "3708 - Temporary Green Coffee"
    enrich_hours(data, [BASE_HEADER, entry()], TODAY.replace(day=1))
    assert [p["bot_label"] for p in data["processes"]] == ["3708", "AIN.002"]
    assert data["processes"][0]["process"] == "3708 - Temporary Green Coffee"


def render(data, monkeypatch):
    monkeypatch.setattr(eva4, "load_eva4", lambda: data)
    return views.eva4(
        RequestFactory().get("/operativa/eva-4/")
    ).content.decode()


def test_empty_cells_say_why_and_zero_hours_is_not_missing_data(monkeypatch):
    rows = []
    for bot, service in (("1", "ROC"), ("2", "Garantía"), ("3", "ROC")):
        item = row(bot=bot)
        item[4] = service
        item[6] = f"{bot} - Proceso"
        rows.append(item)
    data = eva4.build_eva4([HEADER, *rows], TODAY)
    # BOT 1: 0 horas; BOT 2: servicio sin limite; BOT 3: sin tareas en Clockify.
    raw = [BASE_HEADER, entry(task="1 - Proceso", day="2026-09-01", eid="s")]
    enrich_hours(data, raw, TODAY.replace(day=1))
    data["processes"][0]["invested_hours"] = 0
    data["processes"][0]["hours_balance"] = 30
    html = render(data, monkeypatch)
    assert html.count("Sin límite para este servicio") >= 1
    assert html.count("Sin coincidencia en Clockify") >= 1
    assert "Sin dato" not in html
    first = html.split("<tbody>", 1)[1].split("</tr>", 1)[0]
    assert '<td class="n">0</td>' in first


def test_footer_names_the_database_when_hours_come_from_it(monkeypatch):
    data = eva4.build_eva4([HEADER, row()], TODAY)
    data["hours_origin"] = "database"
    data["hours_source"] = "08.Base Clockify 2026"
    html = render(data, monkeypatch)
    assert "horas de Clockify (base de datos)" in html
    assert "08.Base Clockify" not in html


def test_raas_has_a_default_package_limit_of_80_and_other_services_none():
    for service, expected in (("RaaS", 80), ("RAAS", 80), ("ROC", "")):
        data = report(30, service=service)
        enrich_hours(data, [BASE_HEADER, entry()], TODAY.replace(day=1))
        assert data["processes"][0]["package_limit"] == expected


def test_package_limit_from_the_source_is_not_overwritten():
    values = row() + [30, 120]
    values[4] = "RaaS"
    data = eva4.build_eva4(
        [HEADER + ["Tope Mensual", "Hours Package Limit"], values], TODAY
    )
    enrich_hours(data, [BASE_HEADER, entry()], TODAY.replace(day=1))
    assert data["processes"][0]["package_limit"] == 120


def test_available_hours_package_is_the_hours_consumed_column_of_roc():
    values = row()
    values[HEADER.index("Hours Consumed")] = 26
    data = eva4.build_eva4([HEADER, values], TODAY)
    assert data["processes"][0]["package_available"] == 26
    assert "Available Hours Package" not in data["missing_columns"]


def test_each_workspace_preserves_its_own_entry_id():
    totals, _ = monthly_hours(
        [BASE_HEADER, entry(), entry(4, workspace="w2")], TODAY.replace(day=1)
    )
    assert totals["reporte"] == Decimal(10)


def test_known_task_without_hours_in_selected_month_is_zero():
    data = report()
    enrich_hours(
        data, [BASE_HEADER, entry(day="2026-09-01")], TODAY.replace(day=1)
    )
    assert data["processes"][0]["invested_hours"] == 0
    assert data["processes"][0]["hours_balance"] == 30


def test_bot_without_tasks_in_an_existing_project_counts_zero_like_the_excel():
    data = report()
    enrich_hours(
        data, [BASE_HEADER, entry(task="Otro proceso")], TODAY.replace(day=1)
    )
    assert data["processes"][0]["invested_hours"] == 0
    assert data["processes"][0]["hours_balance"] == 30


def test_project_missing_in_clockify_is_missing_data_not_zero():
    values = row()
    values[2] = "ROC.NO.EXISTE"
    data = eva4.build_eva4([HEADER, values], TODAY)
    enrich_hours(
        data, [BASE_HEADER, entry(task="Otra cosa")], TODAY.replace(day=1)
    )
    assert data["processes"][0]["invested_hours"] is None
    assert data["processes"][0]["hours_balance"] is None


def test_processes_sharing_a_bot_each_show_the_hours_of_that_bot():
    one, two = row("AIN.002"), row("AIN.002")
    one[6], two[6] = "Order Entry", "Invoices"
    data = eva4.build_eva4([HEADER, one, two], TODAY)
    enrich_hours(
        data, [BASE_HEADER, entry(task="AIN.002")], TODAY.replace(day=1)
    )
    assert [p["invested_hours"] for p in data["processes"]] == [6, 6]


def test_unique_bot_can_use_its_exact_task_code():
    data = eva4.build_eva4([HEADER, row("AIN.002")], TODAY)
    enrich_hours(
        data, [BASE_HEADER, entry(task="AIN.002")], TODAY.replace(day=1)
    )
    assert data["processes"][0]["invested_hours"] == 6


def test_additional_categories_are_included_in_last_four_months():
    raw = [
        BASE_HEADER,
        entry(tag="Change Request"),
        entry(tag="Change Request", day="2026-08-01", eid="aug"),
    ]
    assert monthly_hours(raw, date(2026, 10, 1))[0]["reporte"] == 6
    assert monthly_hours(raw, date(2026, 8, 1))[0] == {}


def test_topes_can_be_read_from_a_table_in_the_same_sheet():
    data = report("")
    apply_limits(
        data, [["Id Bot", "Cliente", "Tope Mensual"], ["Reporte", "Nestlé", 30]]
    )
    enrich_hours(data, [BASE_HEADER, entry()], TODAY.replace(day=1))
    assert data["processes"][0]["hours_balance"] == 24
    assert data["processes"][0]["package_limit"] == ""


def test_conflicting_topes_are_not_guessed():
    data = report("")
    apply_limits(
        data,
        [
            ["Id Bot", "Cliente", "Tope Mensual"],
            ["Reporte", "Nestlé", 30],
            ["Reporte", "Nestlé", 40],
        ],
    )
    assert data["processes"][0]["average_limit"] == ""


def test_missing_columns_or_invalid_numeric_hours_are_errors():
    with pytest.raises(ValueError, match="base de horas"):
        monthly_hours([["Task"]], TODAY.replace(day=1))
    with pytest.raises(ValueError, match="no numericas"):
        monthly_hours(
            [BASE_HEADER, entry(hours="invalid")], TODAY.replace(day=1)
        )


@pytest.mark.parametrize("value", ["wrong", "2026-13", "2026-1"])
def test_month_validation(value):
    with pytest.raises(ValueError):
        resolve_month(value, TODAY)


def test_loader_and_page_use_month_specific_cache(monkeypatch):
    cache.clear()
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: TODAY)
    reader = InMemorySheetRepository(
        {
            "ROC": [HEADER, row()],
            "EVA-04 Report": [["Id Bot", "Tope Mensual"], ["Reporte", 30]],
            "08.Base Clockify 2026": [
                BASE_HEADER,
                entry(),
                entry(2, day="2026-09-01", eid="sep"),
            ],
        }
    )
    monkeypatch.setattr(eva4, "build_sheet_repository", lambda: reader)
    sep = eva4.load_eva4("2026-09")
    oct_report = eva4.load_eva4()
    assert sep["processes"][0]["hours_balance"] == 28
    assert oct_report["processes"][0]["hours_balance"] == 24
    assert eva4.snapshot_key("2026-09") != eva4.snapshot_key()
    html = views.eva4(
        RequestFactory().get("/operativa/eva-4/", {"mes": "2026-09"})
    ).content.decode()
    assert 'value="2026-09"' in html
    assert "EVA-04 Report" in html
    headers = html.split('id="eva4-processes"', 1)[1].split("</tr>", 1)[0]
    names = re.findall(r"<th(?:\s[^>]*)?>(.*?)</th>", headers)
    assert names == [
        "Delivery Manager",
        "Country",
        "Client",
        "BOT ID",
        "Service",
        "Process Name",
        "Status ROC",
        "Start",
        "Finish",
        "Average Limit",
        "Invested Hours",
        "Hours Balance",
        "Hours Package Limit",
        "Available Hours Package",
        "Risk",
    ]
    assert "Sin dato" not in html
    assert "Fuentes: ROC (Google Sheets) y horas de Clockify (hoja" in html
    cache.clear()
