"""Prepara el grupo de acceso completo antes de encender ACCESS_ENFORCED."""

from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandParser

from apps.access.capabilities import CODES

"""BKD.140.007 - access_setup
Crea (o completa) el grupo "Acceso completo" con todas las capacidades del
catalogo. Con --incluir-usuarios suma a las personas activas, para que
encender ACCESS_ENFORCED no deje a nadie sin acceso. Se puede repetir.
"""

GROUP_NAME = "Acceso completo"


class Command(BaseCommand):
    """Crea el grupo de acceso completo."""

    help = "Crea el grupo 'Acceso completo' con todas las capacidades."

    def add_arguments(self, parser: CommandParser) -> None:
        """Opcion para sumar a las personas activas."""
        parser.add_argument(
            "--incluir-usuarios",
            action="store_true",
            help="Agrega al grupo a todas las personas activas.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        """Crea el grupo, sus permisos y, si se pide, suma a las personas."""
        permissions = Permission.objects.filter(
            content_type__app_label="access", codename__in=CODES
        )
        group, created = Group.objects.get_or_create(name=GROUP_NAME)
        group.permissions.set(permissions)
        added = 0
        if options["incluir_usuarios"]:
            users = get_user_model().objects.filter(is_active=True)
            group.user_set.add(*users)
            added = users.count()
        state = "creado" if created else "actualizado"
        self.stdout.write(
            f"Grupo '{GROUP_NAME}' {state} con {permissions.count()} "
            f"capacidades; {added} personas agregadas."
        )
