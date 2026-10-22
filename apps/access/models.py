"""Modelo sin tabla que registra las capacidades como permisos de Django."""

from django.db import models

from apps.access.capabilities import CATALOG

"""BKD.140.003 - Permisos de capacidades
Django crea un Permission por cada capacidad del catalogo. Asi se asignan
desde grupos en el administrador mientras Genesis no entregue los roles.
No hay tabla: managed=False y sin permisos por defecto.
"""


class Capability(models.Model):
    """Ancla de los permisos del catalogo; nunca se guardan filas."""

    class Meta:
        """Solo declara los permisos del catalogo."""

        managed = False
        default_permissions = ()
        permissions = [(item.code, item.label) for item in CATALOG]
