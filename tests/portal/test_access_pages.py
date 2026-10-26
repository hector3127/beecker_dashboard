"""Pantallas con cifras de todo el portafolio: capacidad y alcance total.

Con los accesos encendidos cada pantalla pide su capacidad; las que muestran
cifras del equipo o del portafolio entero no se pueden recortar por cuenta, asi
que una persona con alcance limitado recibe 403 y nunca llega a las fuentes.
"""

import pytest
from django.urls import reverse

from apps.access.scope import AccessScope
from apps.portal import views

pytestmark = pytest.mark.django_db

PAGES = {
    "view_operations": [
        "eva1",
        "eva1_cerrados",
        "eva2",
        "eva3",
        "eva3_cerrados",
        "inversion",
        "facturabilidad",
        "facturabilidad_especialidad",
        "facturabilidad_recurso",
        "facturabilidad_area",
        "capacidad",
        "capacidad_csv",
        "capacidad_detalle",
    ],
    "view_commercial": ["comercial"],
    "view_executive": [
        "actualizacion_ejecutiva",
        "todas_cuentas",
    ],
    "view_costs": ["ingresos", "costos_detalle"],
}
CASES = [(name, code) for code, names in PAGES.items() for name in names]


@pytest.fixture(autouse=True)
def no_sources(monkeypatch):
    """Si una peticion pasara el control, llegaria aqui y la prueba falla."""

    def fail(*args, **kwargs):
        pytest.fail("Se consultaron las fuentes sin permiso")

    for name in ("load_portfolio", "load_eva2", "load_eva1"):
        monkeypatch.setattr(views, name, fail)


@pytest.mark.parametrize("name,code", CASES)
def test_without_the_capability_it_is_forbidden(client, enforced, name, code):
    other = next(c for c in PAGES if c != code)
    enforced("sin", caps=frozenset({other}))

    assert client.get(reverse(f"portal:{name}")).status_code == 403


@pytest.mark.parametrize("name,code", CASES)
def test_limited_scope_cannot_see_whole_portfolio_figures(
    client, enforced, name, code
):
    enforced(
        "ana",
        caps=frozenset({code}),
        scope=AccessScope.limited(accounts=["Acme"]),
    )

    assert client.get(reverse(f"portal:{name}")).status_code == 403


@pytest.mark.parametrize("name,code", CASES)
def test_anonymous_goes_to_login_when_enforced(client, enforced, name, code):
    # enforced() crea una sesion; se sale para probar a una persona anonima.
    enforced("temporal", caps=frozenset())
    client.logout()

    response = client.get(reverse(f"portal:{name}"))

    assert response.status_code == 302
    assert "login" in response.url


def test_a_project_of_a_foreign_account_does_not_exist(
    client, enforced, monkeypatch
):
    from tests.portal.test_views import portfolio, stub_portfolio

    stub_portfolio(monkeypatch, portfolio())
    monkeypatch.setattr(
        views, "load_portfolio", views.load_portfolio, raising=True
    )
    enforced(
        "ana",
        caps=frozenset({"view_operations"}),
        scope=AccessScope.limited(accounts=["ACME"]),
    )

    foreign = client.get("/proyectos/2/")  # Clinica Sur
    own = client.get("/proyectos/1/")  # ACME

    assert foreign.status_code == 404
    assert own.status_code == 200
    assert client.get("/proyecto/2/").status_code == 404


def test_a_project_needs_the_operations_capability(client, enforced):
    enforced("sin", caps=frozenset({"view_costs"}))

    assert client.get("/proyectos/2/").status_code == 403


def test_the_cost_list_of_an_account_follows_scope(client, enforced):
    enforced(
        "ana",
        caps=frozenset({"view_costs"}),
        scope=AccessScope.limited(accounts=["ACME"]),
    )
    url = reverse("portal:costos_detalle")

    assert client.get(url, {"nombre": "Clinica Sur"}).status_code == 404
    assert client.get(url).status_code == 403


@pytest.mark.parametrize("name", ["eva2", "capacidad", "capacidad_detalle"])
@pytest.mark.parametrize("grant", ["limited", "wrong", "anonymous"])
def test_retired_query_does_not_bypass_page_access(
    client, enforced, name, grant
):
    enforced(
        "ana",
        caps=frozenset(
            {"view_costs"} if grant == "wrong" else {"view_operations"}
        ),
        scope=AccessScope.limited(accounts=["Acme"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()
    response = client.get(reverse(f"portal:{name}"), {"vista": "anterior"})
    assert response.status_code == (302 if grant == "anonymous" else 403)
