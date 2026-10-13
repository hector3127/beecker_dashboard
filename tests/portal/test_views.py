"""Vistas Ejecutiva, Operativa y Comercial."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from apps.portal.services.capacity_loader import CapacityLoad
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.eva_loader import Eva1Load, Eva2Load
from apps.portal.services.facturability_loader import MonthSources
from apps.portal.services.portfolio_loader import PortfolioLoad
from apps.portal.services.project_loader import ProjectDashboardLoad
from tests.portal.builders import make_project

pytestmark = pytest.mark.django_db

LOADED_AT = datetime(
    2026, 10, 12, 10, 24, tzinfo=ZoneInfo("America/Mexico_City")
)


@pytest.fixture(autouse=True)
def no_real_eva1(monkeypatch):
    """Operativa lee EVA 1; en pruebas nunca se consulta la hoja MPB."""
    monkeypatch.setattr(
        "apps.portal.views.load_eva1",
        lambda: Eva1Load(view=build_eva1_view([]), error="Sin MPB."),
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


def stub_capacity(monkeypatch, data=None, error=""):
    load = CapacityLoad(data=data or {}, error=error)
    calls = []

    def fake_load(month, refresh=False):
        calls.append((month, refresh))
        return load

    monkeypatch.setattr("apps.portal.views.load_capacity", fake_load)

    return calls


def capacity_data():
    rule = {
        "cargabilidad": "Cargable",
        "facturable": "Facturable",
        "capacidad": "Afecta Capacidad",
        "afecta": True,
    }

    return {
        "ok": True,
        "bandaColumna": "Octubre",
        "filas": [
            {
                "recurso": "Ana Perez",
                "banda": "B2",
                "concepto": "Proyecto",
                "tecnologia": "DEV",
                "manager": "Brandon Sotelo",
                "idProyecto": "GPO.007",
                "proyecto": "MultiProfile",
                "horasDiarias": 4,
                "horasEstimadas": 100,
                "activo": True,
                "regla": rule,
            },
        ],
    }


def test_capacity_page_shows_resources_and_base_capacity(client, monkeypatch):
    calls = stub_capacity(monkeypatch, capacity_data())

    response = client.get(
        "/operativa/capacidad-instalada/?mes=2026-10&jornada=6&buscar=ana",
    )
    html = response.content.decode()

    assert response.status_code == 200
    assert calls == [("2026-10", False)]
    assert response.context["capacity"].resources == 1
    assert response.context["capacity"].base_hours == 22 * 6
    assert "Ana Perez" in html
    assert "GPO.007" in html
    assert "Octubre 2026" in html
    assert "Pendiente" in html


def test_capacity_page_defaults_and_refresh(client, monkeypatch):
    calls = stub_capacity(monkeypatch, capacity_data())

    client.get("/operativa/capacidad-instalada/?mes=mala&actualizar=1")

    month, refresh = calls[0]
    assert len(month) == 7
    assert month[4] == "-"
    assert refresh is True


def test_capacity_page_with_error_and_without_rows(client, monkeypatch):
    stub_capacity(monkeypatch, error="Falta la hoja Recursos.")

    html = client.get("/operativa/capacidad-instalada/").content.decode()

    assert "Falta la hoja Recursos." in html
    assert "No se pudo leer Capacidad instalada." in html


def test_capacity_csv_download(client, monkeypatch):
    stub_capacity(monkeypatch, capacity_data())

    response = client.get(
        "/operativa/capacidad-instalada/exportar/?mes=2026-10",
    )
    text = response.content.decode("utf-8")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert "capacidad-instalada-2026-10.csv" in response["Content-Disposition"]
    assert text.startswith("\ufeffRecurso,Banda")
    assert "Ana Perez" in text


def test_capacity_pages_require_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    for path in (
        "/operativa/capacidad-instalada/",
        "/operativa/capacidad-instalada/exportar/",
    ):
        assert client.get(path).status_code == 302


def test_operational_page_links_to_capacity(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/").content.decode()

    assert 'href="/operativa/capacidad-instalada/"' in html


def stub_project(monkeypatch, data=None, error=""):
    load = ProjectDashboardLoad(data=data or {}, error=error)
    monkeypatch.setattr(
        "apps.portal.views.load_project_dashboard",
        lambda project_id: load,
    )


def test_project_page_shows_real_numbers_and_decision(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    stub_project(
        monkeypatch,
        {
            "proyecto": {"fechaFinEstimada": "2026-10-28T00:00:00.000Z"},
            "riesgosCriticos": [
                {"descripcion": "Sin acceso", "impacto": "Alto"},
            ],
        },
    )

    response = client.get("/proyecto/3/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["page"].name == "HIS"
    assert "Requiere decisión de dirección" in html
    assert "Sin acceso" in html
    assert "28/10/2026" in html
    assert 'href="/cuenta/acme/"' in html


def test_project_page_without_detail_shows_notice(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    stub_project(monkeypatch, error="Sin Clockify.")

    html = client.get("/proyecto/1/").content.decode()

    assert "Sin Clockify." in html
    assert "Sin riesgos abiertos." in html


def test_unknown_project_is_404_or_goes_back_when_data_fails(
    client,
    monkeypatch,
):
    stub_portfolio(monkeypatch, portfolio())

    assert client.get("/proyecto/nadie/").status_code == 404

    stub_portfolio(monkeypatch, error="Falta configurar el dashboard.")

    assert client.get("/proyecto/1/").url == "/operativa/"


def test_other_pages_link_to_the_project(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    executive = client.get("/").content.decode()
    manager = client.get(
        "/operativa/delivery-manager/alberto/"
    ).content.decode()
    account = client.get("/cuenta/clinica-sur/").content.decode()
    suspended = client.get("/operativa/suspendidos/").content.decode()

    assert 'href="/proyecto/3/"' in executive
    assert 'href="/proyecto/3/"' in manager
    assert 'href="/proyecto/2/"' in account
    assert 'href="/proyecto/4/"' in suspended


def test_project_page_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/proyecto/1/").status_code == 302


def test_in_progress_page_groups_by_manager(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/operativa/en-ejecucion/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["listed"] == 3
    assert [group.name for group in response.context["groups"]] == [
        "Alberto",
        "Laura Vega",
    ]
    assert "Proyectos en ejecución por Delivery Manager" in html
    assert 'href="/proyecto/3/"' in html
    assert 'href="/cuenta/clinica-sur/"' in html
    assert 'href="/operativa/delivery-manager/alberto/"' in html


def test_on_time_page_lists_only_on_time(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/operativa/en-tiempo/")
    html = response.content.decode()

    assert response.context["listed"] == 1
    assert "Proyectos en tiempo por Delivery Manager" in html
    assert 'href="/proyecto/1/"' in html
    assert 'href="/proyecto/3/"' not in html


def test_group_pages_without_projects_and_login(client, monkeypatch, settings):
    stub_portfolio(monkeypatch)

    assert "No hay proyectos en tiempo." in (
        client.get("/operativa/en-tiempo/").content.decode()
    )
    assert "No hay proyectos en ejecución." in (
        client.get("/operativa/en-ejecucion/").content.decode()
    )

    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/operativa/en-ejecucion/").status_code == 302
    assert client.get("/operativa/en-tiempo/").status_code == 302


def test_operational_cards_link_to_grouped_pages(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/").content.decode()

    assert 'href="/operativa/en-ejecucion/"' in html
    assert 'href="/operativa/en-tiempo/"' in html


def test_manager_cards_show_time_and_cost(client, monkeypatch):
    stub_portfolio(
        monkeypatch,
        [
            make_project(project_id="1", delay_days=4, progress_percent=40),
            make_project(project_id="2", delay_days=0, progress_percent=80),
        ],
    )

    operational = client.get("/operativa/").content.decode()
    detail = client.get("/operativa/delivery-manager/laura-vega/")

    assert "2 d · 60%" in operational
    assert "2 d · 60%" in detail.content.decode()


def test_executive_top_accounts_are_real(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/")
    healthy, unhealthy = response.context["top_accounts"]
    html = response.content.decode()

    assert healthy == ()
    assert [item.name for item in unhealthy] == ["Clinica Sur", "ACME"]
    assert "Ninguna cuenta tiene todos sus proyectos en tiempo." in html
    assert 'href="/cuenta/acme/"' in html
    assert 'href="/cuenta/clinica-sur/"' in html


def test_kpis_page_shows_managers_and_totals(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/operativa/kpis-delivery-managers/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["kpis"].totals.total == 3
    assert "KPIs de Delivery Managers" in html
    assert 'href="/operativa/delivery-manager/alberto/"' in html


def test_kpis_page_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/operativa/kpis-delivery-managers/").status_code == 302


def test_operational_eva_cards_use_real_numbers(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    load = Eva1Load(view=build_eva1_view([eva_row(avance=40)]), error="")
    monkeypatch.setattr("apps.portal.views.load_eva1", lambda: load)

    response = client.get("/operativa/")
    html = response.content.decode()

    assert response.context["eva1_card"].total_projects == 1
    assert response.context["eva1_card"].time_cost.cost_percent == 40.0
    assert response.context["eva2_card"].available is False
    assert "40%" in html
    assert 'href="/operativa/kpis-delivery-managers/"' in html


def stub_facturability(monkeypatch):
    sources = {
        "gse": {
            "ok": True,
            "detalle": [
                {
                    "recurso": "Ana",
                    "area": "DEV",
                    "servicio": "AER",
                    "horas": 80,
                },
            ],
        },
        "capacity": {
            "filas": [
                {"recurso": "Ana", "rol": "DEV", "horasEstimadas": 160},
            ],
        },
    }
    monkeypatch.setattr(
        "apps.portal.views.load_month_sources",
        lambda month: MonthSources(month=month, **sources),
    )
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda month: [
            MonthSources(month="2026-01", **sources),
            MonthSources(month="2026-02", error="GSE: sin base"),
        ],
    )


def test_facturability_pages(client, monkeypatch):
    stub_facturability(monkeypatch)

    general = client.get("/operativa/facturabilidad/?mes=2026-02")
    specialty = client.get("/operativa/facturabilidad/especialidad/")
    resource = client.get("/operativa/facturabilidad/recurso/")

    assert general.status_code == 200
    assert general.context["first"].fixed_percent == 50.0
    assert general.context["selected"].error == "GSE: sin base"
    assert "Meses sin datos completos" in general.content.decode()
    assert specialty.context["specialties"][0].name == "DEV"
    assert specialty.context["headcount"] == 1
    assert resource.context["rows"][0].percents == (50.0, None)
    assert "Facturabilidad por recurso" in resource.content.decode()


def test_facturability_month_never_goes_past_today(client, monkeypatch):
    stub_facturability(monkeypatch)

    response = client.get("/operativa/facturabilidad/especialidad/?mes=2999-12")

    assert response.context["month"] < "2999-12"


def test_facturability_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    for path in (
        "/operativa/facturabilidad/",
        "/operativa/facturabilidad/especialidad/",
        "/operativa/facturabilidad/recurso/",
    ):
        assert client.get(path).status_code == 302
