"""Detalle de una cuenta (cliente)."""

from apps.portal.services.account import (
    build_account_detail,
    build_account_row,
    find_account,
)
from apps.portal.services.manager_detail import (
    build_project_row,
    summarize_suspended,
)
from tests.portal.builders import make_project


def acme_projects():
    return [
        make_project(project_id="1", name="Zeta", delivery_manager="Ana"),
        make_project(
            project_id="2",
            name="Critico",
            health="Crítica",
            burn_hours=125.0,
        ),
        make_project(
            project_id="3",
            name="Riesgo",
            health="En Riesgo",
            delay_days=9,
        ),
        make_project(project_id="4", name="Pausa", status_category="En Pausa"),
        make_project(project_id="5", name="Cerrado", status_category="Cerrado"),
    ]


def test_find_account_by_slug():
    projects = acme_projects() + [
        make_project(project_id="9", client="Clínica Sur"),
        make_project(project_id="10", client=""),
    ]

    name, mine = find_account(projects, "acme")
    assert name == "ACME"
    assert len(mine) == 5
    assert find_account(projects, "clinica-sur")[0] == "Clínica Sur"
    assert find_account(projects, "sin-nombre") is None
    assert find_account(projects, "nadie") is None


def test_account_row_has_manager_status_and_detail():
    row = build_account_row(acme_projects()[1])

    assert row.delivery_manager == "Laura Vega"
    assert row.status_label == "Crítico"
    assert row.status_code == "r"
    assert row.detail == "Presupuesto usado: 125%"
    assert row.row_class == "rs"


def test_account_detail_counts_orders_and_shares():
    detail = build_account_detail("ACME", acme_projects())

    assert detail.name == "ACME"
    assert (detail.total, detail.in_progress, detail.paused) == (4, 3, 1)
    assert (
        detail.health.on_time,
        detail.health.at_risk,
        detail.health.critical,
    ) == (1, 1, 1)
    assert [row.name for row in detail.rows] == [
        "Critico",
        "Riesgo",
        "Zeta",
        "Pausa",
    ]
    assert [share.count for share in detail.shares] == [1, 1, 1]
    assert detail.shares[0].percent == 33


def test_account_without_active_projects():
    detail = build_account_detail(
        "ACME",
        [make_project(status_category="Cerrado")],
    )

    assert detail.total == 0
    assert detail.rows == ()
    assert [share.count for share in detail.shares] == [0, 0, 0]


def test_rows_link_to_the_account_with_a_slug():
    project = make_project(client="Clínica Sur")

    assert build_project_row(project).client_slug == "clinica-sur"
    assert build_project_row(make_project(client="")).client_slug == ""
    paused = make_project(client="Clínica Sur", status_category="En Pausa")
    assert summarize_suspended([paused]).rows[0].client_slug == "clinica-sur"
