"""Horas por mes y por tarea leidas de la base en lugar de la hoja gigante."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any

from apps.datastore.models import ClockifyMonthSync, ClockifyTimeEntry
from apps.gse.services.base_store import BaseStore, HourRecord, unique_ids
from apps.gse.services.cells import norm
from apps.portal.services.eva4_hours import BASE_TAGS, EXTRA_TAGS, task_key

"""BKD.130.010 - Base de horas desde la base de datos
Sustituye a la hoja «08.Base Clockify AAAA» (164,000 filas que se recorrian
celda por celda en cada consulta) por clockify_time_entry. Las dos lecturas
entregan lo mismo que la hoja: Facturabilidad y GSE reciben HourRecord, y
EVA-04 el indice de horas por tarea y mes. Un mes que no esta sincronizado
sigue leyendose de la hoja.
"""

TAG_SEPARATOR = ", "
# Desde septiembre tambien cuentan las etiquetas extra (regla de EVA-04).
EXTRA_TAGS_FROM_MONTH = 9


def month_start(month: str) -> date:
    """Primer dia de un mes AAAA-MM."""
    return date.fromisoformat(f"{month}-01")


def is_synced(month: str) -> bool:
    """Indica si el mes esta guardado en la base."""
    return ClockifyMonthSync.objects.filter(month=month_start(month)).exists()


def read_hour_records(
    month: str,
    user_ids: Sequence[str] | None = None,
) -> list[HourRecord]:
    """
    Registros de horas de un mes, en el orden de la hoja (por ID).

    Args:
        month: Mes AAAA-MM, ya sincronizado.
        user_ids: IDs de Clockify a incluir; None incluye a todos.

    Returns:
        Los HourRecord del mes. Las etiquetas se dividen por «, » como las
        guardaba la hoja, para que el resultado sea el mismo.
    """
    rows = ClockifyTimeEntry.objects.filter(
        month=month_start(month), entry_date__isnull=False
    )
    if user_ids is not None:
        rows = rows.filter(user_id__in=list(user_ids))
    return [
        HourRecord(
            record_id=entry_id,
            user_id=user_id,
            resource=user_name,
            project=project_name,
            task=task_name,
            tags=TAG_SEPARATOR.join(tags).split(TAG_SEPARATOR),
            billable=billable,
            day=entry_date.isoformat(),
            hours=seconds / 3600,
        )
        for (
            entry_id,
            user_id,
            user_name,
            project_name,
            task_name,
            tags,
            billable,
            entry_date,
            seconds,
        ) in rows.order_by("entry_id").values_list(
            "entry_id",
            "user_id",
            "user_name",
            "project_name",
            "task_name",
            "tags",
            "billable",
            "entry_date",
            "duration_seconds",
        )
        if entry_date is not None
    ]


class StoredBaseStore(BaseStore):
    """BaseStore que lee de la base los meses ya sincronizados."""

    def read_stored_month(
        self,
        month: str,
        user_ids: Sequence[str] | None,
        allow_old: bool,
    ) -> list[HourRecord] | None:
        """
        Lee un mes de la base de datos; si no esta, de la hoja.

        Args:
            month: Mes AAAA-MM.
            user_ids: IDs de Clockify pedidos; None para todos.
            allow_old: Sin efecto: la base es la de la ultima sincronizacion.

        Returns:
            Los registros del mes, o None si no hay de donde leerlos.
        """
        if not is_synced(month):
            return super().read_stored_month(month, user_ids, allow_old)
        return read_hour_records(month, unique_ids(user_ids))


def year_is_synced(year: int) -> bool:
    """Indica si algun mes del ano esta guardado en la base."""
    return ClockifyMonthSync.objects.filter(month__year=year).exists()


def build_hour_index_from_store(year: int) -> dict[str, Any]:
    """
    Horas por tarea y mes de un ano, como el indice que armaba la hoja.

    Args:
        year: Ano del reporte.

    Returns:
        {"totals": mes -> tarea -> horas, "tasks": tareas vistas, "errors":
        meses con horas no numericas (siempre vacio: la base es numerica)}.
    """
    totals: dict[str, dict[str, Decimal]] = {}
    tasks: set[str] = set()
    rows = ClockifyTimeEntry.objects.filter(entry_date__year=year).values_list(
        "task_name", "tags", "entry_date", "duration_seconds"
    )
    accumulated: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    for task_name, tags, entry_date, seconds in rows.iterator():
        key = task_key(task_name)
        if not key or entry_date is None:
            continue
        tasks.add(key)
        allowed = BASE_TAGS | (
            EXTRA_TAGS if entry_date.month >= EXTRA_TAGS_FROM_MONTH else set()
        )
        if norm(TAG_SEPARATOR.join(tags)) not in allowed:
            continue
        month_key = entry_date.strftime("%Y-%m")
        accumulated[(month_key, key)] += Decimal(str(seconds / 3600))
    for (month_key, key), hours in accumulated.items():
        totals.setdefault(month_key, {})[key] = hours
    return {"totals": totals, "tasks": tasks, "errors": set()}
