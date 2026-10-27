"""Return links must resolve to live portal routes without browser history."""

import re
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from django.template import Context, Template
from django.template.loader import render_to_string
from django.urls import resolve

from apps.portal.services.opportunity_profitability import OPPORTUNITY_VERSION

ROOT = Path(__file__).resolve().parents[2] / "tests/reference/templates/portal"


@pytest.fixture(autouse=True)
def no_background_refresh(monkeypatch):
    """Las pruebas de navegación no deben lanzar lecturas de proveedores."""
    monkeypatch.setattr(
        "apps.portal.services.executive_refresh.request_refresh",
        lambda *a, **k: {"state": "running"},
    )


LINKS = []
for source in ROOT.glob("*.html"):
    for anchor in re.findall(
        r"<a\b[^>]*>.*?</a>", source.read_text(encoding="utf-8"), re.S
    ):
        text = re.sub(r"<[^>]+>", "", anchor)
        if any(
            label in text
            for label in ("Regresar", "Volver", "Operación de proyectos")
        ):
            LINKS.append((source.name, anchor))


@pytest.mark.parametrize("name,anchor", LINKS, ids=[item[0] for item in LINKS])
def test_return_links_resolve_to_correct_section(name, anchor):
    html = Template(anchor).render(
        Context({"cost_back": "/", "executive_query": "periodo=anio&anio=2026"})
    )
    href = re.search(r'href="([^"]+)"', html).group(1).replace("&amp;", "&")
    assert not urlsplit(href).netloc
    match = resolve(urlsplit(href).path)
    expected = (
        "portal:ejecutiva"
        if name
        in {
            "comercial.html",
            "costos_detalle.html",
            "oportunidades_financieras.html",
        }
        else "portal:operativa"
    )
    assert match.view_name == expected
    assert "target=" not in html
    assert "history.back" not in html


def test_commercial_return_preserves_selected_executive_dates():
    html = render_to_string(
        "pages/commercial.html",
        {
            "from_executive": True,
            "start": "2026-03-01",
            "end": "2026-06-30",
            "error": "Fuente no disponible",
            "pipeline_details": {},
        },
    )
    href = (
        re.search(r'data-portal-back href="([^"]+)"', html)
        .group(1)
        .replace("&amp;", "&")
    )
    assert resolve(urlsplit(href).path).view_name == "portal:ejecutiva"
    assert parse_qs(urlsplit(href).query) == {
        "periodo": ["rango"],
        "desde": ["2026-03-01"],
        "hasta": ["2026-06-30"],
    }


def test_project_return_is_visible_before_async_dashboard_loads():
    html = render_to_string(
        "pages/project_detail.html",
        {"project_id": "TYM.AAU.001", "project_context": {"id": "TYM.AAU.001"}},
    )
    assert html.index("Regresar a Operativa") < html.index(
        'id="view-container"'
    )


@pytest.mark.parametrize("from_executive", [False, True])
def test_commercial_back_only_for_executive_entry(from_executive):
    html = render_to_string(
        "pages/commercial.html",
        {
            "from_executive": from_executive,
            "error": "Sin conexión",
            "pipeline_details": {},
        },
    )
    assert ("data-portal-back" in html) is from_executive


@pytest.mark.parametrize(
    "query,expected",
    [
        ("", False),
        ("pipeline_year=2026", False),
        ("origen=business-overview&desde=2026-01-01&hasta=2026-12-31", True),
        ("desde=ejecutiva", True),
    ],
)
def test_commercial_origin_flag_survives_date_filters(query, expected):
    from unittest.mock import Mock, patch

    from django.http import QueryDict

    from apps.portal.services.commercial_view import build_commercial_context

    reader = Mock()
    reader.read_values.return_value = []
    with patch(
        "apps.portal.services.commercial_view.build_sheet_repository",
        return_value=reader,
    ):
        assert (
            build_commercial_context(QueryDict(query))["from_executive"]
            is expected
        )


@pytest.mark.parametrize(
    "path,label",
    [
        (
            "/ejecutiva/cuentas/?periodo=anio&anio=2026&buscar=Heineken&clasificacion=pending",
            "Todas las cuentas",
        ),
        ("/?periodo=mes&anio=2026&mes=10", "Business Overview"),
        (
            "/cuenta/heineken/?nombre=Heineken+Mexico&volver=%2Fejecutiva%2Fcuentas%2F",
            "Heineken Mexico",
        ),
    ],
)
def test_costs_return_to_immediate_parent(client, settings, path, label):
    settings.PORTAL_LOGIN_REQUIRED = False
    response = client.get(
        "/ejecutiva/costos/detalle/",
        {
            "vista": "proyectos",
            "nombre": "Heineken Mexico",
            "volver": path,
            "periodo": "anio",
            "anio": 2026,
        },
    )
    assert response.status_code == 200
    assert response.context["cost_back"] == path
    assert response.context["cost_back_label"] == label


