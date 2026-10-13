"""Vistas Ejecutiva, Operativa y Comercial."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.eva_loader import Eva1Load, Eva2Load
from apps.portal.services.portfolio_loader import PortfolioLoad
from tests.portal.builders import make_project

pytestmark = pytest.mark.django_db

LOADED_AT = datetime(
    2026, 10, 12, 10, 24, tzinfo=ZoneInfo("America/Mexico_City")
)


def stub_portfolio(monkeypatch, projects=(), error=""):
    load = PortfolioLoad(
        projects=tuple(projects),
        error=error,
        loaded_at=LOADED_AT,
    )
    monkeypatch.setattr("apps.portal.views.load_portfolio", lambda: load)


def portfolio():
    return [
        make_project(project_id="1", name="Alpha", client="ACME"),
        make_project(
            project_id="2",
            name="Portal Pacientes",
            client="Clinica Sur",
            service="T&M",
            delivery_manager="Alberto",
            health="Crítica",
            delay_days=12,
        ),
        make_project(
            project_id="3",
            name="HIS",
            delivery_manager="Alberto",
            health="Crítica",
            burn_hours=125.0,
        ),
        make_project(project_id="4", status_category="En Pausa"),
    ]


def test_executive_shows_decisions_hours_and_period(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/")
    html = response.content.decode()

    assert response.status_code == 200
    assert "Datos al 12/10/2026, 10:24" in html
    assert "01-oct-2026" in html
    assert "31-dic-2026" in html
    assert "Portal Pacientes" in html
    assert "excede en 25%" in html
    assert response.context["hours"].budget_hours == 300
    assert html.count('class="ej"') >= 4


def test_executive_without_projects_shows_empty_messages(client, monkeypatch):
    stub_portfolio(monkeypatch)

    html = client.get("/").content.decode()

    assert "Sin proyectos que mostrar todavía." in html
    assert "Sin horas que mostrar todavía." in html


def test_executive_without_problem_projects(client, monkeypatch):
    stub_portfolio(monkeypatch, [make_project()])

    html = client.get("/").content.decode()

    assert "Ningún proyecto en ejecución está crítico ni en riesgo." in html


def test_executive_shows_sheets_error_without_failing(client, monkeypatch):
    stub_portfolio(monkeypatch, error="Falta configurar el dashboard.")

    response = client.get("/")

    assert response.status_code == 200
    assert "No se pudo leer Google Sheets" in response.content.decode()


def test_operational_counts_real_projects(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/operativa/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["summary"].in_progress == 3
    assert response.context["summary"].paused == 1
    assert [item.name for item in response.context["managers"]] == [
        "Alberto",
        "Laura Vega",
    ]
    assert "Salud del portafolio" in html
    assert "<circle" in html
    assert 'name="servicio"' in html
    assert 'value="T&amp;M"' in html


def test_operational_filters_by_service_and_client(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    by_service = client.get("/operativa/", {"servicio": "T&M"})
    by_client = client.get("/operativa/", {"cuenta": "Clinica Sur"})
    nothing = client.get("/operativa/", {"servicio": "IXB"})

    assert by_service.context["summary"].in_progress == 1
    assert by_client.context["summary"].in_progress == 1
    assert nothing.context["has_projects"] is False
    assert "Ningún proyecto coincide con los filtros." in (
        nothing.content.decode()
    )
    assert 'value="T&amp;M" selected' in by_service.content.decode()


def test_operational_without_projects(client, monkeypatch):
    stub_portfolio(monkeypatch)

    html = client.get("/operativa/").content.decode()

    assert "Sin proyectos que mostrar todavía." in html


def test_operational_shows_sheets_error(client, monkeypatch):
    stub_portfolio(monkeypatch, error="Falta configurar el dashboard.")

    assert "No se pudo leer Google Sheets" in (
        client.get("/operativa/").content.decode()
    )


def test_commercial_is_marked_as_example(client):
    response = client.get("/comercial/")
    html = response.content.decode()

    assert response.status_code == 200
    assert "Cifras de ejemplo" in html
    assert "HubSpot" in html


def test_navigation_links_to_all_views_and_the_legacy_panel(
    client,
    monkeypatch,
):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/").content.decode()

    assert 'href="/"' in html
    assert 'href="/operativa/"' in html
    assert 'href="/comercial/"' in html
    assert 'href="/legacy/"' in html


def test_screens_without_view_yet_say_coming_soon(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/").content.decode()

    assert "data-pronto" in html
    assert ".dc.html" not in html


def test_login_is_required_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    for path in ("/", "/operativa/", "/comercial/"):
        response = client.get(path)

        assert response.status_code == 302
        assert response.url.startswith("/admin/login/")


def test_only_get_is_allowed(client):
    assert client.post("/operativa/").status_code == 405


def test_delivery_manager_page_lists_real_projects(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/operativa/delivery-manager/alberto/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["detail"].name == "Alberto"
    assert "Portal Pacientes" in html
    assert "Presupuesto usado: 125%" in html
    assert "12 días atrasado" in html
    assert 'href="/operativa/"' in html


def test_operational_cards_link_to_manager_and_suspended_pages(
    client,
    monkeypatch,
):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/").content.decode()

    assert 'href="/operativa/delivery-manager/alberto/"' in html
    assert 'href="/operativa/delivery-manager/laura-vega/"' in html
    assert 'href="/operativa/suspendidos/"' in html


def test_unknown_delivery_manager_is_404(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    assert client.get("/operativa/delivery-manager/nadie/").status_code == 404


def test_delivery_manager_page_without_data_goes_back_to_operational(
    client,
    monkeypatch,
):
    stub_portfolio(monkeypatch, error="Falta configurar el dashboard.")

    response = client.get("/operativa/delivery-manager/alberto/")

    assert response.status_code == 302
    assert response.url == "/operativa/"


def test_suspended_page_lists_paused_projects(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/operativa/suspendidos/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["suspended"].count == 1
    assert "Proyectos suspendidos" in html
    assert "Laura Vega" in html


def test_suspended_page_without_projects(client, monkeypatch):
    stub_portfolio(monkeypatch)

    html = client.get("/operativa/suspendidos/").content.decode()

    assert "No hay proyectos suspendidos." in html


def test_new_pages_require_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    for path in (
        "/operativa/suspendidos/",
        "/operativa/delivery-manager/alberto/",
    ):
        assert client.get(path).status_code == 302


def stub_eva1(monkeypatch, rows=(), error=""):
    load = Eva1Load(view=build_eva1_view(list(rows)), error=error)
    monkeypatch.setattr("apps.portal.views.load_eva1", lambda: load)


def eva_row(**overrides):
    row = {
        "idProyecto": "AER.001",
        "cliente": "ACME",
        "servicio": "AER",
        "nombre": "Backlog",
        "deliveryManager": "Laura Vega",
        "fte": 2,
        "ftePorRol": {"DEV": 2},
        "fechaInicio": "2026-01-01",
        "fechaFin": "2026-10-20",
        "budget": 1000,
        "burn": 1100.5,
        "avance": 110.1,
        "renewalDias": 8,
        "etc": -100.5,
    }
    row.update(overrides)

    return row


def test_eva1_shows_projects_and_alerts(client, monkeypatch):
    stub_eva1(monkeypatch, [eva_row()])

    response = client.get("/operativa/eva-1/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["eva"].total_projects == 1
    assert "AER.001" in html
    assert "Laura Vega" in html
    assert "20/10/26" in html
    assert 'class="bd bad"' in html
    assert "Definición por confirmar" in html


def test_eva1_without_projects_and_with_error(client, monkeypatch):
    stub_eva1(monkeypatch, error="Falta configurar el dashboard.")

    html = client.get("/operativa/eva-1/").content.decode()

    assert "No se pudo leer Google Sheets" in html
    assert "No hay proyectos AER o T&amp;M en progreso." in html


def test_operational_eva_cards_link_to_eva1(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/").content.decode()

    assert 'href="/operativa/eva-1/"' in html


def test_eva1_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/operativa/eva-1/").status_code == 302


def test_eva2_shows_stages_and_pivots(client, monkeypatch):
    row = {
        "deliveryManager": "Laura Vega",
        "idProyecto": "AMK.008_S4",
        "servicio": "RAAS",
        "nombre": "Alertas",
        "status": "Deployment",
        "fechaInicio": "2026-08-28T00:00:00",
        "fechaFin": "2026-10-13T00:00:00",
        "desviacionDias": 1,
        "budget": 141,
        "burn": 167.59,
        "etc": -26.59,
        "avance": 118.8,
        "wi": {"development": {"total": 56, "cerrados": 50, "pendientes": 6}},
        "etapas": {"development": {"cerrada": True}},
        "riesgos": ["R1"],
    }
    load = Eva2Load(view=build_eva2_view([row]), error="")
    monkeypatch.setattr("apps.portal.views.load_eva2", lambda: load)

    response = client.get("/operativa/eva-2/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["eva"].total_projects == 1
    assert "AMK.008_S4" in html
    assert "RaaS" in html
    assert "<span class=pd>6</span>" in html
    assert 'class="bd bad"' in html


def test_eva2_with_error_and_login(client, monkeypatch, settings):
    load = Eva2Load(view=build_eva2_view([]), error="Azure no responde.")
    monkeypatch.setattr("apps.portal.views.load_eva2", lambda: load)

    html = client.get("/operativa/eva-2/").content.decode()

    assert "Azure no responde." in html
    assert "No hay proyectos IXB o RaaS vigentes." in html

    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/operativa/eva-2/").status_code == 302


def test_operational_eva_cards_link_to_eva2(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/").content.decode()

    assert 'href="/operativa/eva-2/"' in html


def test_account_page_lists_its_projects(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/cuenta/clinica-sur/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["account"].name == "Clinica Sur"
    assert "Portal Pacientes" in html
    assert "12 días atrasado" in html
    assert "Con proyectos críticos" in html
    assert 'href="/operativa/"' in html


def test_unknown_account_is_404_or_goes_back_when_data_fails(
    client,
    monkeypatch,
):
    stub_portfolio(monkeypatch, portfolio())

    assert client.get("/cuenta/nadie/").status_code == 404

    stub_portfolio(monkeypatch, error="Falta configurar el dashboard.")
    response = client.get("/cuenta/acme/")

    assert response.status_code == 302
    assert response.url == "/operativa/"


def test_manager_and_suspended_pages_link_to_the_account(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    manager = client.get("/operativa/delivery-manager/alberto/")
    suspended = client.get("/operativa/suspendidos/")

    assert 'href="/cuenta/clinica-sur/"' in manager.content.decode()
    assert 'href="/cuenta/acme/"' in suspended.content.decode()


def test_account_page_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/cuenta/acme/").status_code == 302
