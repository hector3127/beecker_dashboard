"""Persistent global executive agreements and follow-ups."""

from django.db import models


class ExecutiveAgreement(models.Model):
    """Acuerdo o pendiente global con responsable y seguimiento."""

    account = models.CharField(max_length=150, blank=True)
    meeting_source = models.CharField(
        max_length=12,
        choices=[("direction", "Dirección"), ("board", "Consejo")],
        default="direction",
    )
    meeting_date = models.DateField(null=True, blank=True)
    title = models.CharField(max_length=200)
    kind = models.CharField(
        max_length=12,
        choices=[("agreement", "Acuerdo"), ("pending", "Pendiente")],
        default="pending",
    )
    owner = models.CharField(max_length=150, blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=12,
        choices=[
            ("open", "Abierto"),
            ("progress", "En curso"),
            ("done", "Completado"),
        ],
        default="open",
    )
    notes = models.CharField(max_length=2000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Muestra primero los registros recientes."""

        ordering = ["-created_at", "-pk"]


class AccountLogo(models.Model):
    """Small validated account logo, stored with the database backup."""

    key = models.CharField(max_length=150, unique=True)
    account = models.CharField(max_length=150)
    image = models.BinaryField()
    updated_at = models.DateTimeField(auto_now=True)
