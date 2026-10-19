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
    # Fecha de lockTimeEntries al iniciar ("" = sin bloqueo; None = no se
    # consulto) y por que se revisaron los meses mas antiguos.
    lock_seen = models.CharField(max_length=40, null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        """Las corridas recientes primero."""

        ordering = ["-started_at", "-pk"]


class SheetSnapshot(models.Model):
    """Una hoja de Google Sheets tal como estaba en la ultima sincronizacion.

    Las pantallas la leen desde aqui en lugar de pedirla a Google.
    """

    name = models.CharField(max_length=150, unique=True)
    rows = models.JSONField()
    row_count = models.IntegerField(default=0)
    synced_at = models.DateTimeField()


class Client(models.Model):
    """Cliente o cuenta, una sola vez aunque cada hoja lo escriba distinto."""

    name = models.CharField(max_length=255)
    key = models.CharField(max_length=255, unique=True)

    def __str__(self) -> str:
        return self.name


class ClientAlias(models.Model):
    """Forma de escribir un cliente (sin acentos ni mayusculas) y su cliente.

    Para unir dos nombres distintos (GNP y Grupo Nacional Provincial) se
    cambia el cliente de la variante en el admin: queda como manual y las
    siguientes sincronizaciones la respetan.
    """

    key = models.CharField(max_length=255, unique=True)
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="aliases"
    )
    spellings = models.JSONField(default=list)
    manual = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.key} -> {self.client}"


class Person(models.Model):
    """Persona (Delivery Manager, recurso, Account Manager, usuario)."""

    name = models.CharField(max_length=255)
    key = models.CharField(max_length=255, unique=True)
    clockify_user_id = models.CharField(max_length=40, blank=True)
    roles = models.JSONField(default=list)

    def __str__(self) -> str:
        return self.name


class PersonAlias(models.Model):
    """Forma de escribir una persona y la persona a la que corresponde."""

    key = models.CharField(max_length=255, unique=True)
    person = models.ForeignKey(
        Person, on_delete=models.CASCADE, related_name="aliases"
    )
    spellings = models.JSONField(default=list)
    manual = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.key} -> {self.person}"


class Project(models.Model):
    """Proyecto por su ID interno.

    Las variantes _S#, _CR# y _QA# apuntan a su proyecto base.
    """

    internal_id = models.CharField(max_length=80, unique=True)
    base_id = models.CharField(max_length=80, db_index=True)
    name = models.CharField(max_length=255, blank=True)
    service = models.CharField(max_length=60, blank=True)
    client = models.ForeignKey(
        Client, null=True, blank=True, on_delete=models.SET_NULL
    )
    delivery_manager = models.ForeignKey(
        Person, null=True, blank=True, on_delete=models.SET_NULL
    )
    sources = models.JSONField(default=list)
    spellings = models.JSONField(default=list)

    def __str__(self) -> str:
        return self.internal_id


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
