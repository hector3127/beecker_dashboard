"""EVA reads committed local cuts only: no network, Sheets or volatile cache."""

from datetime import date
from typing import Any

from django.utils import timezone

from apps.datastore.models import EvaExtraction, EvaScopeSnapshot
from apps.portal.services.eva2 import build_eva2_view


def snapshot(
    cut: date, closed: bool = False, latest: bool = False
) -> dict[str, Any]:
    """Past dates require an observation from that day."""
    runs = EvaExtraction.objects.filter(published=True, full_inventory=True)
    runs = runs.filter(cut__lte=cut) if latest else runs.filter(cut=cut)
    run = runs.order_by("-cut", "-started_at", "-pk").first()
    if run is None:
        return {
            "rows": [],
            "error": "No hay un corte Azure/Clockify para esta fecha. "
            "Actualiza las fuentes para crear el corte de hoy.",
            "extraction": None,
        }
    rows = list(
        EvaScopeSnapshot.objects.filter(source__extraction=run, closed=closed)
        .order_by("project_id")
        .values_list("row", flat=True)
    )
    # Normalize earlier observed projections using their saved exact mapping;
    # this does not fetch or substitute a different source/date.
    for row in rows:
        if (
            row.get("business_base")
            and row.get("scope")
            and row.get("summary_scope") != "BASE"
        ):
            row["idProyecto"] = f"{row['business_base']}_{row['scope']}"
        if "inverted_dates" in row.get("source_issues", []):
            row.update(
                hours_pending=True,
                progress_pending=True,
                burn=None,
                etc=None,
                avance=None,
                hoursDeviation=None,
            )
    rows = [
        r
        for r in rows
        if not r.get("fechaInicio") or r["fechaInicio"] <= cut.isoformat()
    ]
    messages = []
    services = {"IXB", "RAAS", "RAAS+", "SAAS", "POC", "IXB Y RAAS"}
    unclassified = [r for r in rows if r.get("servicio") not in services]
    rows = [r for r in rows if r.get("servicio") in services]
    if unclassified:
        messages.append(
            f"TP parcial: {len(unclassified)} bloques sin servicio confirmado "
            "no se incluyen en EVA; requieren completar el Summary."
        )
    uncertain = [
        r
        for r in rows
        if r.get("azure_pending")
        and r.get("status") == "Pendiente"
        or {"invalid_project_id", "scope_id_mismatch", "identity_mismatch"}
        & set(r.get("source_issues", []))
    ]
    uncertain_ids = {id(r) for r in uncertain}
    rows = [r for r in rows if id(r) not in uncertain_ids]
    if uncertain:
        messages.append(
            f"TP parcial: {len(uncertain)} bloques sin estado confirmado "
            "quedan fuera del inventario abierto hasta resolver su iteración."
        )
    if run.cut != cut:
        messages.append(f"Se muestra el último corte disponible: {run.cut}.")
    if run.issues:
        messages.append(
            f"{len(run.issues)} incidencias de origen; "
            "los valores no verificables quedan pendientes."
        )
    return {"rows": rows, "error": " ".join(messages), "extraction": run}


def load_native_cut(
    cut: date, closed: bool = False, latest: bool = False
) -> dict[str, Any]:
    """Preserve the existing screen contract with local persisted providers."""
    data = snapshot(cut, closed, latest)
    return {
        "eva": build_eva2_view(data["rows"]),
        "error": data["error"],
        "extraction": data["extraction"],
    }


def extraction_status() -> dict[str, Any]:
    """Return timings/status without disclosing raw source payloads."""
    run = (
        EvaExtraction.objects.filter(full_inventory=True)
        .order_by("-pk")
        .first()
    )
    if not run:
        return {"state": "idle", "id": None, "metrics": {}}
    state = (
        "running"
        if run.finished_at is None
        else "ready"
        if run.published
        else "failed"
    )
    return {
        "state": state,
        "id": run.pk,
        "cut": run.cut.isoformat(),
        "started_at": run.started_at.isoformat(),
        "metrics": run.metrics,
        "issues": run.issues,
        "full_inventory": run.full_inventory,
        "stale_job": run.finished_at is None
        and (timezone.now() - run.started_at).total_seconds() > 7200,
    }
