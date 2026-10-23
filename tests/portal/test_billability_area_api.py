"""El transporte HTTP mantiene parámetros, permisos y servicios de GSE."""

from unittest.mock import Mock

import pytest
from django.test import Client

from apps.access.scope import AccessScope

pytestmark = pytest.mark.django_db
BASE = "/api/v1/screens/facturabilidad/area/"


@pytest.mark.parametrize(
    ("path", "query", "service", "args"),
    [
        ("areas/", {}, "get_gse_areas", ()),
        (
            "mes/",
            {
                "mes": "2026-02",
                "area": "DEV",
                "fuente": "api",
                "actualizar": "1",
            },
            "get_gse_month",
            ("2026-02", "api", True, "DEV"),
        ),
        (
            "lote/",
            {
                "anio": "2026",
                "area": "QA",
                "cursor": "200",
                "total": "600",
                "actualizar": "1",
            },
            "get_gse_batch",
            (2026, "QA", 200, 600, True),
        ),
        (
            "cache/",
            {"anio": "2026", "area": "QA"},
            "read_gse_result_cache",
            (2026, "QA", False),
        ),
    ],
)
def test_reads_keep_original_fields(
    client, monkeypatch, path, query, service, args
):
    source = Mock(
        return_value={"ok": True, "pending": True, "records": [{"horas": 8.5}]}
    )
    monkeypatch.setattr("apps.gse.rpc." + service, source)
    response = client.get(BASE + path, query)
    assert response.status_code == 200
    assert response.json()["data"] == source.return_value
    source.assert_called_once_with(*args)


@pytest.mark.parametrize(
    ("path", "body", "service", "args"),
    [
        (
            "cache/",
            {"anio": 2026, "area": "DEV", "borrar": True},
            "read_gse_result_cache",
            (2026, "DEV", True),
        ),
        (
            "cache/",
            {
                "anio": 2026,
                "area": "DEV",
                "resultado": {"data": {}, "bandas": [], "total": 0},
            },
            "save_gse_result_cache",
            (2026, "DEV", {"data": {}, "bandas": [], "total": 0}),
        ),
        (
            "ids/",
            {"mes": "2026-02", "solo_reporte": True},
            "get_gse_clockify_ids",
            ("2026-02", True),
        ),
    ],
)
def test_posts_keep_the_same_services(
    client, monkeypatch, path, body, service, args
):
    source = Mock(return_value={"ok": True, "guardados": 2})
    monkeypatch.setattr("apps.gse.rpc." + service, source)
    response = client.post(BASE + path, body, content_type="application/json")
    assert response.status_code == 200
    assert response.json()["data"] == source.return_value
    source.assert_called_once_with(*args)


@pytest.mark.parametrize("grant", ["anonymous", "limited", "wrong"])
@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "areas/"),
        ("get", "mes/"),
        ("get", "lote/"),
        ("get", "cache/"),
        ("post", "cache/"),
        ("post", "ids/"),
    ],
)
def test_rejects_before_reading_sources(
    client, enforced, monkeypatch, grant, method, path
):
    sources = []
    for name in [
        "get_gse_areas",
        "get_gse_month",
        "get_gse_batch",
        "read_gse_result_cache",
        "save_gse_result_cache",
        "get_gse_clockify_ids",
    ]:
        source = Mock(side_effect=AssertionError("Source read"))
        monkeypatch.setattr("apps.gse.rpc." + name, source)
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
    "query",
    [
        {},
        {"anio": "2026.5"},
        {"anio": "1999"},
        {"anio": "2026", "cursor": "-1"},
        {"anio": "2026", "total": "nan"},
    ],
)
def test_invalid_batch_does_not_load(client, monkeypatch, query):
    source = Mock(side_effect=AssertionError("Source read"))
    monkeypatch.setattr("apps.gse.rpc.get_gse_batch", source)
    assert client.get(BASE + "lote/", query).status_code == 400
    source.assert_not_called()


@pytest.mark.parametrize(
    "query", [{"mes": "2026-13"}, {"mes": "2026-02", "fuente": "other"}]
)
def test_invalid_month_or_source(client, monkeypatch, query):
    source = Mock(side_effect=AssertionError("Source read"))
    monkeypatch.setattr("apps.gse.rpc.get_gse_month", source)
    assert client.get(BASE + "mes/", query).status_code == 400
    source.assert_not_called()


def test_ids_get_cannot_write(client, monkeypatch):
    source = Mock(side_effect=AssertionError("Write"))
    monkeypatch.setattr("apps.gse.rpc.get_gse_clockify_ids", source)
    assert client.get(BASE + "ids/", {"mes": "2026-02"}).status_code == 405
    source.assert_not_called()


@pytest.mark.parametrize("path", ["cache/", "ids/"])
def test_post_requires_csrf_even_when_access_is_disabled(path):
    response = Client(enforce_csrf_checks=True).post(
        BASE + path,
        {"anio": 2026, "mes": "2026-02"},
        content_type="application/json",
    )
    assert response.status_code == 403


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("cache/", []),
        ("ids/", []),
        ("cache/", {"anio": 2026, "area": [], "borrar": True}),
        ("cache/", {"anio": 2026, "borrar": "true"}),
        ("cache/", {"anio": 2026, "resultado": []}),
        ("ids/", {"mes": "2026-02", "solo_reporte": "false"}),
    ],
)
def test_invalid_post_is_a_validation_error(client, path, payload):
    assert (
        client.post(
            BASE + path, payload, content_type="application/json"
        ).status_code
        == 400
    )
