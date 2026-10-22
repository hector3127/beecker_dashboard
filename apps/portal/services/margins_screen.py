"""Comparativa de margenes: oportunidades visibles para una persona."""

from typing import Any

from django.core.cache import cache

from apps.access.scope import AccessScope
from apps.ejecutivo.services.account_view import account_matches
from apps.portal.services.opportunity_profitability import (
    OPPORTUNITY_VERSION,
    build_opportunities,
    opportunity_summary,
)

"""BKD.120.021 - Comparativa de margenes
Usa el corte guardado cuando esta vigente; si no, calcula con lo disponible y
pide preparar los costos. Solo entrega las cuentas del alcance de la persona.
"""


def load_margins(account: str, scope: AccessScope) -> dict[str, Any]:
    """Oportunidades del periodo activo, filtradas por cuenta y alcance."""
    from apps.portal.services.executive_refresh import request_refresh
    from apps.portal.services.financial_cache import (
        cached_financial_snapshot,
        snapshot_key,
    )

    snapshot = cached_financial_snapshot()
    prepared = snapshot.get("opportunities") or cache.get(
        snapshot_key() + ":opportunities"
    )
    if prepared and prepared.get("version") != OPPORTUNITY_VERSION:
        prepared = None
    data = prepared or build_opportunities()
    rows = [
        row
        for row in data["opportunities"]
        if scope.allows_account(row["account"])
        and (not account or account_matches(row["account"], account))
    ]
    if not prepared:
        request_refresh()
    return {
        "opportunities": rows,
        "summary": opportunity_summary(rows),
        "start": data["start"],
        "end": data["end"],
        "excluded": data.get("excluded", ""),
        "preparing": not prepared,
    }
