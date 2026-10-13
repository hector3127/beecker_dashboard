"""Pantalla EVA 1 a partir del resumen AER/T&M de MPB."""

from apps.ejecutivo.services.aer_tym_summary import build_aer_tym_summary
from apps.portal.services.eva1 import (
    build_eva1_view,
    build_eva_project,
    format_short_date,
)
from tests.ejecutivo.test_aer_tym import TODAY, build_mpb_row, build_values


def sample_rows():
    values = build_values(
        build_mpb_row(
            cliente="ACME",
            id="TYM.AMK.010",
            nombre="Soporte",
            service="T & M",
            inicio="01/03/2026",
            fin="2026-10-12",
            estatus="En progreso",
            dm="Laura",
            fte="2",
            dev=2,
            horas="1,000",
            burn=250,
        ),
        build_mpb_row(
            cliente="Globex",
            id="AER.003",
            nombre="Backlog",
            service="AER",
            inicio="01/01/2026",
            fin="2027-03-01",
            estatus="En progreso",
            dm="Laura",
            fte="1",
            dev=1,
            horas="100",
            burn=120,
        ),
        build_mpb_row(
            cliente="Initech",
            id="AER.004",
            nombre="Sin consumo",
            service="AER",
            estatus="En progreso",
            fte="3",
            dev=3,
        ),
    )

    return build_aer_tym_summary(values, TODAY)["filas"]


def test_short_date():
    assert format_short_date("2026-10-06") == "06/10/26"
    assert format_short_date("") == ""
    assert format_short_date(None) == ""
    assert format_short_date("06/10/2026") == ""


def test_project_alerts():
    rows = {row["idProyecto"]: row for row in sample_rows()}

    near = build_eva_project(rows["TYM.AMK.010"])
    over = build_eva_project(rows["AER.003"])
    empty = build_eva_project(rows["AER.004"])

    assert near.renewal_days == 10
    assert near.renewal_bad is True
    assert near.progress_bad is False
    assert near.etc_bad is False
    assert over.progress == 120.0
    assert over.progress_bad is True
    assert over.etc_bad is True
    assert over.renewal_bad is False
    assert (empty.burn, empty.etc, empty.progress) == (None, None, None)
    assert empty.progress_bad is False
    assert empty.start == ""


def test_view_totals_and_pivot():
    view = build_eva1_view(sample_rows())

    assert view.total_projects == 3
    assert view.total_fte == 6
    assert view.services == ("AER", "T&M")
    assert [item.name for item in view.managers] == ["Laura", "Sin asignar"]
    laura = view.managers[0]
    assert laura.services == (1, 1)
    assert laura.roles[0] == 3
    assert laura.total_fte == 3
    assert view.totals.services == (2, 1)
    assert view.totals.roles[view.roles.index("DEV")] == 6
    assert view.totals.total_fte == 6


def test_projects_sorted_by_renewal_days_and_missing_last():
    view = build_eva1_view(sample_rows())

    assert [item.project_id for item in view.projects] == [
        "TYM.AMK.010",
        "AER.003",
        "AER.004",
    ]
    assert view.projects[-1].renewal_days is None


def test_empty_view():
    view = build_eva1_view([])

    assert view.total_projects == 0
    assert view.managers == ()
    assert view.totals.total_fte == 0
