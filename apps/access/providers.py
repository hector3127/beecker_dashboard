"""De donde salen las capacidades y el alcance de cada persona."""

from typing import Any, Protocol

from django.conf import settings
from django.utils.module_loading import import_string

from apps.access.capabilities import CODES
from apps.access.scope import AccessScope

"""BKD.140.005 - Proveedores de acceso
El portal le pregunta a un proveedor; cambiar de fuente (grupos de Django
hoy, Genesis despues) es cambiar ACCESS_PROVIDER, sin tocar pantallas ni
API. Un proveedor implementa capabilities() y scope().
"""


class AccessProvider(Protocol):
    """Contrato que cumple cualquier fuente de accesos."""

    def capabilities(self, user: Any) -> frozenset[str]:
        """Codigos del catalogo que la persona puede ejercer."""
        ...

    def scope(self, user: Any) -> AccessScope:
        """Cuentas y proyectos sobre los que puede ejercerlos."""
        ...


def _active(user: Any) -> bool:
    return bool(getattr(user, "is_authenticated", False) and user.is_active)


class DjangoAccessProvider:
    """Capacidades por grupos y permisos de Django; alcance sin restriccion.

    shortcut: todas las personas con sesion ven todo el portafolio porque
    Django no guarda a que cuentas pertenece cada quien; el alcance limitado
    lo entrega Genesis (o un proveedor propio) cuando se defina.
    """

    def capabilities(self, user: Any) -> frozenset[str]:
        """Los permisos access.<codigo> que tiene la persona."""
        if not _active(user):
            return frozenset()
        return frozenset(c for c in CODES if user.has_perm(f"access.{c}"))

    def scope(self, user: Any) -> AccessScope:
        """Todo el portafolio para quien tiene sesion; nada para el resto."""
        return (
            AccessScope.everything() if _active(user) else AccessScope.limited()
        )


def get_provider() -> AccessProvider:
    """El proveedor configurado en ACCESS_PROVIDER."""
    provider: AccessProvider = import_string(settings.ACCESS_PROVIDER)()
    return provider
