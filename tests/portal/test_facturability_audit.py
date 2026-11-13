"""El desglose de consulta conserva horas, áreas y cierres."""

import pytest

from apps.portal.services.facturability_audit import summarize


def test_person_and_projects_balance_without_food_or_adjustments():
    gse = {
        "plantilla": [
            {"nombre": "Ana", "rol": "Dev", "capacidad_horas": 176},
            {"nombre": "Sin horas", "rol": "Dev", "capacidad_horas": 176},
        ],
        "detalle": [
            {
                "recurso": "Ana",
                "area": "DEV",
                "proyecto": "AER.A",
                "servicio": "AER",
                "horas": 10.125,
                "categorias": ["Facturable"],
            },
            {
                "recurso": "Ana",
                "area": "DEV",
                "proyecto": "AER.A",
                "servicio": "AER",
                "horas": 2,
                "categorias": ["Facturable"],
            },
            {
                "recurso": "Ana",
                "area": "DEV",
                "proyecto": "Comida",
                "servicio": "NA",
                "horas": 8,
            },
            {
                "recurso": "Ana",
                "area": "DEV",
                "proyecto": "Ajuste aprobado de octubre",
                "servicio": "AER",
                "horas": 86,
                "categorias": ["Facturable"],
            },
            {
                "recurso": "ROC",
                "area": "ROC",
                "proyecto": "ROC.A",
                "servicio": "ROC",
                "horas": 24,
            },
        ],
    }
    result = summarize(gse, frozenset({"dev"}))
    assert len(result["people"]) == 2
    ana = result["people"][0]
    assert ana["registered"] == 12.125
    assert ana["adjustment"] == 86
    assert ana["services"]["AER"] == 12.125
    assert (
        sum(
            row["hours"]
            for row in result["projects"]
            if row["kind"] == "Horas registradas"
        )
        == 12.125
    )
    assert result["people"][1]["registered"] == 0


@pytest.mark.django_db
def test_endpoint_validates_month_and_forwards_roles(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        "apps.portal.services.facturability_audit.audit_month",
        lambda month, roles: calls.append((month, roles)) or {"ok": True},
    )
    url = "/api/v1/screens/facturabilidad/desglose/"
    assert client.get(url, {"mes": "invalid"}).status_code == 400
    response = client.get(url, {"mes": "2026-10", "roles": "1", "rol": "ROC"})
    assert response.status_code == 200
    assert calls == [("2026-10", frozenset({"roc"}))]


@pytest.mark.django_db
def test_missing_download_is_pending_without_calling_sources(monkeypatch):
    from apps.portal.services import facturability_audit

    monkeypatch.setattr(
        facturability_audit,
        "read_gse_month",
        lambda *args, **kwargs: pytest.fail("No debe consultar fuentes"),
    )
    result = facturability_audit.audit_month("2099-01", frozenset({"dev"}))
    assert not result["ok"]
    assert "descarga" in result["error"]


def test_audit_uses_summary_service_scope_and_includes_adjustments():
    from apps.portal.services.facturability import build_month_facturability
    from apps.portal.services.facturability_loader import facturable_services

    detail = [
        {
            "recurso": "Ana",
            "area": "DEV",
            "proyecto": project,
            "servicio": service,
            "horas": hours,
            "categorias": ["Facturable"],
        }
        for project, service, hours in (
            ("AER.A", "AER", 100),
            ("Ajuste aprobado de octubre", "AER", 86),
            ("IXB.A", "IxB", 20),
            ("ROC.A", "ROC", 164),
            ("RAAS.SAC.001", "ROC RaaS", 12),
            ("SaaS.A", "SaaS", 0.5),
            ("Proyecto sin servicio", "NA", 40),
            ("Pre ventas", "Otros", 83),
        )
    ]
    gse = {
        "mes": "2026-10",
        "detalle": detail,
        "serviciosFacturables": facturable_services("2026-10"),
        "plantilla": [{"nombre": "Ana", "rol": "DEV", "capacidad_horas": 176}],
    }
    scope = frozenset({"dev"})
    audit = summarize(gse, scope)
    summary = build_month_facturability("2026-10", gse, scope=(scope, None))
    person = audit["people"][0]
    assert person["counted_services"]["AER"] == summary.fixed_hours == 186
    assert (
        person["counted_hours"] == summary.fixed_hours + summary.variable_hours
    )
    assert person["counted_hours"] == 289
    assert sum(row["hours"] for row in audit["projects"]) == 289
    assert len(audit["excluded"]) == 4


