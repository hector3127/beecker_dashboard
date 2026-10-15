"""Prepara Finanzas sin consultar Clockify al renderizar la pagina."""

import logging
import threading
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from apps.portal.services.account_profitability import account_profitability
from apps.portal.services.monthly_profitability import (
    load_monthly_profitability,
)
from apps.portal.services.revenue import load_revenue
from apps.portal.services.revenue_costs import (
    calculate_project_cost,
    cost_summary,
    key,
    prepare_cost_context,
    project_ids,
)
from core.exceptions import DashboardError
from core.sheets.factory import build_sheet_repository
from core.utils.parallel import map_in_parallel

logger = logging.getLogger(__name__)
_WARM_LOCK = threading.Lock()


def snapshot_key() -> str:
    """Separa el corte financiero de los otros bloques y de otros dias."""
    return "portal:financial:snapshot:v2:" + timezone.localdate().isoformat()


def cached_financial_snapshot() -> dict[str, Any]:
    """Lee el corte preparado sin llamadas a fuentes externas."""
    return cache.get(snapshot_key()) or {}


def warm_financial(only_stale: bool = False) -> dict[str, Any]:
    """Agrupa actualizaciones simultaneas sin ocultar el ultimo corte."""
    with _WARM_LOCK:
        if only_stale and cache.get(snapshot_key() + ":fresh"):
            return {"ok": True, "error": ""}
        return _prepare_financial()


def _prepare_financial() -> dict[str, Any]:
    """Prepara ingresos, costos y rentabilidad con dos consultas simultaneas."""
    failures: list[str] = []
    try:
        revenue = load_revenue()
        reader = build_sheet_repository()
        ids = project_ids(reader)
        context = prepare_cost_context(reader=reader, ids=ids)
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
        error for error in map_in_parallel(prepare, ids, max_workers=2) if error
    )
    costs = cost_summary(ids=ids)
    profitability = load_monthly_profitability(reader=context.reader, ids=ids)
    if not profitability["complete"] and not failures:
        failures.append("Rentabilidad mensual incompleta")
    snapshot = {
        "revenue": revenue,
        "costs": costs,
        "profitability": profitability,
        "accounts": account_profitability(reader=context.reader),
        "loaded_at": timezone.localtime().isoformat(),
    }
    # Un corte parcial es explicito; nunca reemplaza uno completo vigente.
    previous = cached_financial_snapshot()
    if not failures or not previous.get("costs", {}).get("complete"):
        cache.set(snapshot_key(), snapshot, 86400)
        cache.set(snapshot_key() + ":fresh", True, 300)
    return {"ok": not failures, "error": "; ".join(failures)}
