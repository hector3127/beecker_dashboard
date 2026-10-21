"""Account identities shared by global and account-level agreements."""

from core.utils.text import normalize_name


def agreement_account_key(name: str) -> str:
    """Match the account aliases used by the imported account view."""
    normalized = normalize_name(name)
    return {
        "heineken mexico": "heineken",
        "cadena comercial oxxo": "oxxo",
        "cadena comercial oxxo.": "oxxo",
    }.get(normalized, normalized)
