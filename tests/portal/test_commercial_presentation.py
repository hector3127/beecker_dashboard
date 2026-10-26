import pytest
from django.template.loader import get_template

from apps.portal.services.commercial_pipeline import (
    build_pipeline,
    group_services,
)
from apps.portal.templatetags.executive_numbers import hours_number
from apps.portal.templatetags.presentation_labels import commercial_stage


@pytest.mark.parametrize("previous", [False, True])
@pytest.mark.parametrize("grant", ["anonymous", "limited", "wrong"])
def test_saved_query_cannot_bypass_commercial_access(
    client, enforced, monkeypatch, previous, grant
):
    from apps.access.scope import AccessScope

    enforced(
        "Ana",
        caps=frozenset(
            {"view_costs"} if grant == "wrong" else {"view_commercial"}
        ),
        scope=AccessScope.limited(accounts=["ACME"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()

    def unexpected(*args):
        pytest.fail("Se leyeron datos comerciales sin acceso")

    monkeypatch.setattr(
        "apps.portal.services.commercial_view.build_commercial_context",
        unexpected,
    )
    response = client.get(
        "/comercial/", {"vista": "anterior"} if previous else {}
    )
    assert response.status_code == (302 if grant == "anonymous" else 403)


def test_services_reconcile_to_rows_and_month_totals():
    rows = [
        {
            "estado": "abierta",
            "fechaCierre": "2026-05-01",
            "horas": h,
            "cuenta": a,
            "servicio": s,
            "probabilidad": 80,
        }
        for a, s, h in [
            ("A", "AER", 1200.25),
            ("B", "AER", 20.5),
            ("C", "IxB", 33.75),
        ]
    ]
    section = build_pipeline(rows, 2026)["sections"][0]
    groups = group_services(section["rows"])
    assert sum(g["total"] for g in groups) == pytest.approx(section["total"])
    assert sum(
        sum(r["cells"]) for g in groups for r in g["rows"]
    ) == pytest.approx(sum(section["totals"]))
    assert len(groups) == 2
    for index, total in enumerate(section["totals"]):
        assert sum(g["cells"][index] for g in groups) == pytest.approx(total)
    assert groups[0]["probability_label"] == "80%"
    assert hours_number(1200.25) == "1,200.25"


def test_source_stage_keys_have_spanish_display_labels():
    assert commercial_stage("Closed Won (Pipeline)") == "Ganada"
    assert commercial_stage("Proposal Sent (Pipeline)") == "Propuesta enviada"


def test_changed_templates_compile():
    for name in [
        "pages/commercial.html",
        "pages/operativa.html",
        "portal/ejecutiva.html",
    ]:
        assert get_template(name)


def test_annual_service_cells_reconcile():
    from apps.portal.services.commercial_pipeline import (
        build_annual_unconfirmed,
    )

    rows = [
        {
            "estado": "abierta",
            "fechaCierre": day,
            "horas": hours,
            "cuenta": account,
            "servicio": "RaaS",
            "probabilidad": 50,
        }
        for day, hours, account in [
            ("2026-05-01", 12.5, "A"),
            ("2027-05-01", 25, "B"),
        ]
    ]
    section = build_annual_unconfirmed(rows, [2026, 2027])
    service = group_services(section["rows"])[0]
    assert service["cells"] == [12.5, 25]
    assert service["total"] == sum(service["cells"]) == section["total"]
