"""Vistas Ejecutiva, Operativa y Comercial."""

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
from django.core.cache import cache

from apps.portal.constants import FACTURABILITY_CACHE_PREFIX
from apps.portal.services.capacity_loader import CapacityLoad
from apps.portal.services.eva1 import build_eva1_view
from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.eva_loader import Eva1Load, Eva2Load
from apps.portal.services.facturability_loader import MonthSources
from apps.portal.services.portfolio_loader import PortfolioLoad
from apps.portal.services.project_loader import ProjectDashboardLoad
from apps.portal.services.time_cost import summarize_time_cost
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
        lambda *args, **kwargs: Eva1Load(
            view=build_eva1_view([]),
            error="",
        ),
    )
    monkeypatch.setattr(
        "apps.portal.views.load_eva2",
        lambda **kwargs: Eva2Load(view=build_eva2_view([]), error=""),
    )
    cache.clear()


def stub_portfolio(monkeypatch, projects=(), error=""):
    monkeypatch.setattr(
        "apps.portal.services.executive_population.population",
        lambda: [{"id": p.project_id} for p in projects],
    )
    load = PortfolioLoad(
        projects=tuple(projects),
        error=error,
        loaded_at=LOADED_AT,
    )
    monkeypatch.setattr(
        "apps.portal.views.load_portfolio", lambda *args, **kwargs: load
    )
    source_projects = tuple(
        SimpleNamespace(
            project_id=p.project_id,
            name=p.name,
            client=p.client,
            manager=p.delivery_manager,
            service=p.service,
            budget=p.budget_hours,
            burn=p.burn_hours,
            etc=p.etc_hours,
            progress=p.progress_percent,
            start="01/01/26",
            end="31/12/26",
            risk_titles=(),
            renewal_days=-p.delay_days,
        )
        for p in projects
    )
    monkeypatch.setattr(
        "apps.portal.views.load_eva2",
        lambda **kwargs: SimpleNamespace(
            view=SimpleNamespace(
                projects=source_projects,
                total_projects=len(source_projects),
                time_cost=summarize_time_cost(projects),
            ),
            error=error,
        ),
    )
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.eva_projects",
        lambda *args: tuple(projects),
    )
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.remaining_days",
        lambda p: p.renewal_days,
    )
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.tagged_investment",
        lambda *args, **kwargs: {
            "complete": False,
            "totals": {},
            "by_project": {},
        },
    )
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.manager_monthly_history",
        lambda *args: {"complete": False},
    )

    def account_data(client_name):
        return {
            "ok": True,
            "proyectos": [
                {
                    "id": p.project_id,
                    "nombre": p.name,
                    "servicio": p.service,
                    "budget": p.budget_hours,
                    "burn": p.burn_hours,
                    "estado": p.status_category,
                    "atrasado": p.delay_days > 0,
                    "excedido": p.burn_hours > p.budget_hours,
                }
                for p in projects
                if p.client == client_name
            ],
        }

    monkeypatch.setattr(
        "apps.ejecutivo.account_rpc.get_account_view",
        account_data,
    )


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
    assert html.count('class="ej"') >= 3


def test_executive_without_projects_shows_empty_messages(client, monkeypatch):
    stub_portfolio(monkeypatch)

    html = client.get("/").content.decode()

    assert "Sin proyectos que mostrar todavía." in html
    assert 'id="executive-ops-budget"' in html


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

    response = client.get("/operativa/datos/", {"bloque": "eva3"})
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

    by_service = client.get("/operativa/datos/", {"servicio": "T&M", "bloque": "eva3"})
    by_client = client.get("/operativa/datos/", {"cuenta": "Clinica Sur", "bloque": "eva3"})
    nothing = client.get("/operativa/datos/", {"servicio": "IXB", "bloque": "eva3"})

    assert by_service.context["summary"].in_progress == 1
    assert by_client.context["summary"].in_progress == 1
    assert nothing.context["has_projects"] is False
    assert "Ningún proyecto coincide con los filtros." in (
        nothing.content.decode()
    )
    assert 'value="T&amp;M" selected' in by_service.content.decode()


