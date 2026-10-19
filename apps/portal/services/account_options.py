"""Account navigation shares the complete financial account catalogue."""

from collections.abc import Sequence

from django.core.cache import cache
from django.utils import timezone

from apps.portal.services.account_profitability import (
    load_account_profitability,
)
from core.exceptions import DashboardError
from core.utils.text import normalize_name


def account_names(fallback: Sequence[str] = ()) -> list[str]:
    """Reuse financial accounts without querying Clockify on navigation."""
    key = "portal:account-options:v1:" + timezone.localdate().isoformat()
    saved: list[str] | None = cache.get(key)
    if saved is not None:
        return saved
    try:
        data = load_account_profitability()
    except (DashboardError, ValueError):
        return list(fallback)
    names: dict[str, str] = {}
    for account in data["accounts"]:
        name = account["name"]
        names.setdefault(normalize_name(name), name)
    result = sorted(names.values(), key=normalize_name)
    cache.set(key, result, 300)
    return result
