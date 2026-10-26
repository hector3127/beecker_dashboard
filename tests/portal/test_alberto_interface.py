"""Executive controls and rate provenance requested in the review."""

from django.template.loader import render_to_string

from apps.portal.services.data_dictionary import CONCEPTS, glossary_groups


def test_executive_exposes_glossary_and_ordering_in_the_main_view():
    html = render_to_string(
        "pages/executive.html",
        {"glossary": glossary_groups(), "executive_year": 2026},
    )
    assert "¿Qué significa cada indicador?" in html
    assert 'id="ranking-search"' in html
    assert 'id="ranking-sort"' in html
    assert html.count('data-ranking-column="revenue"') == 2
    assert html.count('data-ranking-column="gross_profit"') == 2
    assert html.count('data-ranking-column="margin"') == 2
    assert "70% utilidad" not in html


def test_glossary_distinguishes_sold_rate_and_internal_band_rate():
    concepts = {name: definition for name, definition, _source in CONCEPTS}
    assert "costing rate" in " ".join(concepts)
    assert "Florencia" in concepts["Tarifa de costo vendida (costing rate)"]
    assert "No equivale" in concepts["Tarifa interna de banda"]
    assert "sin ponderación 70/30" in concepts["Comparación de cuentas"]