def test_operational_without_projects(client, monkeypatch):
    stub_portfolio(monkeypatch)

    html = client.get("/operativa/datos/", {"bloque": "eva3"}).content.decode()

    assert "Sin proyectos que mostrar todavía." in html


def test_operational_shows_sheets_error(client, monkeypatch):
    stub_portfolio(monkeypatch, error="Falta configurar el dashboard.")

    assert "Falta configurar el dashboard." in (
        client.get("/operativa/datos/", {"bloque": "eva3"}).content.decode()
    )


def test_commercial_reads_backlog_without_example_figures(client, monkeypatch):
    from tests.fakes import InMemorySheetRepository

    monkeypatch.setattr(
        "apps.portal.services.commercial_view.build_sheet_repository",
        lambda: InMemorySheetRepository(
            {
                "Backlog_Proyectos": [
                    ["Account Name", "Opportunity Name", "Opportunity Stage"],
                ],
            }
        ),
    )
    response = client.get("/comercial/")
    html = response.content.decode()

    assert response.status_code == 200
    assert "Cifras de ejemplo" not in html
    assert response.context["count"] == 0


def test_navigation_links_to_current_views_without_legacy_panel(
    client,
    monkeypatch,
):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/datos/", {"bloque": "eva3"}).content.decode()

    assert 'href="/"' in html
    assert 'href="/operativa/"' in html
    assert 'href="/comercial/"' in html
    assert 'href="/legacy/"' not in html


