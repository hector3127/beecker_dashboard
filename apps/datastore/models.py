"""Tablas de la base diaria del panel."""

from django.db import models

"""BKD.130.002 - Modelos de la base diaria
Registros de horas de Clockify por mes y el control de cada corrida de
sincronizacion. Ver docs/propuesta-base-datos-postgres.md.
"""


class SyncRun(models.Model):
    """Una corrida de sincronizacion (diaria o manual)."""

    kind = models.CharField(max_length=20)
    status = models.CharField(
        max_length=10,
        choices=[
            ("running", "En curso"),
            ("ok", "Correcta"),
            ("failed", "Fallida"),
        ],
        default="running",
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    months = models.JSONField(default=list)
    entries = models.IntegerField(default=0)
    requests = models.IntegerField(default=0)
    error = models.TextField(blank=True)

    class Meta:
        """Las corridas recientes primero."""

        ordering = ["-started_at", "-pk"]


class ClockifyMonthSync(models.Model):
    """Mes de Clockify ya guardado en la base y su resumen."""

    month = models.DateField(unique=True)
    entries_count = models.IntegerField()
    total_seconds = models.BigIntegerField()
    synced_at = models.DateTimeField()
    run = models.ForeignKey(SyncRun, on_delete=models.PROTECT)


class ClockifyTimeEntry(models.Model):
    """Un registro del reporte detallado de Clockify."""

    entry_id = models.CharField(max_length=40, primary_key=True)
    project_id = models.CharField(max_length=40)
    project_name = models.CharField(max_length=255, blank=True)
    task_id = models.CharField(max_length=40, blank=True)
    task_name = models.CharField(max_length=255, blank=True)
    user_id = models.CharField(max_length=40, blank=True)
    user_name = models.CharField(max_length=255, blank=True)
    tags = models.JSONField(default=list)
    description = models.TextField(blank=True)
    billable = models.BooleanField(default=False)
    # Inicio y fin tal como los entrega Clockify (ISO 8601), para que el
    # mapeo existente los lea igual que en el reporte.
    start = models.CharField(max_length=40, blank=True)
    end = models.CharField(max_length=40, blank=True)
    entry_date = models.DateField(null=True)
    month = models.DateField()
    duration_seconds = models.IntegerField()

    class Meta:
        """Indices de las consultas por proyecto, persona y mes."""

        indexes = [
            models.Index(fields=["project_id", "month"]),
            models.Index(fields=["user_id", "entry_date"]),
            models.Index(fields=["month"]),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(duration_seconds__gte=0),
                name="clockify_entry_duration_not_negative",
            ),
        ]
