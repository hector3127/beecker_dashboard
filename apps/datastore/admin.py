"""Admin de los catalogos: aqui se unen las variantes de un nombre."""

from typing import Any

from django.contrib import admin
from django.db.models import Model
from django.http import HttpRequest

from apps.datastore.models import (
    Client,
    ClientAlias,
    Person,
    PersonAlias,
    Project,
)

"""BKD.130.009 - Admin de la base diaria
Para unir dos nombres (por ejemplo «GNP» y «Grupo Nacional Provincial»)
se abre la variante en Alias de clientes o Alias de personas y se elige el
registro correcto: queda como manual y las sincronizaciones lo respetan.
"""


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Clientes del catalogo."""

    list_display = ("name", "key")
    search_fields = ("name", "key")


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Personas del catalogo."""

    list_display = ("name", "roles", "clockify_user_id")
    search_fields = ("name", "key", "clockify_user_id")


class AliasAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Alias: cambiar el registro de una variante la marca como manual."""

    list_display = ("key", "target", "manual")
    list_filter = ("manual",)
    search_fields = ("key",)
    readonly_fields = ("key", "spellings")
    owner_field = ""

    def target(self, obj: Model) -> str:
        """Registro al que apunta la variante."""
        return str(getattr(obj, self.owner_field))

    def save_model(
        self,
        request: HttpRequest,
        obj: Model,
        form: Any,
        change: bool,
    ) -> None:
        """Marca el alias como manual cuando se cambia su registro."""
        if self.owner_field in form.changed_data:
            obj.manual = True  # type: ignore[attr-defined]
        super().save_model(request, obj, form, change)


@admin.register(ClientAlias)
class ClientAliasAdmin(AliasAdmin):
    """Variantes de clientes."""

    owner_field = "client"
    autocomplete_fields = ("client",)


@admin.register(PersonAlias)
class PersonAliasAdmin(AliasAdmin):
    """Variantes de personas."""

    owner_field = "person"
    autocomplete_fields = ("person",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):  # type: ignore[type-arg]
    """Proyectos del catalogo."""

    list_display = (
        "internal_id",
        "name",
        "service",
        "client",
        "delivery_manager",
    )
    list_filter = ("service",)
    search_fields = ("internal_id", "name", "base_id")
