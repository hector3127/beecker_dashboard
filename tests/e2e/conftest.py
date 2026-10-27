"""Navegador real contra el portal actual, sin salir a internet.

Los datos vienen de los mismos dobles que usan las pruebas de vistas.
El servidor de pruebas corre en este proceso, por eso los monkeypatch
alcanzan a las vistas que atiende.
"""

import json
import os
import re
import socket
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import pytest

# Playwright corre un ciclo asincrono en el hilo principal; el ORM de las
# pruebas es sincrono y Django lo bloquearia sin este permiso.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost"}
SNAPSHOTS = Path(__file__).parent / "snapshots"
# La hora de corte cambia en cada corrida; no es parte de lo que se compara.
STAMP = re.compile(r"\d{2}/\d{2}/\d{4},? \d{2}:\d{2}")


def visible(locator: Any) -> str:
    """Texto que ve la persona, en una linea y sin la hora de corte."""
    return STAMP.sub("<corte>", " ".join(locator.inner_text().split()))


def rows(table: Any) -> list[str]:
    """Una entrada por fila para que una diferencia se lea facil."""
    return [visible(row) for row in table.locator("tr").all()]


@pytest.fixture
def snapshot() -> Callable[[str, dict[str, Any]], None]:
    """Compara lo visible con tests/e2e/snapshots/<nombre>.json.

    UPDATE_SNAPSHOTS=1 los vuelve a escribir: solo se hace a proposito,
    revisando el cambio, porque son la referencia de la migracion.
    """

    def check(name: str, regions: dict[str, Any]) -> None:
        path = SNAPSHOTS / f"{name}.json"
        if os.environ.get("UPDATE_SNAPSHOTS") == "1":
            SNAPSHOTS.mkdir(exist_ok=True)
            text = json.dumps(regions, ensure_ascii=False, indent=2)
            path.write_text(text + "\n", encoding="utf-8")
        assert path.exists(), f"Falta {path.name}: corre con UPDATE_SNAPSHOTS=1"
        assert regions == json.loads(path.read_text(encoding="utf-8"))

    return check


@pytest.fixture(autouse=True)
def _no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ninguna fuente real (Sheets, Clockify, Azure) se consulta."""
    connect = socket.socket.connect

    def local_only(sock: socket.socket, address: Any) -> Any:
        host = address[0] if isinstance(address, tuple) else address
        if host not in LOCAL_HOSTS:
            raise ConnectionRefusedError(f"Red bloqueada en e2e: {host}")
        return connect(sock, address)

    monkeypatch.setattr(socket.socket, "connect", local_only)


@pytest.fixture
def datos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Portafolio, EVA-04 y oportunidades de prueba; lo demas queda sin red."""
    from django.core.cache import cache

    from apps.portal.services import eva4, executive_refresh
    from apps.portal.services import opportunity_profitability as opp
    from apps.portal.services.eva1 import build_eva1_view
    from apps.portal.services.eva_loader import Eva1Load
    from apps.portal.services.facturability_loader import MonthSources
    from tests.portal import test_eva4
    from tests.portal.test_opportunity_profitability import reader
    from tests.portal.test_views import portfolio, stub_portfolio

    cache.clear()
    monkeypatch.setattr(
        "apps.portal.views.load_eva1",
        lambda *a, **k: Eva1Load(view=build_eva1_view([]), error=""),
    )
    stub_portfolio(monkeypatch, portfolio())
    sheet = [test_eva4.HEADER, test_eva4.row(), test_eva4.row("2")]
    data = eva4.build_eva4(sheet, test_eva4.TODAY)
    data["month"] = "2026-10"
    monkeypatch.setattr(eva4, "load_eva4", lambda *a: data)
    monkeypatch.setattr(eva4.timezone, "localdate", lambda: test_eva4.TODAY)
    monkeypatch.setattr(executive_refresh, "request_refresh", lambda **k: None)
    monkeypatch.setattr(
        "apps.portal.services.operational_sources.legacy_capacity",
        lambda month: {
            "month": month,
            "available": 96.0,
            "registered_people": 4,
            "estimated": 100.0,
            "consumed": 64.0,
            "billable": 64.0,
            "base": 160.0,
            "days": 20,
            "over": 1,
            "pending": 0,
        },
    )
    monkeypatch.setattr(
        "apps.portal.views.load_year_sources",
        lambda month: [MonthSources(month=month)],
    )
    monkeypatch.setattr(
        "apps.portal.services.account_options.load_account_profitability",
        lambda: {"accounts": [{"name": "ACME"}, {"name": "Clinica Sur"}]},
    )
    sale = ["Confirmed", "Clinica Sur", "OP.7", "T&M", "2", 0, "2026-03-01"]
    monkeypatch.setattr(
        opp,
        "build_sheet_repository",
        lambda: reader(
            [*sale, 1000, "40%"],
            [
                "Confirmed",
                "ACME",
                "OP.9",
                "RaaS",
                "1",
                0,
                "2026-03-01",
                500,
                "55%",
            ],
        ),
    )


