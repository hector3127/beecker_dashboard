"""Catálogo persistente, separado de las horas y aislado por workspace."""

from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.clockify.services.clockify_client import (
    ClockifyClient,
    ClockifyProject,
)
from apps.datastore.models import (
    ClockifyCatalog,
    ClockifyProjectRecord,
    ClockifyTaskRecord,
)
from core.data_cache import bump_revision


@transaction.atomic
def read_projects(workspace_id: str) -> list[ClockifyProject] | None:
    """Return the complete workspace catalog or None when missing."""
    catalog = ClockifyCatalog.objects.filter(workspace_id=workspace_id).first()
    if catalog is None:
        return None
    return [
        ClockifyProject(
            project_id=p.external_id, name=p.name, client_id=p.client_id
        )
        for p in ClockifyProjectRecord.objects.filter(catalog=catalog).order_by(
            "position"
        )
    ]


@transaction.atomic
def read_tasks(
    workspace_id: str, project_id: str
) -> list[dict[str, Any]] | None:
    """Return complete tasks, distinguishing empty from not synchronized."""
    project = ClockifyProjectRecord.objects.filter(
        catalog__workspace_id=workspace_id,
        external_id=project_id,
        tasks_synced_at__isnull=False,
    ).first()
    if project is None:
        return None
    return list(
        ClockifyTaskRecord.objects.filter(project=project)
        .order_by("position")
        .values_list("payload", flat=True)
    )


def sync_catalog(client: ClockifyClient, workspace_id: str) -> int:
    """Publica solo un catálogo completo; un error no borra la copia anterior.

    Las tareas se sincronizan bajo demanda por proyecto. El catálogo de
    proyectos suele ser grande; no se disparan miles de peticiones por corrida.
    """
    projects = client.list_projects(workspace_id)
    ids = [p.project_id for p in projects]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError("Catálogo Clockify con IDs vacíos o repetidos")
    with transaction.atomic():
        catalog, _ = ClockifyCatalog.objects.update_or_create(
            workspace_id=workspace_id,
            defaults={"synced_at": timezone.now()},
        )
        ClockifyProjectRecord.objects.filter(catalog=catalog).exclude(
            external_id__in=ids
        ).delete()
        ClockifyProjectRecord.objects.bulk_create(
            [
                ClockifyProjectRecord(
                    catalog=catalog,
                    external_id=p.project_id,
                    name=p.name,
                    client_id=p.client_id,
                    position=i,
                )
                for i, p in enumerate(projects)
            ],
            batch_size=500,
            update_conflicts=True,
            unique_fields=["catalog", "external_id"],
            update_fields=["name", "client_id", "position"],
        )
        ClockifyProjectRecord.objects.filter(catalog=catalog).update(
            tasks_synced_at=None
        )
        bump_revision()
    return len(projects)


def save_tasks(
    workspace_id: str, project_id: str, tasks: list[dict[str, Any]]
) -> None:
    """Guarda una respuesta completa, incluyendo la lista vacía."""
    ids = [str(t.get("id") or "") for t in tasks]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError("Tasks Clockify con IDs vacíos o repetidos")
    with transaction.atomic():
        project = ClockifyProjectRecord.objects.filter(
            catalog__workspace_id=workspace_id,
            external_id=project_id,
        ).first()
        if project is None:
            return
        ClockifyTaskRecord.objects.filter(project=project).delete()
        ClockifyTaskRecord.objects.bulk_create(
            [
                ClockifyTaskRecord(
                    project=project, external_id=value, position=i, payload=task
                )
                for i, (value, task) in enumerate(zip(ids, tasks, strict=True))
            ]
        )
        project.tasks_synced_at = timezone.now()
        project.save(update_fields=["tasks_synced_at"])
        bump_revision()
