"""Executive controls and rate provenance requested in the review."""

from apps.portal.services.data_dictionary import CONCEPTS


def test_glossary_distinguishes_sold_rate_and_internal_band_rate():
    concepts = {name: definition for name, definition, _source in CONCEPTS}
    assert "costing rate" in " ".join(concepts)
    assert "Florencia" in concepts["Tarifa de costo vendida (costing rate)"]
    assert "No equivale" in concepts["Tarifa interna de banda"]
    assert "sin ponderación 70/30" in concepts["Comparación de cuentas"]