@pytest.fixture
def portal(live_server: Any, page: Any) -> Iterator[Any]:
    """Pagina del navegador limitada al servidor de pruebas."""
    origin = live_server.url

    def only_local(route: Any) -> None:
        if route.request.url.startswith(origin):
            route.continue_()
        else:
            route.abort()

    page.route("**/*", only_local)
    page.set_default_timeout(15000)
    page.base = origin
    yield page


@pytest.fixture
def enforced_csp(portal: Any, settings: Any) -> Iterator[None]:
    """Apply the proposed policy to local HTML only in this test browser."""
    settings.CSP_REPORT_ONLY = True

    def enforce(route: Any) -> None:
        if (
            not route.request.url.startswith(portal.base)
            or route.request.resource_type != "document"
        ):
            route.fallback()
            return
        response = route.fetch()
        headers = dict(response.headers)
        policy = headers.pop("content-security-policy-report-only", None)
        if policy:
            headers["content-security-policy"] = policy
        route.fulfill(response=response, headers=headers)

    portal.route("**/*", enforce)
    yield
    portal.unroute("**/*", enforce)


def watch(portal):
    """Anota lo que sale mal en la pagina; las fuentes de Google se ignoran."""
    problems = []
    portal.on(
        "console",
        lambda m: (
            problems.append(m.text)
            if m.text.startswith("[Report Only]")
            or "Content Security" in m.text
            else None
        ),
    )
    portal.on("pageerror", lambda e: problems.append(str(e)))
    portal.on(
        "requestfailed",
        lambda r: problems.append(r.url) if portal.base in r.url else None,
    )
    return problems


@pytest.fixture(autouse=True)
def _previous_project_detail(reference_site: None) -> None:
    """Las comparaciones usan la referencia anterior que viven en pruebas."""


@pytest.fixture(autouse=True)
def _csp_everywhere(request: pytest.FixtureRequest) -> Iterator[None]:
    """E2E_CSP=1: toda la suite con la politica aplicada y avisos en un archivo.

    Sirve para auditar la CSP: cada aviso del navegador queda en
    tmp/csp-violations.log con la prueba que lo provoco.
    """
    if os.environ.get("E2E_CSP") != "1" or "portal" not in request.fixturenames:
        yield
        return
    request.getfixturevalue("enforced_csp")
    page = request.getfixturevalue("portal")
    log = Path("tmp/csp-violations.log")
    log.parent.mkdir(exist_ok=True)

    def note(message: Any) -> None:
        if "Content Security" in message.text:
            with log.open("a", encoding="utf-8") as handle:
                line = (
                    f"{request.node.nodeid}\t{page.url}\t{message.text[:200]}"
                )
                handle.write(line.replace("\n", " ") + "\n")

    page.on("console", note)
    yield
