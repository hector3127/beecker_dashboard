"""Los endpoints EVA conservan formato, servicios y alcance de portafolio."""

from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope
from apps.portal.services.eva2 import build_eva2_view
from tests.portal.test_eva2 import make_row

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/"
READS = [
    ("eva-3/cerrados/", "eva3_closed_data"),
]


@pytest.mark.parametrize("path,loader", READS)
def test_closed_data_preserves_project_and_django_format(
    client, monkeypatch, path, loader
):
    project = build_eva2_view([make_row(budget=1234.5)]).projects[0]
    monkeypatch.setattr(
        "apps.portal.views." + loader,
        lambda: {
            "projects": [project],
            "error": "",
            "historic_rows": [
                {
                    "idProyecto": project.project_id,
                    "estadoHistorico": "Completed",
                }
            ],
        },
    )
    response = client.get(BASE + path)
    assert response.status_code == 200
    result = response.json()["data"]["projects"][0]
    assert result["display"]["budget"] == "1,234.50"
    assert result["display"]["burn"] == "167.59"
    assert result["display"]["progress"] == "118.8"
    assert result["closed_status"] == "Completed"
    assert result["project_id"] == project.project_id
    assert result["url"] == "/proyectos/AMK.008_S4/"


@pytest.mark.parametrize("path,loader", READS)
def test_source_error_remains_a_readable_empty_result(
    client, monkeypatch, path, loader
):
    monkeypatch.setattr(
        "apps.portal.views." + loader,
        lambda: {"projects": [], "error": "MPB no disponible"},
    )
    response = client.get(BASE + path)
    assert response.json()["data"] == {
        "projects": [],
        "error": "MPB no disponible",
    }


def test_consumption_reuses_original_service(client, monkeypatch):
    service = Mock(
        return_value={"ok": True, "items": [{"id": "AER.1", "burn": 12.5}]}
    )
    monkeypatch.setattr("apps.portal.api.eva.get_aer_tym_consumption", service)
    response = client.post(
        BASE + "eva-3/consumos/",
        {"proyectos": ["AER.1", "TYM.2"]},
        content_type="application/json",
    )
    assert response.status_code == 200
    assert response.json()["data"] == service.return_value
    service.assert_called_once_with(["AER.1", "TYM.2"])


def test_closed_burn_keeps_service_and_error(client, monkeypatch):
    service = Mock(return_value={"burn": 60.25})
    monkeypatch.setattr("apps.portal.api.eva.fill_closed_burn", service)
    path = BASE + "eva-3/cerrados/consumo/"
    response = client.post(
        path, {"id": "AER.1"}, content_type="application/json"
    )
    assert response.json()["data"] == {"burn": 60.25}
    service.assert_called_once_with("AER.1")
    service.side_effect = ValueError("No se pudo guardar MPB")
    response = client.post(
        path, {"id": "AER.1"}, content_type="application/json"
    )
    assert response.status_code == 502
    assert response.json()["error"]["message"] == "No se pudo guardar MPB"


@pytest.mark.parametrize("grant", ["anonymous", "limited", "wrong"])
@pytest.mark.parametrize(
    "path,method",
    [
        ("eva-3/cerrados/", "get"),
        ("eva-3/consumos/", "post"),
        ("eva-3/cerrados/consumo/", "post"),
    ],
)
def test_access_is_checked_before_sources(
    client, enforced, monkeypatch, grant, path, method
):
    sources = []
    for name in [
        "apps.portal.views.eva3_closed_data",
        "apps.portal.api.eva.get_aer_tym_consumption",
        "apps.portal.api.eva.fill_closed_burn",
    ]:
        source = Mock(side_effect=AssertionError("Source read"))
        monkeypatch.setattr(name, source)
        sources.append(source)
    enforced(
        "Ana",
        caps=frozenset(
            {"view_costs"} if grant == "wrong" else {"view_operations"}
        ),
        scope=AccessScope.limited(accounts=["Acme"])
        if grant == "limited"
        else AccessScope.everything(),
    )
    if grant == "anonymous":
        client.logout()
    response = getattr(client, method)(BASE + path)
    assert response.status_code in {401, 403}
    for source in sources:
        source.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"proyectos": []},
        {"proyectos": ["A", "B", "C"]},
        {"proyectos": [None]},
        {"proyectos": [" "]},
    ],
)
def test_invalid_consumption_payload_does_not_read(
    client, monkeypatch, payload
):
    source = Mock(side_effect=AssertionError("Source read"))
    monkeypatch.setattr("apps.portal.api.eva.get_aer_tym_consumption", source)
    assert (
        client.post(
            BASE + "eva-3/consumos/", payload, content_type="application/json"
        ).status_code
        == 400
    )
    source.assert_not_called()


@pytest.mark.parametrize("path", ["eva-3/consumos/", "eva-3/cerrados/consumo/"])
def test_post_requires_csrf_and_get_cannot_change_burn(client, path):
    assert client.get(BASE + path).status_code == 405
    response = Client(enforce_csrf_checks=True).post(
        BASE + path,
        {"id": "AER.1", "proyectos": ["AER.1"]},
        content_type="application/json",
    )
    assert response.status_code == 403


@pytest.mark.parametrize("screen", [1, 2, 3])
def test_active_pages_use_modular_templates(client, monkeypatch, screen):
    empty = build_eva2_view([])
    if screen == 3:
        from apps.portal.services.eva1 import build_eva1_view

        empty = build_eva1_view([])
    monkeypatch.setattr(
        f"apps.portal.views.eva{2 if screen < 3 else 3}_data",
        lambda: {"eva": empty, "error": ""},
    )
    response = client.get(f"/operativa/eva-{screen}/")
    assert response.status_code == 200
    assert f"pages/eva{screen}.html" in [t.name for t in response.templates]
    html = response.content.decode()
    assert f"app/scripts/pages/eva{screen}/main.js" in html
    assert "onclick=" not in html
