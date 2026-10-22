"""Cada término del glosario de Business Overview tiene su definición completa.

Hoy el glosario está escrito a mano y repite lo que dice el diccionario de
datos. Esta prueba obliga a que cada término nuevo declare de qué concepto
del diccionario sale, para que las dos definiciones no se separen sin que
alguien lo vea. Cuando el glosario se genere desde CONCEPTS (fase 8) esta
correspondencia desaparece.
"""

import re
from pathlib import Path

from apps.portal.services.data_dictionary import CONCEPTS

GLOSSARY = Path("apps/portal/templates/portal/_executive_glossary.html")

# término del glosario -> conceptos del diccionario que lo definen
SOURCES = {
    "Facturación": ["Facturación"],
    "Utilidad y margen bruto": ["Utilidad bruta", "Margen bruto"],
    "Cobranza": ["Cobranza"],
    "ETC · horas restantes": ["ETC"],
    "Avance en horas": ["Avance en horas"],
    "Facturabilidad": ["Facturabilidad global"],
    "Inversión operativa": ["Inversión operativa"],
    "Ventas cerradas · booking": ["Booking / ventas cerradas"],
    "Trabajo por entregar": ["Trabajo por entregar"],
    "Previas al cierre": ["Previas al cierre"],
}


def glossary_terms():
    return re.findall(r"<dt>(.*?)</dt>", GLOSSARY.read_text(encoding="utf-8"))


def test_every_glossary_term_declares_its_dictionary_concept():
    assert sorted(glossary_terms()) == sorted(SOURCES)


def test_the_declared_concepts_exist_in_the_dictionary():
    names = {name for name, _definition, _source in CONCEPTS}

    for term, concepts in SOURCES.items():
        missing = [name for name in concepts if name not in names]
        assert not missing, (term, missing)


def test_pending_items_are_never_described_as_zero():
    html = GLOSSARY.read_text(encoding="utf-8")

    assert "no equivale a cero" in html