def test_screens_without_view_yet_say_coming_soon(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/datos/", {"bloque": "eva3"}).content.decode()

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

    response = client.get("/operativa/delivery-manager/alberto/?bloque=inv")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["detail"].name == "Alberto"
    assert "Portal Pacientes" in html
    assert "Presupuesto usado: 125%" in html
    assert response.context["project_rows"][0]["detail"] == "12 días de vencido"
    assert 'href="/operativa/"' in html


def test_operational_cards_keep_manager_links(
    client,
    monkeypatch,
):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/datos/", {"bloque": "eva3"}).content.decode()

    assert 'href="/operativa/delivery-manager/alberto/?nombre=Alberto"' in html
    assert 'href="/operativa/delivery-manager/laura-vega/?nombre=Laura%20Vega"' in html
    for path in (
        "/operativa/en-ejecucion/",
        "/operativa/en-tiempo/",
        "/operativa/suspendidos/",
    ):
        assert f'href="{path}"' not in html
        assert client.get(path).status_code == 404


def test_unknown_delivery_manager_is_404(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    assert client.get("/operativa/delivery-manager/nadie/?bloque=inv").status_code == 404


def test_delivery_manager_page_without_data_goes_back_to_operational(
    client,
    monkeypatch,
):
    stub_portfolio(monkeypatch, error="Falta configurar el dashboard.")

    response = client.get("/operativa/delivery-manager/alberto/?bloque=inv")

    assert response.status_code == 302
    assert response.url == "/operativa/"


def test_new_pages_require_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    for path in ("/operativa/delivery-manager/alberto/",):
        assert client.get(path).status_code == 302


def stub_eva1(monkeypatch, rows=(), error=""):
    load = Eva1Load(view=build_eva1_view(list(rows)), error=error)
    monkeypatch.setattr(
        "apps.portal.views.load_eva1", lambda *args, **kwargs: load
    )


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

    response = client.get("/operativa/eva-3/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["eva"].total_projects == 1
    assert "AER.001" in html
    assert 'href="/proyectos/AER.001/"' in html
    assert "Laura Vega" in html
    assert "20/10/26" in html
    assert 'class="bd bad"' in html
    assert "Promedio de Renovaci&oacute;n" in html
    assert "Avance promedio de los proyectos" in html


def test_eva1_without_projects_and_with_error(client, monkeypatch):
    stub_eva1(monkeypatch, error="Falta configurar el dashboard.")

    html = client.get("/operativa/eva-3/").content.decode()

    assert "No se pudo leer Google Sheets" in html
    assert "No hay proyectos AER o T&amp;M en progreso." in html


def test_operational_eva_cards_link_to_eva1(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/datos/", {"bloque": "eva3"}).content.decode()

    assert 'href="/operativa/eva-1/"' in html


def test_eva1_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/operativa/eva-3/").status_code == 302


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
    monkeypatch.setattr(
        "apps.portal.views.load_eva2", lambda *args, **kwargs: load
    )

    response = client.get("/operativa/eva-2/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["eva"].total_projects == 1
    assert "AMK.008_S4" in html
    assert 'href="/proyectos/AMK.008_S4/"' in html
    assert "RaaS" in html
    assert "<span class=pd>6</span>" in html
    assert 'class="bd bad"' in html


def test_eva2_with_error_and_login(client, monkeypatch, settings):
    load = Eva2Load(view=build_eva2_view([]), error="Azure no responde.")
    monkeypatch.setattr(
        "apps.portal.views.load_eva2", lambda *args, **kwargs: load
    )

    html = client.get("/operativa/eva-2/").content.decode()

    assert "Azure no responde." in html
    assert "No hay proyectos IXB o RaaS vigentes." in html

    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/operativa/eva-2/").status_code == 302


def test_operational_eva_cards_link_to_eva4(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/datos/", {"bloque": "eva3"}).content.decode()

    assert 'href="/operativa/eva-4/"' in html
    assert 'href="/operativa/eva-2/"' not in html


def test_account_page_lists_its_projects(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/cuenta/clinica-sur/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["client"] == "Clinica Sur"
    assert "Portal Pacientes" in html
    assert response.context["alerts"][0]["id"] == "2"
    assert response.context["risk_count"] == 1
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


def test_manager_page_links_to_the_account(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    manager = client.get("/operativa/delivery-manager/alberto/?bloque=inv")

    assert 'href="/cuenta/clinica-sur/"' in manager.content.decode()


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

    html = client.get("/operativa/datos/", {"bloque": "eva3"}).content.decode()

    assert 'href="/capacidad-instalada/">' in html


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
        "/operativa/delivery-manager/alberto/?bloque=inv"
    ).content.decode()
    account = client.get("/cuenta/clinica-sur/").content.decode()

    assert 'href="/proyectos/3/"' in executive
    assert 'href="/proyectos/3/"' in manager
    assert 'href="/proyectos/2/"' in account
    assert 'href="/proyecto/3/"' not in manager


def test_project_page_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/proyecto/1/").status_code == 302


def test_manager_cards_show_time_and_cost(client, monkeypatch):
    stub_portfolio(
        monkeypatch,
        [
            make_project(project_id="1", delay_days=4, progress_percent=40),
            make_project(project_id="2", delay_days=0, progress_percent=80),
        ],
    )

    operational = client.get("/operativa/datos/", {"bloque": "eva3"}).content.decode()
    detail = client.get("/operativa/delivery-manager/laura-vega/?bloque=inv")

    assert "2 d · 60%" in operational
    assert detail.context["detail"].time_cost.time_days == 2
    assert detail.context["detail"].time_cost.cost_percent == 60


def test_executive_top_accounts_are_real(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    response = client.get("/")
    healthy, unhealthy = response.context["top_accounts"]
    html = response.content.decode()

    assert healthy == ()
    assert [item.name for item in unhealthy] == ["Clinica Sur", "ACME"]
    assert 'id="healthy-financial-accounts"' in html
    assert 'href="/ejecutiva/cuentas/"' in html
    assert 'id="unhealthy-financial-accounts"' in html


def stub_history(monkeypatch, history=None, error=""):
    from apps.portal.services.kpi_history import build_kpi_history
    from apps.portal.services.kpi_history_loader import KpiHistoryLoad
    from tests.portal.test_kpi_history import NOW, sources

    load = KpiHistoryLoad(
        history=history
        or (None if error else build_kpi_history(sources(), NOW, 2026)),
        error=error,
    )
    monkeypatch.setattr(
        "apps.portal.views.load_kpi_history", lambda *args: load
    )


def test_kpis_page_shows_managers_and_totals(client, monkeypatch):
    monkeypatch.setattr("apps.portal.views.load_portfolio", lambda: pytest.fail("Proyectos no se consulta para KPIs"))
    stub_history(monkeypatch)

    response = client.get("/operativa/kpis-delivery-managers/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["kpis"].totals.total == 2
    assert "KPIs de Delivery Managers" in html
    assert 'href="/operativa/delivery-manager/ana/"' in html


def test_kpis_page_shows_monthly_and_quarterly_history(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    stub_history(monkeypatch)

    response = client.get(
        "/operativa/kpis-delivery-managers/?periodo=anio&anio=2026"
    )
    html = response.content.decode()

    assert response.context["month_matrix"].headers[0] == "Ene"
    assert "Oct*" in response.context["month_matrix"].headers
    assert [row.name for row in response.context["month_matrix"].rows] == [
        "Ana",
        "Beto",
    ]
    assert response.context["quarter_matrix"].headers[0] == "T1"
    assert response.context["period"].label == "2026"
    assert 'id="period-filter"' in html
    assert 'id="kpi-chart-data"' in html
    assert "Pendiente" not in html


def test_kpis_chart_shows_the_year_with_the_period_highlighted(
    client, monkeypatch
):
    stub_portfolio(monkeypatch, portfolio())
    stub_history(monkeypatch)

    response = client.get(
        "/operativa/kpis-delivery-managers/?periodo=mes&mes=2026-08"
    )
    chart = response.context["chart"]

    assert chart["labels"] == [
        "Ene",
        "Feb",
        "Mar",
        "Abr",
        "May",
        "Jun",
        "Jul",
        "Ago",
    ]
    assert chart["highlight"] == ["Ago"]

    response = client.get(
        "/operativa/kpis-delivery-managers/?periodo=mes&mes=2026-10"
    )
    current = response.context["chart"]
    assert current["labels"][-1] == "Oct*"
    assert current["highlight"] == ["Oct*"]


def test_kpis_page_explains_when_history_fails(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    stub_history(monkeypatch, error="Clockify no responde.")

    response = client.get("/operativa/kpis-delivery-managers/")
    html = response.content.decode()

    assert response.status_code == 200
    assert "month_matrix" not in response.context
    assert "No se pudo reconstruir el hist\u00f3rico." in html
    assert "Clockify no responde." in html


def test_kpis_page_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/operativa/kpis-delivery-managers/").status_code == 302


def test_operational_eva_cards_use_real_numbers(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    load = Eva1Load(view=build_eva1_view([eva_row(avance=40)]), error="")
    monkeypatch.setattr(
        "apps.portal.views.load_eva1", lambda *args, **kwargs: load
    )

    response = client.get("/operativa/datos/", {"bloque": "eva3"})
    html = response.content.decode()

    assert response.context["eva3_card"].total_projects == 1
    assert response.context["eva3_card"].time_cost.cost_percent == 40.0
    assert response.context["eva2_card"].available is True
    assert "40%" in html
    assert 'href="/operativa/kpis-delivery-managers/"' in html


def facturable_gse(*rows):
    areas = {}

    for person, area, _service, _hours in rows:
        areas.setdefault(area, set()).add(person)

    return {
        "ok": True,
        "areas": [
            {
                "area": area,
                "recursos": len(people),
                "personas": [{"nombre": name} for name in sorted(people)],
            }
            for area, people in areas.items()
        ],
        "detalle": [
            {
                "recurso": person,
                "area": area,
                "servicio": service,
                "horas": hours,
                "categorias": ["Facturable"],
            }
            for person, area, service, hours in rows
        ],
    }


def stub_facturability(monkeypatch):
    january = facturable_gse(("Ana", "DEV", "AER", 84))
    monkeypatch.setattr(
        "apps.portal.views.load_month_sources",
        lambda month: MonthSources(month=month, gse=january),
    )
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda month: [
            MonthSources(month="2026-01", gse=january),
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
    assert specialty.context["specialties"][0].name == "Dev"
    assert specialty.context["headcount"] == 1
    assert resource.context["rows"][0].percents == (50.0, None)
    assert resource.context["workdays"] == [21, 19]
    assert [option.label for option in general.context["role_options"]] == [
        "DEV",
    ]
    assert "Facturabilidad por recurso" in resource.content.decode()


def test_facturability_month_never_goes_past_today(client, monkeypatch):
    stub_facturability(monkeypatch)

    response = client.get("/operativa/facturabilidad/especialidad/?mes=2999-12")

    assert response.context["month"] < "2999-12"


def test_facturability_loads_every_month_with_only_operational_areas(
    client,
    monkeypatch,
):
    months = [f"2026-{number:02d}" for number in range(1, 9)]
    keys = [f"{FACTURABILITY_CACHE_PREFIX}{month}" for month in months]
    calls = []
    gse = facturable_gse(
        ("Ana", "DEV", "AER", 84),
        ("Eva", "QA", "IXB", 42),
        ("Dan", "DM", "AER", 100),
    )

    def read_gse(month):
        calls.append(month)
        return gse

    monkeypatch.setattr(
        "apps.portal.services.facturability_loader.read_gse_month",
        read_gse,
    )
    cache.delete_many(keys)
    try:
        response = client.get("/operativa/facturabilidad/?mes=2026-08")
        assert response.status_code == 200
        assert calls == months
        assert response.context["errors"] == []
        assert [item.month for item in response.context["months"]] == months
        for item in response.context["months"]:
            assert item.resources == 2
            assert item.fixed_hours == 84
            assert item.variable_hours == 42
        assert "sin personas vigentes" not in response.content.decode()
    finally:
        cache.delete_many(keys)


def test_facturability_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    for path in (
        "/operativa/facturabilidad/",
        "/operativa/facturabilidad/especialidad/",
        "/operativa/facturabilidad/recurso/",
    ):
        assert client.get(path).status_code == 302


def test_investment_page_reads_gse_categories(client, monkeypatch):
    gse = {
        "ok": True,
        "detalle": [
            {
                "area": "DEV",
                "proyecto": "Preventa",
                "categorias": ["Pre-Venta"],
                "horas": 12,
            },
            {
                "area": "QA",
                "proyecto": "Interno",
                "categorias": ["Internos"],
                "horas": 8,
            },
        ],
    }
    monkeypatch.setattr(
        "apps.portal.views.load_month_sources",
        lambda month: MonthSources(month=month, gse=gse),
    )

    response = client.get("/operativa/inversion/?mes=2026-09")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["investment"].totals.total == 20
    assert response.context["month"] == "2026-09"
    assert "Inversión operativa y comercial" in html
    assert "Pre-Venta" in html


def test_operational_investment_cards_use_cache_only(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    monkeypatch.setattr("apps.portal.views.peek_month_sources", lambda m: None)

    response = client.get("/operativa/datos/?actualizar=1")

    assert response.context["investment"]["loading"] is True

    cache.set(
        "portal:ops:investment:v2",
        {
            "complete": True,
            "totals": {"operational": 7, "commercial": 0},
        },
    )

    response = client.get("/operativa/datos/?actualizar=1")

    assert response.context["investment"]["totals"]["operational"] == 7


def test_missing_roster_months_show_one_note_at_the_end(client, monkeypatch):
    gse = {
        **facturable_gse(("Ana", "DEV", "AER", 84)),
        "plantillaAviso": "Bandas/rol no tiene banda.",
    }
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda month: [
            MonthSources(month="2026-01", gse=gse),
            MonthSources(month="2026-02", gse=gse),
        ],
    )

    for path in (
        "/operativa/facturabilidad/?mes=2026-02",
        "/operativa/facturabilidad/recurso/?mes=2026-02",
    ):
        html = client.get(path).content.decode()

        assert html.count("Bandas/rol no trae banda para: Ene, Feb.") == 1
        assert html.index("Bandas/rol no trae banda") > html.index("<table")


def test_investment_requires_login_when_configured(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/operativa/inversion/").status_code == 302


def test_operations_summary_fragment(client, monkeypatch):
    gse = facturable_gse(("Ana", "DEV", "AER", 134.4))
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda month: [MonthSources(month="2026-09", gse=gse)],
    )

    response = client.get("/operativa/operations-resumen/")
    html = response.content.decode()

    assert response.status_code == 200
    assert response.context["ops"].gap == 10.0
    assert "80%" in html
    assert "puntos arriba de la meta" in html
    assert "<html" not in html


def test_operational_page_loads_operations_apart(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())

    html = client.get("/operativa/datos/", {"bloque": "eva3"}).content.decode()

    assert 'data-summary-endpoint="/operations/resumen/"' in html
    assert 'src="/static/portal/js/operativa.js"' in html
    assert 'href="/operativa/facturabilidad/"' in html
    assert 'href="/operativa/facturabilidad/especialidad/"' in html
    assert 'href="/operativa/facturabilidad/recurso/"' in html


def test_operations_fragment_without_login(client, settings):
    settings.PORTAL_LOGIN_REQUIRED = True

    assert client.get("/operativa/operations-resumen/").status_code == 401


def test_facturability_role_filter(client, monkeypatch):
    gse = facturable_gse(
        ("Ana", "DEV", "AER", 40),
        ("Dan", "DM", "AER", 60),
        ("Eva", "R&D", "AER", 80),
    )
    monkeypatch.setattr(
        "apps.portal.views.load_month_sources",
        lambda month: MonthSources(month=month, gse=gse),
    )

    default = client.get("/operativa/facturabilidad/especialidad/")
    chosen = client.get(
        "/operativa/facturabilidad/especialidad/",
        {"roles": "1", "rol": ["DEV", "DM", "R&D"]},
    )

    assert [row.name for row in default.context["specialties"]] == ["Dev"]
    assert default.context["selected"].fixed_hours == 40
    assert "Áreas mostradas" in default.content.decode()
    assert len(chosen.context["specialties"]) == 1
    assert chosen.context["selected"].fixed_hours == 40
    assert [r.label for r in chosen.context["role_options"]] == ["DEV"]


def test_kpis_page_filters_a_closed_month_and_a_quarter(client, monkeypatch):
    stub_portfolio(monkeypatch, portfolio())
    stub_history(monkeypatch)

    month = client.get(
        "/operativa/kpis-delivery-managers/?periodo=mes&mes=2026-02"
    )
    quarter = client.get(
        "/operativa/kpis-delivery-managers/?periodo=trimestre&anio=2026&trim=1"
    )

    assert month.context["cut_is_current"] is False
    assert month.context["cut_label"] == "28/02/2026"
    assert month.context["kpis"].totals.total == 2
    assert month.context["month_matrix"].headers == ("Feb",)
    assert quarter.context["month_matrix"].headers == ("Ene", "Feb", "Mar")
    assert quarter.context["quarter_matrix"].headers == ("T1",)
    assert "?periodo=trimestre&amp;anio=2026&amp;trim=1" in (
        quarter.content.decode()
    )


def test_facturability_period_year_quarter_and_month(client, monkeypatch):
    january = facturable_gse(("Ana", "DEV", "AER", 84))
    monkeypatch.setattr(
        "apps.portal.views.load_month_sources",
        lambda month: MonthSources(month=month, gse=january),
    )
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda month: [
            MonthSources(month=f"2026-{number:02d}", gse=january)
            for number in range(1, int(month[5:7]) + 1)
        ],
    )

    year = client.get("/operativa/facturabilidad/?periodo=anio&anio=2026")
    quarter = client.get(
        "/operativa/facturabilidad/?periodo=trimestre&anio=2026&trim=1"
    )
    month = client.get("/operativa/facturabilidad/?mes=2026-02")
    specialty = client.get(
        "/operativa/facturabilidad/especialidad/"
        "?periodo=trimestre&anio=2026&trim=1"
    )

    assert year.context["selected"].label == "2026"
    assert quarter.context["selected"].label == "T1 2026"
    assert quarter.context["selected"].capacity == 8 * (21 + 19 + 21)
    assert quarter.context["in_period"] == ("2026-01", "2026-02", "2026-03")
    assert len(quarter.context["months"]) == 3
    assert month.context["selected"].month == "2026-02"
    assert specialty.context["selected"].label == "T1 2026"
    assert specialty.context["specialties"][0].name == "Dev"
    assert specialty.context["specialties"][0].capacity == 8 * (21 + 19 + 21)
    assert 'id="period-filter"' in year.content.decode()
