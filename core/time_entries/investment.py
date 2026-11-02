"""Clasificación de inversión exclusivamente por etiquetas de Clockify."""

from collections.abc import Iterable

INVESTMENT_TAGS = {
    "INV_OPERATIVA": "operational",
    "INV_COMERCIAL": "commercial",
}


def investment_categories(tags: Iterable[str]) -> tuple[str, ...]:
    """Clasifica etiquetas exactas, ignorando mayúsculas y espacios externos."""
    normalized = {str(tag).strip().upper() for tag in tags}
    return tuple(
        category
        for tag, category in INVESTMENT_TAGS.items()
        if tag in normalized
    )
