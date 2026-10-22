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


def test_opportunity_rate_is_explicitly_pending_without_changing_margins():
    html = render_to_string(
        "portal/oportunidades_financieras.html",
        {
            "data": {
                "opportunities": [
                    {
                        "account": "ACME",
                        "name": "Venta",
                        "ids": [],
                        "projects": [],
                        "services": [],
                        "sold_margin": 25,
                        "actual_margin": 20,
                        "deviation_pp": -5,
                    }
                ]
            },
            "summary": {},
        },
    )
    assert "Tarifa de costo vendida" in html
    assert "Por validar con Florencia" in html
    assert 'colspan="11"' in html
    for heading in (
        "Bookings",
        "Revenue operado",
        "Cobrado",
        "Costos",
        "Margen real",
    ):
        assert f"<th>{heading}</th>" in html
    assert "Fecha de servicio: G · por validar" in html
    assert "Margen consumido" not in html
    assert "No se sustituye por la tarifa interna de banda" in html
    assert "25,00%" in html or "25.00%" in html


def test_glossary_distinguishes_sold_rate_and_internal_band_rate():
    concepts = {name: definition for name, definition, _source in CONCEPTS}
    assert "costing rate" in " ".join(concepts)
    assert "Florencia" in concepts["Tarifa de costo vendida (costing rate)"]
    assert "No equivale" in concepts["Tarifa interna de banda"]
    assert "sin ponderación 70/30" in concepts["Comparación de cuentas"]
