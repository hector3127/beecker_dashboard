"""Materialize current-month DM KPIs without altering EVA or its sources."""

from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.datastore.models import (
    DmKpiMetric,
    DmKpiObservation,
    DmKpiPeriod,
    EvaExtraction,
)
from apps.portal.services.kpi_dm_store import closing_day
from apps.portal.services.kpi_eva import eva_manager_view
from apps.portal.services.summary_inventory import inventory_rows


def _projects(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    projects = []
    for row in rows:
        metric = dict(row.get("eva_metrics") or {})
        fields = row.get("fields") or {}
        metric.update(
            idProyecto=row["display_id"],
            deliveryManager=fields.get("delivery_manager")
            or "Sin DM confirmado",
            desviacionDias=row.get("deviation_days"),
            budget=float(row["budget"])
            if row.get("budget") is not None
            else None,
            budget_pending=row.get("budget") is None,
            hours_pending=metric.get("burn") is None,
            progress_pending=metric.get("avance") is None,
        )
        projects.append(metric)
    return projects


def capture_current_month(*, require_today: bool = False) -> DmKpiObservation:
    """Persist only a real observation in the current month, atomically."""
    today = timezone.localdate()
    month = today.replace(day=1)
    end = closing_day(today)
    if today > end:
        raise ValueError(
            "Terminó el corte KPI del mes; no se modifica. "
            "El siguiente mes tendrá su propio registro."
        )
    source = (
        EvaExtraction.objects.filter(
            published=True,
            finished_at__isnull=False,
            metrics__kind="summary_inventory",
            metrics__eva_enriched=True,
        )
        .order_by("-pk")
        .first()
    )
    stamp = (
        parse_datetime(source.metrics.get("source_observed_at", ""))
        if source
        else None
    )
    if source is None or stamp is None or not timezone.is_aware(stamp):
        raise ValueError(
            "No hay una extracción local válida para actualizar KPIs."
        )
    cut = timezone.localdate(stamp)
    if cut.replace(day=1) != month or cut > today:
        raise ValueError(
            "Actualiza primero las fuentes del mes actual; "
            "no se reconstruyen meses anteriores."
        )
    if require_today and cut != today:
        raise ValueError("Las fuentes aún no tienen una observación de hoy.")
    _, rows = inventory_rows(cut=cut, source_run=source, use_closes=False)
    projects = _projects(rows)
    view = eva_manager_view(projects)
    with transaction.atomic():
        period, _ = DmKpiPeriod.objects.get_or_create(
            month=month, defaults={"closing_day": end}
        )
        period = DmKpiPeriod.objects.select_for_update().get(pk=period.pk)
        if period.status != "open":
            raise ValueError(
                "El periodo KPI está cerrado o pendiente de conciliación; "
                "no se sobrescribe."
            )
        if period.latest_observation and period.latest_observation.cut > cut:
            raise ValueError(
                "La fuente es anterior a la última captura KPI guardada."
            )
        observation, created = DmKpiObservation.objects.get_or_create(
            period=period,
            cut=cut,
            defaults={"source_observed_at": stamp, "source": source},
        )
        if not created and cut < today:
            return observation
        observation.source = source
        observation.source_observed_at = stamp
        observation.issues = list(source.issues)
        observation.save()
        observation.metrics.all().delete()
        metrics = []
        for item in view.rows:
            own = [p for p in projects if p["deliveryManager"] == item.name]
            cost_unknown = sum(
                bool(
                    p.get("budget_pending")
                    or p.get("hours_pending")
                    or p.get("progress_pending")
                    or float(p.get("budget") or 0) <= 0
                )
                for p in own
            )
            metrics.append(
                DmKpiMetric(
                    observation=observation,
                    manager=item.name,
                    slug=item.slug,
                    total=item.total,
                    on_time=item.health.on_time,
                    late=item.time_late or 0,
                    over_budget=item.cost_over or 0,
                    time_unknown=sum(
                        p.get("desviacionDias") is None for p in own
                    ),
                    cost_unknown=cost_unknown,
                )
            )
        DmKpiMetric.objects.bulk_create(metrics)
        period.latest_observation = observation
        period.save()
    return observation


def close_due_periods() -> None:
    """Future daily job closes only this KPI store, never EVA."""
    if not settings.KPI_DM_AUTO_UPDATE_ENABLED:
        return
    today = timezone.localdate()
    with transaction.atomic():
        for period in (
            DmKpiPeriod.objects.select_for_update()
            .filter(status="open", closing_day__lt=today)
            .select_related("latest_observation")
        ):
            complete = bool(
                period.latest_observation
                and period.latest_observation.cut == period.closing_day
            )
            period.status = "closed" if complete else "pending"
            period.closed_at = timezone.now() if complete else None
            period.save()
