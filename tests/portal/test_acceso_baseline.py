"""Linea base de acceso antes de migrar el front.

Lo que hoy se rechaza debe seguir rechazandose. Lo que todavia no existe
(permisos por accion y alcance por cuenta) queda como xfail estricto: el
dia que la fase de accesos lo resuelva, estas pruebas pasan y obligan a
quitar la marca.
"""

import pytest
from django.urls import reverse

from apps.portal.models import ExecutiveAgreement
from tests.portal.test_views import portfolio, stub_portfolio

pytestmark = pytest.mark.django_db

PENDIENTE = pytest.mark.xfail(
    strict=True, reason="Fase 2: permisos y alcance por usuario (app access)"
)


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


def test_rpc_sin_sesion_se_rechaza(client, monkeypatch):
    # DRF fija los permisos al importar la vista; se aplican los de base.py
    # (produccion) porque test.py los abre para las demas pruebas.
    from django.utils.module_loading import import_string

    from config.settings.base import REST_FRAMEWORK
    from core.rpc.views import RpcView

    classes = REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"]
    monkeypatch.setattr(
        RpcView, "permission_classes", [import_string(c) for c in classes]
    )
    called = []
    monkeypatch.setattr(
        "core.rpc.views.get_rpc_function", lambda name: called.append(name)
    )
    response = client.post(
        "/api/rpc/getResumenRecursos/", {}, content_type="application/json"
    )
    assert response.status_code == 403
    assert called == []


def test_hoy_cualquier_sesion_ve_y_modifica_todo(sesion, acuerdo, monkeypatch):
    """Comportamiento actual: el login es el unico control."""
    stub_portfolio(monkeypatch, portfolio())
    url = reverse("portal:acuerdos_ejecutivos")
    cambio = {"id": acuerdo.pk, "action": "status", "status": "done"}

    assert sesion.get("/cuenta/clinica-sur/").status_code == 200
    assert sesion.post(url, cambio).status_code == 200


@PENDIENTE
def test_sin_permiso_de_edicion_no_se_modifican_acuerdos(sesion, acuerdo):
    url = reverse("portal:acuerdos_ejecutivos")
    cambio = {"id": acuerdo.pk, "action": "status", "status": "done"}

    assert sesion.post(url, cambio).status_code == 403


@PENDIENTE
def test_sin_permiso_de_costos_no_se_ve_la_comparativa(sesion, monkeypatch):
    from apps.portal.services import executive_refresh
    from apps.portal.services import opportunity_profitability as opp
    from tests.portal.test_opportunity_profitability import reader

    monkeypatch.setattr(executive_refresh, "request_refresh", lambda **k: None)
    monkeypatch.setattr(opp, "build_sheet_repository", lambda: reader())

    assert sesion.get("/ejecutiva/oportunidades/").status_code == 403


@PENDIENTE
def test_cuenta_fuera_de_alcance_no_existe(sesion, settings, monkeypatch):
    settings.ACCESS_ENFORCED = True
    stub_portfolio(monkeypatch, portfolio())

    assert sesion.get("/cuenta/clinica-sur/").status_code == 404


@PENDIENTE
def test_acuerdos_fuera_de_alcance_no_se_listan(sesion, settings, acuerdo):
    settings.ACCESS_ENFORCED = True
    url = reverse("portal:acuerdos_ejecutivos")

    assert sesion.get(url).json()["items"] == []
