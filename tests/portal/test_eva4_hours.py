"""Meses, topes y saldos de EVA-04 se obtienen exclusivamente de Sheets."""

from datetime import date
from decimal import Decimal

import pytest
from django.core.cache import cache

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


def test_hours_respect_date_and_duplicate_entry_id_and_count_all_tags():
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
    # Por proyecto y BOT cuentan todas las etiquetas: 6 + 32 + 999.
    assert data["processes"][0]["invested_hours"] == 1037
    assert data["processes"][0]["hours_balance"] == -1007
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


def test_every_tag_counts_for_the_bot_of_a_project():
    data = bot_report("3634")
    raw = [
        BASE_HEADER,
        entry(task="3634 - A", tag="Monitoreo", eid="a", hours=1),
        entry(task="3634 - A", tag="Reunion", eid="b", hours=2),
        entry(task="3634 - B", tag="", eid="c", hours=4),
    ]
    enrich_hours(data, raw, TODAY.replace(day=1))
    assert data["processes"][0]["invested_hours"] == 7


def test_project_map_points_a_roc_id_to_a_differently_named_project():
    values = row("OPT.011")
    values[2] = "ROC.OPT.001"
    data = eva4.build_eva4([HEADER, values], TODAY)
    raw = [
        BASE_HEADER,
        [
            "TYM.OPT.001",
            "Ana",
            "2026-10-01",
            5,
            "OPT.011",
            "Monitoreo",
            "No",
            "a",
            "w1",
        ],
    ]
    enrich_hours(
        data,
        raw,
        TODAY.replace(day=1),
        project_map={"roc.opt.001": "tym.opt.001"},
    )
    assert data["processes"][0]["invested_hours"] == 5


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


def served(data, client, monkeypatch, **params):
    """Lo que la API de EVA-04 entrega para estos datos."""
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: data)
    return client.get("/api/v1/screens/eva4/", params).json()["data"]


@pytest.mark.django_db
def test_zero_hours_and_missing_data_are_different_in_the_contract(
    client, monkeypatch
):
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
    data["processes"][2].update(invested_hours=None, hours_balance=None)

    first, second, third = served(data, client, monkeypatch)["processes"]

    assert first["invested_hours"] == 0  # un cero real no es "sin dato"
    assert first["hours_balance"] == 30
    assert second["average_limit"] is None and second["hours_balance"] is None
    assert third["invested_hours"] is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("origin", "source"),
    [("database", "08.Base Clockify 2026"), ("sheet", "08.Base Clockify 2026")],
)
def test_contract_says_where_the_hours_come_from(
    client, monkeypatch, origin, source
):
    data = eva4.build_eva4([HEADER, row()], TODAY)
    data["hours_origin"] = origin
    data["hours_source"] = source

    body = served(data, client, monkeypatch)

    assert body["notes"]["hours_origin"] == origin
    assert body["notes"]["hours_source"] == source


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


def test_loader_uses_month_specific_cache(monkeypatch):
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
    cache.clear()
