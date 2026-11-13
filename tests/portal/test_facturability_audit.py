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
            },
            {
                "recurso": "Ana",
                "area": "DEV",
                "proyecto": "AER.A",
                "servicio": "AER",
                "horas": 2,
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
