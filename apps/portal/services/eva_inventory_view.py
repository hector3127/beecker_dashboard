"""Inventory logic adapted to the approved EVA presentation contract."""

from datetime import date
from typing import Any

from django.conf import settings

from apps.portal.services.eva2 import build_eva2_view
from apps.portal.services.eva_monthly_closes import is_closed_period
from apps.portal.services.summary_inventory import inventory_rows


def load_inventory_eva(cut: date) -> dict[str, Any]:
    """Use exactly the inventory range and historical provider data in EVA."""
    run, rows = inventory_rows(cut=cut)
    state = ("fixed" if run else "pending") if is_closed_period(cut) else "live"
    if not settings.EVA_MONTHLY_CLOSES_ENABLED:
        state = "disabled"
    projected = []
    for row in rows:
        fields = row.get("fields") or {}
        metric = dict(row.get("eva_metrics") or {})
        metric.update(
            idProyecto=row["display_id"],
            deliveryManager=fields.get("delivery_manager")
            or "Sin DM confirmado",
            servicio=str(fields.get("service") or "Pendiente").upper(),
            nombre=fields.get("project_name") or "Pendiente",
            cliente=fields.get("client") or "",
            fechaInicio=row["iteration_start"],
            fechaFin=row["iteration_finish"],
            status=row["calendar_stage"],
            desviacionDias=row["deviation_days"],
            budget=float(row["budget"])
            if row.get("budget") is not None
            else None,
            budget_pending=row.get("budget") is None,
            hours_pending=metric.get("burn") is None,
            progress_pending=metric.get("avance") is None,
            azure_pending=metric.get("azure_pending", True),
        )
        # Stage alerts also follow iteration dates at the selected cut.
        metric["etapas"] = {
            stage.lower(): {
                "cerrada": any(
                    s["stage"] == stage
                    and s.get("finish")
                    and s["finish"] < cut.isoformat()
                    for s in row.get("stages", [])
                )
            }
            for stage in ("Discovery", "Development", "Deployment")
        }
        projected.append(metric)
    return {
        "eva": build_eva2_view(projected),
        "projected_rows": projected,
        "inventory_rows": rows,
        "extraction": run,
        "monthly_close_state": state,
        "eva_empty_text": (
            "Cierre mensual pendiente de validar/cargar."
            if state == "pending"
            else "No hay proyectos en el rango del corte seleccionado."
        ),
        "error": (
            f"{len(run.issues)} incidencias de origen." if run.issues else ""
        )
        if run
        else (
            f"Cierre mensual del {cut:%d/%m/%Y} pendiente de validar/cargar. "
            "No se reconstruye con el Azure actual."
            if state == "pending"
            else "Todavía no hay un inventario guardado."
        ),
    }
