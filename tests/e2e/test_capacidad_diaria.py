"""Capacidad instalada del equipo en un navegador (Bandas/rol + Clockify)."""

import copy
from pathlib import Path

import pytest
from playwright.sync_api import expect

pytestmark = pytest.mark.django_db(transaction=True)
SERVICE = "apps.portal.api.capacity_daily.build_team_capacity"
DAYS = ["2026-10-01", "2026-10-02", "2026-10-03"]


def row(name, role, band, project, daily, dm="Dora DM", clockify="u"):
    facturables = sum(daily.values())
    return {
        "nombre": name,
        "clockifyId": clockify + name[:1].lower(),
        "rol": role,
        "banda": band,
        "dm": dm,
        "idProyecto": project,
        "proyecto": "Proyecto " + project if project else "",
        "inicio": "2026-09-15",
        "fin": "2026-12-31",
        "concepto": "Proyecto",
        "facturable": "Facturable",
        "cargabilidad": "Cargable",
        "capacidad": "Afecta Capacidad",
        "facturables": facturables,
        "noFacturables": 0.0,
        "total": facturables,
        "daily": daily,
    }


def payload(month, people=None, rows=None):
    rows = rows or [
        row("Ana Perez", "Dev", "B2", "P1", {"2026-10-01": 10}),
        row("Luis", "QA", "B1", "P2", {"2026-10-01": 6, "2026-10-03": 2}),
    ]
    people = people or [
        {
            "nombre": name,
            "rol": rol,
            "banda": banda,
            "clockifyId": "u" + name[:1].lower(),
            "total": total,
            "facturables": total,
            "noFacturables": 0.0,
        }
        for name, rol, banda, total in (
            ("Ana Perez", "Dev", "B2", 10.0),
            ("Luis", "QA", "B1", 8.0),
        )
    ]
    return {
        "ok": True,
        "mes": month,
        "dias": DAYS,
        "diasHabiles": 22,
        "jornada": 8.0,
        "personas": people,
        "filas": rows,
        "resumen": {},
    }


@pytest.fixture
def daily(monkeypatch, datos):
    """Lecturas de la API; guarda los parametros de cada una."""

    class Calls(list):
        state: dict = {}

    calls = Calls()
    state = {"fail": False, "factory": payload}

    def read(_reader, month, workday):
        calls.append((month, workday))
        if state["fail"]:
            return {"ok": False, "error": "Sheets no disponible"}
        return copy.deepcopy(state["factory"](month))

    monkeypatch.setattr(SERVICE, read)
    monkeypatch.setattr(
        "apps.portal.api.capacity_daily.build_sheet_repository", lambda: None
    )
    calls.state = state
    return calls


def ready(portal):
    expect(portal.locator("#ci-status")).to_contain_text(
        "Mes 2026-10 · Bandas/rol + Clockify"
    )


def stats(portal):
    return portal.locator(".ci-stat strong").all_text_contents()


def test_indicators_follow_people_days_and_workday(portal, daily):
    portal.goto(portal.base + "/capacidad-instalada/?mes=2026-10")
    ready(portal)

    assert stats(portal) == ["2", "352 h", "18 h", "334 h", "5.11%"]
    portal.locator("#ci-jornada").fill("10")
    portal.locator("#ci-jornada").dispatch_event("change")
    assert stats(portal) == ["2", "440 h", "18 h", "422 h", "4.09%"]
    assert len(daily) == 1  # la jornada se recalcula sin volver a leer


def test_filters_and_csv_use_the_visible_rows(portal, daily, tmp_path):
    portal.goto(portal.base + "/capacidad-instalada/?mes=2026-10")
    ready(portal)
    rows = portal.locator(".ci-table tbody tr")
    expect(rows).to_have_count(2)

    portal.locator("#ci-search").fill("dora")
    expect(rows).to_have_count(2)
    portal.locator("#ci-search").fill("proyecto p2")
    expect(rows).to_have_count(1)
    portal.locator("#ci-search").fill("")
    portal.locator("#ci-role").select_option("Dev")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("Ana Perez")
    portal.locator("#ci-role").select_option("")
    portal.locator("#ci-band").select_option("B1")
    expect(rows).to_have_count(1)
    expect(rows.first).to_contain_text("Luis")
    assert stats(portal)[0] == "2"  # los indicadores son del mes completo

    with portal.expect_download() as download:
        portal.locator("#ci-export").click()
    path = tmp_path / "capacidad.csv"
    download.value.save_as(path)
    lines = path.read_bytes().decode("utf-8-sig").split("\r\n")
    assert (
        download.value.suggested_filename == "Capacidad_instalada_2026-10.csv"
    )
    assert lines[0].startswith('"Recurso","Rol","Banda","Delivery Manager"')
    assert "ID Clockify" not in lines[0]
    assert len(lines) == 2 and lines[1].startswith('"Luis"')
    assert '"15/09/2026"' not in lines[1] and '"2026-09-15"' in lines[1]