@pytest.mark.parametrize(
    "target",
    [
        "https://other.test/",
        "//other.test/",
        "/api/rpc/getDashboardData/",
        "/no-existe/",
        "/\\other.test/",
        "/ejecutiva/acuerdos/",
    ],
)
def test_return_rejects_non_page_destinations(target):
    from django.test import RequestFactory

    from apps.portal.services.return_navigation import return_context

    request = RequestFactory().get("/cuenta/heineken/", {"volver": target})
    assert return_context(request, "/operativa/", "Operativa") == {
        "back_url": "/operativa/",
        "back_label": "Operativa",
    }


@pytest.mark.parametrize(
    "origin,label",
    [("/", "Business Overview"), ("/operativa/?servicio=AER", "Operativa")],
)
def test_hours_return_preserves_account_origin(
    client, monkeypatch, settings, origin, label
):
    from html import unescape
    from urllib.parse import urlencode

    settings.PORTAL_LOGIN_REQUIRED = False
    monkeypatch.setattr(
        "apps.portal.views.authorized_account",
        lambda request, slug: "Heineken Mexico",
    )
    parent = "/cuenta/heineken-mexico/?" + urlencode(
        {"nombre": "Heineken Mexico", "volver": origin}
    )
    response = client.get(
        "/cuenta/heineken-mexico/horas/",
        {"nombre": "Heineken Mexico", "volver": parent},
    )
    assert response.status_code == 200
    link = re.search(
        r'<a[^>]*data-portal-back[^>]*href="([^"]+)"', response.content.decode()
    )
    assert link is not None
    target = unescape(link.group(1))
    assert target == parent
    account = client.get(target)
    assert account.context["back_url"] == origin
    assert account.context["back_label"] == label


def test_account_returns_to_account_list_instead_of_operations(
    client, monkeypatch, settings
):
    settings.PORTAL_LOGIN_REQUIRED = False
    monkeypatch.setattr(
        "apps.ejecutivo.account_rpc.get_account_view",
        lambda name: {"ok": True, "proyectos": []},
    )
    parent = "/ejecutiva/cuentas/?periodo=anio&anio=2026&buscar=Heineken"
    response = client.get(
        "/cuenta/heineken/", {"nombre": "Heineken Mexico", "volver": parent}
    )
    assert response.context["back_url"] == parent
    assert response.context["back_label"] == "Todas las cuentas"
    assert "Regresar a Todas las cuentas" in response.content.decode()


@pytest.mark.parametrize("account", ["Heineken Mexico", "Otra cuenta"])
def test_opportunity_comparison_returns_to_account_after_date_filters(
    client, monkeypatch, settings, account
):
    from urllib.parse import urlencode

    from django.utils.text import slugify

    settings.PORTAL_LOGIN_REQUIRED = False
    monkeypatch.setattr(
        "apps.portal.services.financial_cache.cached_financial_snapshot",
        lambda: {
            "opportunities": {
                "version": OPPORTUNITY_VERSION,
                "start": "2026-01-01",
                "end": "2026-12-31",
                "opportunities": [],
            }
        },
    )
    parent = f"/cuenta/{slugify(account)}/?" + urlencode(
        {
            "nombre": account,
            "volver": "/ejecutiva/cuentas/?buscar=Heineken",
        }
    )
    response = client.get(
        "/ejecutiva/oportunidades/",
        {
            "nombre": account,
            "volver": parent,
        },
    )
    assert response.context["back_url"] == parent
    assert response.context["back_label"] == account
    html = response.content.decode()
    assert f"Regresar a {account}" in html
    hidden = re.search(
        r'<input type="hidden" name="volver" value="([^"]+)"', html
    )
    from html import unescape

    response = client.get(
        "/ejecutiva/oportunidades/",
        {
            "nombre": account,
            "volver": unescape(hidden.group(1)),
            "periodo": "rango",
            "desde": "2026-03-01",
            "hasta": "2026-09-30",
        },
    )
    assert response.context["back_url"] == parent
    assert response.context["back_label"] == account
