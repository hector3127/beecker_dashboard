"""Prepara Finanzas sin consultar Clockify al renderizar la pagina."""

import logging
import threading
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.portal.services.account_profitability import account_profitability
from apps.portal.services.executive_period import cache_suffix
from apps.portal.services.monthly_profitability import (
    load_monthly_profitability,
)
from apps.portal.services.revenue import load_revenue
from apps.portal.services.revenue_costs import (
    calculate_project_cost,
    cost_summary,
    future_project_month,
    key,
    prepare_cost_context,
    project_ids,
)
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.utils.parallel import map_in_parallel
from core.utils.source_refresh import force_sources

logger = logging.getLogger(__name__)
_WARM_LOCK = threading.Lock()


def snapshot_key() -> str:
    """Separa el corte financiero de los otros bloques y de otros dias."""
    return (
        "portal:financial:snapshot:v13:"
        + timezone.localdate().isoformat()
        + cache_suffix()
    )


def cached_financial_snapshot() -> dict[str, Any]:
    """Lee el corte preparado sin llamadas a fuentes externas."""
    saved = cache.get(snapshot_key()) or {}
    if (
        saved.get("accounts", {}).get("accounts") is not None
        and saved["accounts"].get("ranking_version") != 4
    ):
        from apps.portal.services.account_profitability import (
            rank_financial_accounts,
        )

        saved = {
            **saved,
            "accounts": rank_financial_accounts(saved["accounts"]["accounts"]),
        }
    return saved


def warm_financial(only_stale: bool = False) -> dict[str, Any]:
    """Agrupa actualizaciones simultaneas sin ocultar el ultimo corte."""
    with _WARM_LOCK:
        if (
            only_stale
            and cache.get(snapshot_key() + ":fresh")
            and (
                cached_financial_snapshot().get("opportunities")
                or cache.get(snapshot_key() + ":opportunities")
                or {}
            ).get("version")
            == 5
        ):
            return {"ok": True, "error": ""}
        return _prepare_financial()


def _prepare_financial() -> dict[str, Any]:
    """Prepara ingresos, costos y rentabilidad con dos consultas simultaneas."""
    failures: list[str] = []
    try:
        revenue = load_revenue()
        reader = build_sheet_repository()
        ids = project_ids(reader)

        # Do not re-read/parse rosters and rates for already prepared costs.
        def needs_preparation(pid: Any) -> Any:
            if future_project_month(pid):
                return False
            saved = cache.get(key(pid))
            return (
                force_sources.get()
                or not saved
                or saved.get("financial_grouping_version") != 3
                or "sprints" not in saved
                or any("people" not in group for group in saved["sprints"])
            )

        pending = [pid for pid in ids if needs_preparation(pid)]
        context = (
            prepare_cost_context(reader=reader, ids=ids) if pending else None
        )
        logger.info(
            "Financiera: %s costos reutilizados, %s pendientes",
            len(ids) - len(pending),
            len(pending),
        )
    except (DashboardError, ValueError) as error:
        return {"ok": False, "error": str(error)}

    def prepare(pid: str) -> str:
        """Guarda el costo o el error de cada ID de DataRevenue."""
        try:
            result = calculate_project_cost(pid, context=context)
        except (DashboardError, ValueError) as error:
            message = str(error)
            cache.set(key(pid) + ":error", message, 300)
            logger.warning("Financiera %s: %s", pid, message)
            return pid + ": " + message
        if not result["complete"]:
            return pid + ": falta banda o tarifa"
        return ""

    failures.extend(
        error
        for error in map_in_parallel(prepare, pending, max_workers=2)
        if error
    )
    costs = cost_summary(ids=ids)
    if not costs["complete"] and not failures:
        failures.append("Costos incompletos")
    profitability = load_monthly_profitability(reader=reader, ids=ids)
    if not profitability["complete"] and not failures:
        failures.append("Rentabilidad mensual incompleta")
    from apps.portal.services.opportunity_profitability import (
        build_opportunities,
    )

    opportunities = build_opportunities(reader)
    snapshot = {
        "revenue": revenue,
        "costs": costs,
        "profitability": profitability,
        "accounts": account_profitability(reader=reader),
        "opportunities": opportunities,
        "loaded_at": timezone.localtime().isoformat(),
        "query_errors": failures,
    }
    # Un corte parcial es explicito; nunca reemplaza uno completo vigente.
    previous = cached_financial_snapshot()
    if not failures or not previous.get("costs", {}).get("complete"):
        cache.set(snapshot_key(), snapshot, 86400)
        cache.set(snapshot_key() + ":fresh", True, 300)
    if opportunities:
        cache.set(snapshot_key() + ":opportunities", opportunities, 86400)
    return {"ok": not failures, "error": "; ".join(failures)}
