"""El glosario de Business Overview sale del diccionario de datos.

Cada termino nombra el concepto de CONCEPTS que lo define; si el concepto
se renombra o desaparece, esta prueba lo avisa antes de que el glosario
quede huerfano.
"""

import pytest

from apps.portal.services.data_dictionary import (
    CONCEPTS,
    GLOSSARY,
    glossary_groups,
)


@pytest.fixture(autouse=True)
def no_background_refresh(monkeypatch):
    monkeypatch.setattr(
        "apps.portal.services.executive_refresh.request_refresh",
        lambda **kwargs: None,
    )


def test_every_term_points_to_an_existing_concept():
    names = {name for name, _definition, _source in CONCEPTS}

    missing = [
        (term, concept)
        for _group, terms in GLOSSARY
        for term, concept, _summary in terms
        if concept not in names
    ]

    assert not missing, missing


def test_groups_come_in_the_published_order_without_empty_terms():
    groups = glossary_groups()

    assert [g["name"] for g in groups] == [
        "Finanzas",
        "Operaciones",
        "Comercial",
    ]
    for group in groups:
        for item in group["terms"]:
            assert item["summary"].strip()


def test_executive_links_to_one_glossary_without_repeated_inline_glossaries(
    client,
):
    html = client.get("/").content.decode()
    assert "Glosario de indicadores" in html
    assert 'href="/diccionario-datos/"' in html
    assert 'class="executive-glossary' not in html
    assert 'id="executive-prepare"' not in html


def test_the_glossary_api_serves_concepts_and_groups(client):
    body = client.get("/api/v1/reference/glossary/").json()

    assert body["meta"]["definitions_date"] == "2026-11-17"
    names = {c["name"] for c in body["data"]["concepts"]}
    assert len(body["data"]["concepts"]) == len(CONCEPTS)
    for group in body["data"]["groups"]:
        for item in group["terms"]:
            assert item["concept"] in names
