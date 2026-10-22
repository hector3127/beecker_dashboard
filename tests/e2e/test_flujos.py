"""Flujos del portal actual que la migracion del front debe conservar.

Cada prueba recorre la pantalla en un navegador real. Los snapshots
guardan lo que la persona ve; la version nueva debe mostrar lo mismo.
"""

import re

import pytest
from playwright.sync_api import expect

from apps.portal.models import ExecutiveAgreement
from tests.e2e.conftest import rows, visible

pytestmark = pytest.mark.django_db(transaction=True)

PERIODO = "periodo=anio&anio=2026"


def metric(portal, element_id, label, value):
    """Espera el numero de una tarjeta, no solo que el texto aparezca."""
    expect(portal.locator(f"#{element_id}")).to_have_text(
        re.compile(rf"{label}\s*{value}\b")
    )


def test_filtrar_por_servicio_actualiza_indicadores(portal, datos, snapshot):
    portal.goto(f"{portal.base}/operativa/")
    listo = portal.locator("#ops-refresh-button")
    expect(listo).to_be_enabled(timeout=20000)  # terminaron todos los bloques
    metric(portal, "ops-metric-progress", "Proyectos en ejecución", 3)
    metric(portal, "ops-metric-paused", "Suspendidos", 1)
    todos = {
        "indicadores": visible(portal.locator("#ops-metrics")),
        "delivery_managers": visible(portal.locator("#ops-managers")),
    }

    servicio = portal.get_by_label("Filtrar portafolio por servicio")
    servicio.select_option("T&M")
    portal.wait_for_url(re.compile(r"servicio=T%26M"))
    expect(listo).to_be_enabled(timeout=20000)

    metric(portal, "ops-metric-progress", "Proyectos en ejecución", 1)
    metric(portal, "ops-metric-paused", "Suspendidos", 0)
    expect(servicio).to_have_value("T&M")
    expect(portal.locator("#ops-managers")).not_to_contain_text("Laura Vega")
    snapshot(
        "operativa",
        {
            "todos": todos,
            "t&m": {
                "indicadores": visible(portal.locator("#ops-metrics")),
                "delivery_managers": visible(portal.locator("#ops-managers")),
            },
        },
    )


def test_dm_abre_proyecto_y_regresa(portal, datos, snapshot):
    portal.goto(f"{portal.base}/operativa/")
    portal.locator("#ops-managers").get_by_role(
        "link", name=re.compile("Alberto")
    ).first.click()
    portal.wait_for_url(re.compile(r"/operativa/delivery-manager/alberto/"))
    portal.wait_for_load_state("networkidle")
    dm_url = portal.url
    tabla = portal.locator("#dm-table table")
    expect(tabla).to_contain_text("Portal Pacientes")
    snapshot("delivery_manager", {"proyectos": rows(tabla)})

    tabla.get_by_role("link", name="Portal Pacientes").click()
    portal.wait_for_url(re.compile(r"/proyectos/2/\?volver="))
    regresar = portal.get_by_role("link", name=re.compile("^← Regresar"))
    expect(regresar).to_have_text("← Regresar a Delivery Manager")

    regresar.click()
    portal.wait_for_url(dm_url)
    expect(portal.locator("#dm-table table")).to_contain_text("HIS")


def test_cuenta_compara_margenes_y_regresa(portal, datos, snapshot):
    cuenta_url = (
        f"{portal.base}/cuenta/clinica-sur/?nombre=Clinica+Sur&{PERIODO}"
    )
    portal.goto(cuenta_url)
    proyectos = portal.get_by_role("table").filter(has_text="DELIVERY MANAGER")
    expect(proyectos).to_contain_text("Portal Pacientes")

    portal.get_by_role("link", name="Comparar margen vendido y real").click()
    portal.wait_for_url(re.compile(r"/ejecutiva/oportunidades/"))
    assert "anio=2026" in portal.url
    margenes = portal.get_by_role("table").filter(has_text="MARGEN VENDIDO")
    expect(margenes).to_contain_text("OP.7")
    expect(margenes).not_to_contain_text("OP.9")
    snapshot(
        "cuenta_margenes",
        {"cuenta": rows(proyectos), "margenes": rows(margenes)},
    )

    regresar = portal.get_by_role("link", name="← Regresar a Clinica Sur")
    regresar.click()
    portal.wait_for_url(cuenta_url)
    expect(portal.get_by_role("heading", name="Clinica Sur")).to_be_visible()


def test_eva4_procesos_renovaciones_y_clientes(portal, datos, snapshot):
    portal.goto(f"{portal.base}/operativa/eva-4/")
    expect(portal.locator("#eva4-count")).to_have_text(
        "2 de 2 procesos activos"
    )
    snapshot(
        "eva4",
        {
            name: rows(portal.locator(f"#eva4-{name}"))
            for name in ("processes", "renewals", "clients")
        },
    )


def test_acuerdos_se_consultan_y_modifican_con_sesion(
    portal, datos, settings, client, django_user_model
):
    settings.PORTAL_LOGIN_REQUIRED = True
    user = django_user_model.objects.create_user("dm", password="x")
    client.force_login(user)
    portal.context.add_cookies(
        [
            {
                "name": "sessionid",
                "value": client.cookies["sessionid"].value,
                "url": portal.base,
            }
        ]
    )
    portal.goto(f"{portal.base}/cuenta/clinica-sur/?nombre=Clinica+Sur")
    seccion = portal.locator("#executive-agreements")
    expect(seccion).to_contain_text("Sin acuerdos")

    seccion.get_by_role("button", name="+ Agregar acuerdo o pendiente").click()
    formulario = seccion.locator("#agreement-form")
    formulario.get_by_label("Fecha de sesión").fill("2026-10-01")
    formulario.get_by_label("Título").fill("Revisar alcance de fase 2")
    formulario.get_by_role("button", name="Guardar").click()
    expect(seccion).to_contain_text("Revisar alcance de fase 2")

    seccion.get_by_label(
        "Cambiar estado de Revisar alcance de fase 2"
    ).select_option("progress")
    expect(seccion).to_contain_text("Estado actualizado.")
    acuerdo = ExecutiveAgreement.objects.get()
    assert (acuerdo.account, acuerdo.status) == ("Clinica Sur", "progress")

    portal.reload()
    expect(
        portal.get_by_label("Cambiar estado de Revisar alcance de fase 2")
    ).to_have_value("progress")


def test_sin_sesion_se_manda_a_iniciar_sesion(portal, datos, settings):
    settings.PORTAL_LOGIN_REQUIRED = True
    for path in (
        "/operativa/",
        "/operativa/eva-4/",
        "/operativa/delivery-manager/alberto/",
        "/cuenta/clinica-sur/",
        "/ejecutiva/oportunidades/",
        "/proyectos/2/",
    ):
        portal.goto(portal.base + path)
        assert "/admin/login/" in portal.url, path
