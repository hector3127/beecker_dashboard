"""Identificadores para usar nombres en las direcciones web."""

import re
import unicodedata

"""BKD.120.012 - Slugs del portal
Convierte el nombre de un Delivery Manager en un texto seguro para la URL
(sin acentos ni espacios): "Patricio Ochoa" -> "patricio-ochoa".
"""

EMPTY_SLUG = "sin-nombre"


def build_slug(name: str) -> str:
    """
    Convierte un nombre en un slug.

    Args:
        name: Nombre original, con acentos y espacios.

    Returns:
        El slug en minusculas; "sin-nombre" cuando no queda ningun caracter.
    """
    ascii_name = (
        unicodedata.normalize("NFKD", name)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")

    return slug or EMPTY_SLUG
