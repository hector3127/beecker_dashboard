"""Copia completa de las lecturas del panel, con campos y relaciones.

No se usa el resumen de 1,000 elementos del gateway: contiene menos campos.
Conserva el mismo orden y límite de 750 elementos del panel vigente.
"""

from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.daily.services.daily_azure_client import DailyAzureClient
from apps.datastore.models import (
    AzurePanelSnapshot,
    AzureProject,
    AzureWorkItem,
)
from apps.datastore.services.azure_store import build_work_item
from core.data_cache import bump_revision

PANEL = AzureWorkItem.PANEL
LIMIT = 750
BATCH = 150


def download(
    client: DailyAzureClient, name: str
) -> tuple[int, list[dict[str, Any]]]:
    """Falla ante respuestas incompletas; nunca publica un lote parcial."""
    url = client.project_url(name)
    escaped = name.replace("'", "''")
    response = client.send(
        "POST",
        f"{url}wiql",
        retry=True,
        params={"api-version": "7.1"},
        json={
            "query": "SELECT [System.Id] FROM WorkItems "
            "WHERE [System.TeamProject] = "
            f"'{escaped}' ORDER BY [System.ChangedDate] DESC"
        },
    )
    if not isinstance(response.get("workItems"), list):
        raise ValueError("Azure no devolvió la lista completa de IDs")
    all_ids = [row["id"] for row in response["workItems"]]
    ids = all_ids[:LIMIT]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("Azure devolvió IDs repetidos")
    items: list[dict[str, Any]] = []
    for start in range(0, len(ids), BATCH):
        selected = ids[start : start + BATCH]
        result = client.send(
            "GET",
            f"{url}workitems",
            retry=True,
            params={
                "ids": ",".join(map(str, selected)),
                "$expand": "all",
                "api-version": "7.1",
            },
        )
        rows = result.get("value")
        if (
            not isinstance(rows, list)
            or len(rows) != len(selected)
            or {row.get("id") for row in rows} != set(selected)
            or any(not isinstance(row.get("fields"), dict) for row in rows)
        ):
            raise ValueError(
                "Lote Azure incompleto: se conserva la copia anterior"
            )
        # Igual que fetch_raw_items: conservar el orden de cada lote de Azure.
        items.extend(rows)
    return len(all_ids), items


def save(name: str, total: int, items: list[dict[str, Any]]) -> None:
    """Publish the payloads and coverage marker in the same transaction."""
    if len(items) != min(total, LIMIT):
        raise ValueError("La copia Azure no está completa")
    with transaction.atomic():
        project = AzureProject.objects.get(name=name)
        AzureWorkItem.objects.filter(project=project, kind=PANEL).delete()
        AzureWorkItem.objects.bulk_create(
            [
                build_work_item(project, PANEL, index, item)
                for index, item in enumerate(items)
            ],
            batch_size=500,
        )
        AzurePanelSnapshot.objects.update_or_create(
            project=project,
            defaults={"total_items": total, "synced_at": timezone.now()},
        )
        bump_revision()


@transaction.atomic
def read(name: str) -> tuple[AzurePanelSnapshot, list[dict[str, Any]]] | None:
    """None significa no sincronizado; una lista vacía sí es un corte válido."""
    snapshot = AzurePanelSnapshot.objects.filter(project__name=name).first()
    if snapshot is None:
        return None
    items = list(
        AzureWorkItem.objects.filter(project_id=snapshot.project_id, kind=PANEL)
        .order_by("position")
        .values_list("payload", flat=True)
    )
    if len(items) != min(snapshot.total_items, LIMIT):
        return None
    return snapshot, items


@transaction.atomic
def invalidate(project_name: str | None = None) -> None:
    """Tras una escritura externa, no servir el corte anterior como vigente."""
    snapshots = AzurePanelSnapshot.objects.all()
    projects = AzureProject.objects.all()
    if project_name is not None:
        snapshots = snapshots.filter(project__name=project_name)
        projects = projects.filter(name=project_name)
    snapshots.delete()
    projects.update(risk_fields_ok=False)
    bump_revision()
