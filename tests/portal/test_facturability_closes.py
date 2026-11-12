"""Cierres de Facturabilidad conservan las revisiones y sus decimales."""

from dataclasses import asdict
from datetime import date

import pytest

from apps.datastore.models import FacturabilityClose
from apps.portal.services.facturability_closes import (
    GENERAL,
    SPECIALTY,
    publish,
    specialty_metric,
    specialty_zero_lab,
)

pytestmark = pytest.mark.django_db


def test_operations_chart_matches_published_general_close(client, monkeypatch):
    from apps.portal import views

    monkeypatch.setattr(views.timezone, "localdate", lambda: date(2026, 11, 12))
    publish(
        "2026-09",
        GENERAL,
        {"global_percent": 99.48, "service_hours": []},
        "GSE",
    )
    monkeypatch.setattr(views, "load_month_sources", views.MonthSources)
    data = client.get("/api/v1/screens/operativa/facturabilidad/").json()[
        "data"
    ]
    months = {row["month"]: row["global_percent"] for row in data["months"]}
    assert months["2026-09"] == 99.48
    assert months["2026-10"] == 92.2
    assert "2026-11" not in months


def test_closes_are_read_without_live_sources(client, monkeypatch):
    """Agrega los cierres trimestrales con HC sin redondear."""
    from apps.portal.services.facturability import build_month_facturability

    def unexpected(month):
        pytest.fail(f"Se consultó la fuente de un cierre publicado: {month}")

    monkeypatch.setattr("apps.portal.views.load_month_sources", unexpected)
    for index, headcount in enumerate((3, 4, 5), start=1):
        month = f"2026-{index:02d}"
        general = asdict(build_month_facturability(month, {}))
        general.update(capacity=1200.05, fixed_hours=800.12)
        publish(month, GENERAL, general, "GSE")
        rows = [
            asdict(
                specialty_metric("Dev", 540.15, headcount, 170.25, 385.75, 168)
            ),
            asdict(specialty_zero_lab()),
        ]
        publish(month, SPECIALTY, rows, "GSE")

    general = client.get("/operativa/facturabilidad/?mes=2026-03")
    assert general.context["selected"].capacity == 1200.05
    specialty = client.get(
        "/operativa/facturabilidad/especialidad/?periodo=trimestre&anio=2026&trim=1"
    )
    dev = specialty.context["quarterly_specialties"][0]["quarters"][0]
    assert dev.headcount == 4
    assert dev.capacity == pytest.approx(1620.45)
    assert dev.fixed_hc == pytest.approx(510.75 / 488)
    assert dev.variable_hc == pytest.approx(1157.25 / 488)
    assert dev.free_fte == pytest.approx(4 - (510.75 + 1157.25) / 488)


def test_revision_needs_confirmation_and_preserves_previous_values():
    """Una revisión confirmada conserva el cierre anterior."""
    assert publish("2026-11", GENERAL, {"capacity": 7000}, "Primera fuente")
    assert not publish("2026-11", GENERAL, {"capacity": 6544}, "Revisión")
    assert publish(
        "2026-11",
        GENERAL,
        {"capacity": 6544},
        "Revisión confirmada",
        revision=True,
    )
    assert not publish(
        "2026-11",
        GENERAL,
        {"capacity": 6544},
        "Revisión confirmada",
        revision=True,
    )
    assert list(
        FacturabilityClose.objects.filter(month="2026-11-01")
        .order_by("revision")
        .values_list("revision", "metrics")
    ) == [(1, {"capacity": 7000}), (2, {"capacity": 6544})]
