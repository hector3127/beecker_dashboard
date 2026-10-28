"""Lectura y escritura de Azure DevOps en la base diaria."""

import threading
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from django.db import connection, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.datastore.models import AzureIteration, AzureProject, AzureWorkItem
from core.data_cache import bump_revision
from core.utils.parallel import is_pool_worker

"""BKD.130.011 - Azure DevOps en la base
Guarda por Team Project lo mismo que devuelve AzureDevOpsClient: los 1,000
work items mas recientes, el RAID, los campos de Risk y las iteraciones.
El payload de cada fila es la respuesta de Azure sin tocar, asi que lo que
lee el gateway es identico a lo que leeria en vivo; las columnas (tipo,
estado, titulo, iteracion, asignado, fecha) sirven para consultar.
"""

JsonObject = dict[str, Any]
RaidData = tuple[list[JsonObject], list[JsonObject]]


def _field(item: JsonObject, name: str) -> Any:
    """Campo de un work item, o None."""
    fields = item.get("fields")
    return fields.get(name) if isinstance(fields, dict) else None


def _text(value: Any, limit: int) -> str:
    """Texto acotado; una identidad de Azure se reduce a su nombre."""
    if isinstance(value, dict):
        value = value.get("displayName") or value.get("uniqueName") or ""
    return str(value or "")[:limit]


def _moment(value: Any) -> datetime | None:
    """Fecha ISO 8601 de Azure; None si no es valida."""
    if not isinstance(value, str) or not value:
        return None
    try:
        return parse_datetime(value)
    except ValueError:
        return None


def build_work_item(
    project: AzureProject,
    kind: str,
    position: int,
    item: JsonObject,
) -> AzureWorkItem:
    """
    Fila de un work item.

    Args:
        project: Proyecto al que pertenece.
        kind: LATEST o RAID.
        position: Lugar en la lista que entrego Azure.
        item: Respuesta de Azure.

    Returns:
        La fila sin guardar.
    """
    raw_id = item.get("id", _field(item, "System.Id"))
    return AzureWorkItem(
        project=project,
        kind=kind,
        position=position,
        work_item_id=int(raw_id) if isinstance(raw_id, int) else 0,
        item_type=_text(_field(item, "System.WorkItemType"), 60),
        state=_text(_field(item, "System.State"), 60),
        title=_text(_field(item, "System.Title"), 500),
        iteration_path=_text(_field(item, "System.IterationPath"), 500),
        assigned_to=_text(_field(item, "System.AssignedTo"), 255),
        changed_at=_moment(_field(item, "System.ChangedDate")),
        payload=item,
    )


def save_project(
    name: str,
    position: int,
    data: tuple[
        list[JsonObject], list[JsonObject], list[JsonObject], list[JsonObject]
    ],
    raid_version: int,
    risk_fields_ok: bool = True,
) -> None:
    """
    Reemplaza todo lo guardado de un Team Project en una transaccion.

    Args:
        name: Nombre del Team Project.
        position: Lugar del proyecto en la lista de Azure.
        data: Work items, RAID, campos de Risk e iteraciones.
        raid_version: Version del RAID de la cache en este momento.
        risk_fields_ok: Los campos de Risk se leyeron bien.
    """
    work_items, raid, risk_fields, iterations = data
    with transaction.atomic():
        project, _ = AzureProject.objects.update_or_create(
            name=name,
            defaults={
                "position": position,
                "risk_fields": risk_fields,
                "risk_fields_ok": risk_fields_ok,
                "raid_version": raid_version,
                "synced_at": timezone.now(),
            },
        )
        project.work_items.filter(
            kind__in=[AzureWorkItem.LATEST, AzureWorkItem.RAID]
        ).delete()
        project.iterations.all().delete()
        AzureWorkItem.objects.bulk_create(
            [
                build_work_item(project, AzureWorkItem.LATEST, index, item)
                for index, item in enumerate(work_items)
            ]
            + [
                build_work_item(project, AzureWorkItem.RAID, index, item)
                for index, item in enumerate(raid)
            ],
            batch_size=500,
        )
        AzureIteration.objects.bulk_create(
            [
                AzureIteration(
                    project=project,
                    position=index,
                    name=str(iteration.get("nombre") or "")[:255],
                    path=str(iteration.get("path") or "")[:500],
                    start_date=_moment(iteration.get("fechaInicio")),
                    finish_date=_moment(iteration.get("fechaFin")),
                    payload=iteration,
                )
                for index, iteration in enumerate(iterations)
            ],
            batch_size=500,
        )
        bump_revision()


@transaction.atomic
def drop_projects_except(names: Sequence[str]) -> int:
    """
    Borra los proyectos que ya no existen en la organizacion.

    Args:
        names: Team Projects vigentes.

    Returns:
        Cuantos proyectos se borraron.
    """
    gone = AzureProject.objects.exclude(name__in=list(names))
    # delete() cuenta tambien las filas hijas; aqui solo interesan proyectos.
    count = gone.count()
    gone.delete()
    if count:
        bump_revision()
    return count


def _release_thread_connection() -> None:
    """Cierra la conexion de un hilo suelto (los del pool la cierran solos)."""
    if (
        threading.current_thread() is not threading.main_thread()
        and not is_pool_worker()
    ):
        connection.close()


def read_project_names() -> list[str] | None:
    """Nombres de los Team Projects en el orden de Azure; None si no hay."""
    try:
        names = list(
            AzureProject.objects.order_by("position").values_list(
                "name", flat=True
            )
        )
        return names or None
    finally:
        _release_thread_connection()


def has_project(name: str) -> bool:
    """Indica si el proyecto esta guardado."""
    try:
        return AzureProject.objects.filter(name=name).exists()
    finally:
        _release_thread_connection()


def read_work_items(name: str) -> list[JsonObject] | None:
    """Work items del proyecto como los devolvio Azure; None si no esta."""
    try:
        if not AzureProject.objects.filter(name=name).exists():
            return None
        return list(
            AzureWorkItem.objects.filter(
                project__name=name, kind=AzureWorkItem.LATEST
            )
            .order_by("position")
            .values_list("payload", flat=True)
        )
    finally:
        _release_thread_connection()


def read_raid(name: str, version: int | None = None) -> RaidData | None:
    """
    RAID y campos de Risk del proyecto.

    Args:
        name: Team Project.
        version: Compatibilidad con lectores anteriores; no decide frescura.

    Returns:
        Los dos, o None si el proyecto no esta, sus campos no se leyeron o
        la app creo un registro despues de la sincronizacion.
    """
    try:
        project = AzureProject.objects.filter(name=name).first()
        # La pérdida/rotación de la caché no invalida datos persistentes.
        # Las escrituras reales marcan el proyecto dentro de una transacción.
        if project is None or not project.risk_fields_ok:
            return None
        items = list(
            AzureWorkItem.objects.filter(
                project=project, kind=AzureWorkItem.RAID
            )
            .order_by("position")
            .values_list("payload", flat=True)
        )
        return items, list(project.risk_fields)
    finally:
        _release_thread_connection()


def read_iterations(name: str) -> list[JsonObject] | None:
    """Iteraciones del proyecto como las aplana el cliente; None si no esta."""
    try:
        if not AzureProject.objects.filter(name=name).exists():
            return None
        return list(
            AzureIteration.objects.filter(project__name=name)
            .order_by("position")
            .values_list("payload", flat=True)
        )
    finally:
        _release_thread_connection()
