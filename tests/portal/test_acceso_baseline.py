"""Linea base de acceso antes de migrar el front.

Los acuerdos ya estan resueltos: sus pruebas viven en test_agreements_api.py.

Lo que hoy se rechaza debe seguir rechazandose. Los permisos por accion y
el alcance por cuenta ya estan resueltos en la comparativa y la cuenta.
"""

import pytest
from django.urls import reverse

from apps.portal.models import ExecutiveAgreement
from tests.portal.test_views import portfolio, stub_portfolio

pytestmark = pytest.mark.django_db


@pytest.fixture
def sesion(client, django_user_model, settings):
    """Usuario con sesion y sin permisos ni alcance asignado."""
    settings.PORTAL_LOGIN_REQUIRED = True
    client.force_login(django_user_model.objects.create_user("sin-permisos"))
    return client


@pytest.fixture
def acuerdo():
    return ExecutiveAgreement.objects.create(
        account="Clinica Sur", title="Acuerdo de otra cuenta"
    )


def test_sin_sesion_no_se_consultan_datos_ni_acciones(
    client, settings, acuerdo
):
    settings.PORTAL_LOGIN_REQUIRED = True
    url = reverse("portal:acuerdos_ejecutivos")
    cambio = {"id": acuerdo.pk, "action": "status", "status": "done"}

    assert client.post(url, cambio).status_code == 401
    for path in (
        "/cuenta/clinica-sur/?nombre=Clinica+Sur&bloque=consumos",
        "/operativa/delivery-manager/alberto/?bloque=base",
    ):
        response = client.get(path)
        assert response.status_code == 302, path
        assert response.url.startswith("/admin/login/"), path
    acuerdo.refresh_from_db()
    assert acuerdo.status == "open"


def test_hoy_cualquier_sesion_ve_y_modifica_todo(sesion, acuerdo, monkeypatch):
    """Comportamiento actual: el login es el unico control."""
    stub_portfolio(monkeypatch, portfolio())
    url = reverse("portal:acuerdos_ejecutivos")
    cambio = {"id": acuerdo.pk, "action": "status", "status": "done"}

    assert sesion.get("/cuenta/clinica-sur/").status_code == 200
    assert sesion.post(url, cambio).status_code == 200


def test_sin_permiso_de_costos_no_se_ve_la_comparativa(sesion, settings):
    settings.ACCESS_ENFORCED = True

    assert sesion.get("/ejecutiva/oportunidades/").status_code == 403


def test_sin_permiso_no_se_ve_la_cuenta(sesion, settings, monkeypatch):
    settings.ACCESS_ENFORCED = True
    stub_portfolio(monkeypatch, portfolio())

    assert sesion.get("/cuenta/clinica-sur/").status_code == 403