def test_missing_delivery_manager_is_stated_and_idle_people_listed(
    portal, daily
):
    daily.state["factory"] = lambda month: payload(
        month,
        rows=[
            row("Ana Perez", "Dev", "B2", "ADM.1", {"2026-10-01": 4}, dm=""),
            row("Luis", "QA", "B1", "", {}),
        ],
    )
    portal.goto(portal.base + "/capacidad-instalada/?mes=2026-10")
    ready(portal)

    first = portal.locator(".ci-table tbody tr").first.locator("td")
    expect(first.nth(3)).to_have_text("-")  # sin DM confirmado
    expect(first.nth(6)).to_have_text("15/09/2026")
    expect(first.nth(7)).to_have_text("31/12/2026")
    expect(first.nth(8)).to_have_text("Proyecto")
    expect(first.nth(9)).to_have_text("Facturable")
    expect(first.nth(10)).to_have_text("Cargable")
    expect(first.nth(11)).to_have_text("Afecta Capacidad")
    assert "ID Clockify" not in portal.locator(".ci-table thead").inner_text()
    expect(portal.locator(".ci-table tbody tr").nth(1)).to_contain_text(
        "Sin registros en el mes"
    )


def test_change_month_reads_that_month(portal, daily):
    portal.goto(portal.base + "/capacidad-instalada/?mes=2026-10")
    ready(portal)
    portal.locator("#ci-month").fill("2026-09")
    portal.locator("#ci-month").dispatch_event("change")

    expect(portal.locator("#ci-status")).to_contain_text("Mes 2026-09")
    assert [month for month, _ in daily] == ["2026-10", "2026-09"]


def test_failed_read_can_be_retried(portal, daily):
    daily.state["fail"] = True
    portal.goto(portal.base + "/capacidad-instalada/?mes=2026-10")
    expect(portal.locator("#ci-status")).to_contain_text("Sheets no disponible")

    daily.state["fail"] = False
    portal.locator("#ci-refresh").click()
    ready(portal)
    expect(portal.locator(".ci-table tbody tr")).to_have_count(2)


def test_names_are_plain_text_and_pages_are_numbered(portal, daily):
    rows = [row(f"P{i:02}", "Dev", "B1", "X", {}) for i in range(34)]
    rows[0] = row("<b>Ana</b>", "Dev", "B1", "X", {"2026-10-01": 1})
    people = [
        {
            "nombre": r["nombre"],
            "rol": "Dev",
            "banda": "B1",
            "clockifyId": "",
            "total": r["total"],
            "facturables": r["total"],
            "noFacturables": 0.0,
        }
        for r in rows
    ]
    daily.state["factory"] = lambda month: payload(
        month, people=people, rows=rows
    )
    portal.goto(portal.base + "/capacidad-instalada/?mes=2026-10")
    ready(portal)

    expect(portal.locator(".ci-table tbody tr")).to_have_count(30)
    expect(portal.locator(".ci-foot")).to_contain_text("Página 1 de 2")
    expect(portal.locator(".ci-table tbody b")).to_have_count(
        30
    )  # solo totales
    expect(portal.locator(".ci-table tbody tr").first).to_contain_text(
        "<b>Ana</b>"
    )
    portal.get_by_role("button", name="Siguiente →").click()
    expect(portal.locator(".ci-table tbody tr")).to_have_count(4)


@pytest.mark.parametrize("width", [1450, 900, 390])
def test_layout_fits_the_screen_without_csp_violations(
    portal, daily, width, enforced_csp
):
    problems = []
    portal.on(
        "console",
        lambda m: (
            problems.append(m.text) if "Content Security" in m.text else None
        ),
    )
    portal.set_viewport_size({"width": width, "height": 1000})
    portal.goto(portal.base + "/capacidad-instalada/?mes=2026-10")
    ready(portal)

    assert portal.evaluate(
        "document.documentElement.scrollWidth <= innerWidth + 1"
    )
    assert not problems, problems
    path = Path(f"tmp/capacity-team/{width}.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    portal.screenshot(path=str(path), full_page=True)
