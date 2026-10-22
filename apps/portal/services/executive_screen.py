"""Business Overview: el corte preparado, recortado al alcance de la persona."""

from typing import Any

from apps.access.scope import AccessScope
from apps.portal.services.slugs import build_slug

"""BKD.120.024 - Business Overview
Las cifras de empresa (facturacion, costos, operaciones, comercial y
rentabilidad mensual) son del portafolio completo: con alcance limitado no se
entregan. El listado de cuentas si, recortado a las cuentas permitidas.
"""


def visible_accounts(
    financial: dict[str, Any], scope: AccessScope
) -> list[dict[str, Any]] | None:
    """Cuentas del corte que la persona puede ver; None si no hay listado."""
    rows = financial.get("accounts", {}).get("accounts")
    if rows is None:
        return None
    return [
        {
            "name": row["name"],
            "slug": build_slug(row["name"]) or "cuenta",
            "revenue": row.get("revenue"),
            "gross_profit": row.get("gross_profit"),
            "margin": row.get("margin"),
            "projects": row.get("projects", 0),
            "partial": bool(row.get("pending") or row.get("partial")),
        }
        for row in rows
        if scope.allows_account(row["name"])
    ]


def company_figures(
    financial: dict[str, Any], operations: dict[str, Any], scope: AccessScope
) -> dict[str, Any]:
    """Cifras del portafolio completo; vacias si el alcance es limitado."""
    if not scope.unrestricted:
        return {
            "finance": None,
            "operations": None,
            "commercial": None,
            "monthly": None,
        }
    return {
        "finance": {
            "revenue": financial.get("revenue"),
            "costs": financial.get("costs"),
        }
        if financial.get("revenue") or financial.get("costs")
        else None,
        "operations": operations or None,
        "commercial": financial.get("commercial"),
        "monthly": financial.get("profitability"),
    }


def scoped_snapshots(
    financial: dict[str, Any], operations: dict[str, Any], scope: AccessScope
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Los cortes que la pagina incrusta, solo con lo que el alcance permite.

    Con alcance total salen completos menos el detalle de oportunidades (la
    pagina no lo usa). Con alcance limitado no sale ninguna cifra de empresa y
    el listado de cuentas se recorta a las permitidas.
    """
    if scope.unrestricted:
        return {k: v for k, v in financial.items() if k != "opportunities"}, (
            operations
        )
    rows = financial.get("accounts", {}).get("accounts")
    visible = None
    if rows is not None:
        visible = [row for row in rows if scope.allows_account(row["name"])]
    limited: dict[str, Any] = {}
    if financial.get("loaded_at"):
        limited["loaded_at"] = financial["loaded_at"]
    if visible is not None:
        limited["accounts"] = {
            "accounts": visible,
            "pending_accounts": sum(bool(r.get("pending")) for r in visible),
            "ranking_version": 4,
        }
    return limited, {}
