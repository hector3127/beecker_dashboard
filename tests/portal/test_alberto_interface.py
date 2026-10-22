"""Executive controls and rate provenance requested in the review."""

from django.template.loader import render_to_string

from apps.portal.services.data_dictionary import CONCEPTS


def test_executive_exposes_glossary_and_ordering_in_the_main_view():
    html = render_to_string(
        "portal/ejecutiva.html",
        {
            "financial_snapshot": {},
            "operations_snapshot": {},
        },
    )
    assert "¿Qué significa cada indicador?" in html
    assert 'id="ranking-search"' in html
    assert 'id="ranking-sort"' in html
    assert html.count('data-sort-key="revenue"') == 2
    assert html.count('data-sort-key="gross_profit"') == 2
    assert html.count('data-sort-key="margin"') == 2
    assert "70% utilidad" not in html


def test_glossary_distinguishes_sold_rate_and_internal_band_rate():
    concepts = {name: definition for name, definition, _source in CONCEPTS}
    assert "costing rate" in " ".join(concepts)
    assert "Florencia" in concepts["Tarifa de costo vendida (costing rate)"]
    assert "No equivale" in concepts["Tarifa interna de banda"]
    assert "sin ponderación 70/30" in concepts["Comparación de cuentas"]
