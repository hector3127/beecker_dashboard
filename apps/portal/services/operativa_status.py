"""Estado de un bloque de Operativa: llego completo o no."""

from typing import Any


def block_error(context: dict[str, Any]) -> str:
    """Motivo por el que el bloque pedido no llego completo ('' si llego)."""
    if context.get("block_error"):
        return str(context["block_error"])
    refreshed = context.get("refresh_block")
    if refreshed == "inversion":
        return str((context.get("investment") or {}).get("error") or "")
    if refreshed == "capacidad":
        return str((context.get("capacity_live") or {}).get("error") or "")
    if refreshed == "eva3" and not context["eva3_card"].available:
        return "EVA 3 no disponible"
    return ""