@pytest.mark.django_db
def test_manual_changes_revise_published_totals(client, monkeypatch):
    from datetime import date
    from unittest.mock import Mock

    from apps.datastore.models import (
        FacturabilityClose,
        FacturabilityCorrection,
    )
    from apps.portal.services import facturability_corrections as corrections

    month = date(2026, 10, 1)
    raw = {
        "ok": True,
        "mes": "2026-10",
        "capacidadInicial": True,
        "plantilla": [{"nombre": "Ana", "rol": "DEV", "capacidad_horas": 176}],
        "detalle": [],
    }
    sync = Mock()
    locked = sync.objects.select_for_update.return_value
    locked.filter.return_value.first.return_value = True
    monkeypatch.setattr(corrections, "ClockifyMonthSync", sync)
    monkeypatch.setattr(
        "apps.portal.services.facturability_loader.read_gse_month",
        lambda *args, **kwargs: raw,
    )
    close = FacturabilityClose.objects.filter(month=month, view="general")
    original = close.latest("revision")
    url = "/api/v1/screens/facturabilidad/correcciones/"

    def post(**data):
        response = client.post(
            url,
            {"month": "2026-10", "person": "Ana", **data},
            content_type="application/json",
        )
        assert response.status_code == 200, response.content

    post(kind="capacity", action="save", hours=168)
    saved = FacturabilityCorrection.objects.get(month=month)
    assert saved.payload["previous_hours"] == 176
    corrected = corrections.corrected_source(
        {**raw, "plantilla": [{**raw["plantilla"][0], "capacidad_horas": 160}]},
        "2026-10",
    )
    person = summarize(corrected, frozenset({"dev"}))["people"][0]
    assert person["estimated"] == 168
    assert person["capacity_changes"] == [{"before": 176, "after": 168}]
    post(
        kind="project",
        action="save",
        role="DEV",
        project="AER.TEST",
        service="AER",
        hours=12,
        billable=True,
    )
    revised = close.latest("revision").metrics
    assert revised["capacity"] == original.metrics["capacity"] - 8
    assert revised["fixed_hours"] == original.metrics["fixed_hours"] + 12
    target = ["ana", "AER.TEST", "AER", "dev", True]
    post(
        kind="project",
        action="save",
        role="DEV",
        project="AER.TEST",
        service="AER",
        hours=20,
        billable=True,
        target=target,
    )
    assert (
        close.latest("revision").metrics["fixed_hours"]
        == original.metrics["fixed_hours"] + 20
    )
    post(kind="project", action="delete", target=target)
    assert (
        close.latest("revision").metrics["fixed_hours"]
        == original.metrics["fixed_hours"]
    )
    assert FacturabilityCorrection.objects.filter(month=month).count() == 4
    assert close.get(pk=original.pk).metrics == original.metrics

    # A second edit still restores the original, even if the source changed.
    post(kind="capacity", action="save", hours=152)
    raw["plantilla"][0]["capacidad_horas"] = 160
    post(kind="capacity", action="reset")
    restored = close.latest("revision").metrics
    assert restored["capacity"] == original.metrics["capacity"]
    assert restored["fixed_hours"] == original.metrics["fixed_hours"]
    person = summarize(
        corrections.corrected_source(raw, "2026-10"), frozenset({"dev"})
    )["people"][0]
    assert person["estimated"] == 176
    assert person["capacity_changes"][-1] == {
        "before": 152,
        "after": 176,
        "reset": True,
    }
    response = client.post(
        url,
        {
            "month": "2026-10",
            "person": "Ana",
            "kind": "capacity",
            "action": "reset",
        },
        content_type="application/json",
    )
    assert response.status_code == 400
    assert FacturabilityCorrection.objects.filter(month=month).count() == 6
